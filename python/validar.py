"""Validación CSV + conciliación independiente pandas/SQL (SQLite local)."""
from pathlib import Path
import json, sqlite3, sys
import numpy as np
import pandas as pd
BASE=Path(__file__).resolve().parents[1]
TABLES=['categorias','proveedores','productos','movimientos','calendario']
def validar(tablas):
    t=tablas; p=t['productos']; m=t['movimientos']; c=t['calendario']
    for name,df in t.items():
        assert not df.isna().any().any(),f'{name}: nulos'
        pk={'categorias':'categoria_id','proveedores':'proveedor_id','productos':'producto_id','movimientos':'movimiento_id','calendario':'fecha'}[name]
        assert not df[pk].duplicated().any(),f'{name}: PK duplicada'
        assert not df.duplicated().any(),f'{name}: filas duplicadas'
        for col in df:
            if col.endswith('_id') or col in ['cantidad','stock_inicial','stock_minimo','anio','mes']:
                n=pd.to_numeric(df[col],errors='raise'); assert np.isfinite(n).all() and (n%1==0).all(),f'{col}: entero requerido'
            if df[col].dtype=='object': assert df[col].astype(str).str.strip().ne('').all(),f'{col}: vacío'
    assert p.codigo.is_unique
    assert p.categoria_id.isin(t['categorias'].categoria_id).all()
    assert p.proveedor_id.isin(t['proveedores'].proveedor_id).all()
    assert m.producto_id.isin(p.producto_id).all()
    assert m.fecha.isin(c.fecha).all()
    for df in [m,p]:
        v=pd.to_numeric(df.costo_unitario,errors='raise'); assert np.isfinite(v).all() and (v>0).all() and np.allclose(v*100,np.round(v*100))
    assert (p.precio_referencia>=p.costo_unitario).all()
    assert p.activo.isin([True,False]).all()
    assert (p.stock_inicial>=0).all() and (p.stock_minimo>0).all()
    assert (m.cantidad>0).all() and m.tipo.isin(['entrada','salida']).all()
    cd=pd.to_datetime(c.fecha,format='%Y-%m-%d',errors='raise'); md=pd.to_datetime(m.fecha,format='%Y-%m-%d',errors='raise')
    assert cd.equals(pd.Series(pd.date_range('2025-01-01','2025-12-31'),name='fecha'))
    assert (c.anio==cd.dt.year).all() and (c.mes==cd.dt.month).all() and (c.anio_mes==cd.dt.strftime('%Y-%m')).all()
    cost=m.producto_id.map(p.set_index('producto_id').costo_unitario)
    assert np.allclose(m.costo_unitario,cost), 'Costo constante requerido'
    signed=np.where(m.tipo=='entrada',m.cantidad,-m.cantidad)
    ordered=m.assign(delta=signed).sort_values(['producto_id','fecha','movimiento_id'])
    saldo=ordered.groupby('producto_id').delta.cumsum()+ordered.producto_id.map(p.set_index('producto_id').stock_inicial)
    assert (saldo>=0).all(),'Saldo negativo'
    assert 3000<=len(m)<=5000
    return ordered,saldo

def main():
    t={n:pd.read_csv(BASE/'datos'/f'{n}.csv') for n in TABLES}; ordered,saldo=validar(t)
    p=t['productos'];m=t['movimientos'];cal=t['calendario']; idx=p.set_index('producto_id')
    db=sqlite3.connect(':memory:')
    for n,df in t.items(): df.to_sql(n,db,index=False)
    db.executescript((BASE/'sql/03_vistas.sql').read_text())
    for sql in '\n'.join(line for line in (BASE/'sql/04_analisis.sql').read_text().splitlines() if not line.lstrip().startswith('--')).split(';'):
        if sql.strip(): db.execute(sql).fetchall()
    daily=m.assign(delta=np.where(m.tipo=='entrada',m.cantidad,-m.cantidad)).pivot_table(index='fecha',columns='producto_id',values='delta',aggfunc='sum',fill_value=0).reindex(cal.fecha,fill_value=0).reindex(columns=idx.index,fill_value=0).cumsum().add(idx.stock_inicial,axis=1)
    stock=daily.iloc[-1]; value=float((stock*idx.costo_unitario).sum());low=int(((stock<idx.stock_minimo)&idx.activo).sum())
    sql_stock=pd.read_sql_query('SELECT producto_id,stock FROM v_stock ORDER BY producto_id',db).set_index('producto_id').stock
    assert np.array_equal(stock,sql_stock)
    sql_kpi=db.execute('SELECT * FROM v_kpi').fetchone()
    assert np.allclose(sql_kpi,[stock.sum(),value,idx.activo.sum(),low])
    py_month=m.assign(entradas=np.where(m.tipo=='entrada',m.cantidad,0),salidas=np.where(m.tipo=='salida',m.cantidad,0),anio_mes=m.fecha.str[:7]).groupby('anio_mes')[['entradas','salidas']].sum()
    sq_month=pd.read_sql_query('SELECT * FROM v_mensual ORDER BY anio_mes',db).set_index('anio_mes');assert np.array_equal(py_month,sq_month)
    py_prov=m.merge(p[['producto_id','proveedor_id']],on='producto_id').groupby(['proveedor_id','tipo']).cantidad.sum().sort_index()
    sq_prov=pd.read_sql_query('SELECT p.proveedor_id,m.tipo,SUM(m.cantidad) cantidad FROM movimientos m JOIN productos p USING(producto_id) GROUP BY p.proveedor_id,m.tipo ORDER BY p.proveedor_id,m.tipo',db).set_index(['proveedor_id','tipo']).cantidad
    assert np.array_equal(py_prov,sq_prov)
    rows=[];scenarios=0
    groups=[('Todos',list(idx.index))]+[(f'Categoria {v}',list(p.loc[p.categoria_id==v,'producto_id'])) for v in sorted(p.categoria_id.unique())]+[(f'Proveedor {v}',list(p.loc[p.proveedor_id==v,'producto_id'])) for v in sorted(p.proveedor_id.unique())]
    for month in range(1,13):
        dates=cal.loc[cal.mes==month,'fecha']; start=dates.iloc[0]; end=dates.iloc[-1]
        for label,ids in groups:
            sub=m[m.producto_id.isin(ids)&m.fecha.between(start,end)]; en=int(sub.loc[sub.tipo=='entrada','cantidad'].sum()); sa=int(sub.loc[sub.tipo=='salida','cantidad'].sum())
            close=daily.loc[end,ids]; val=float((close*idx.loc[ids,'costo_unitario']).sum()); low_count=int(((close<idx.loc[ids,'stock_minimo'])&idx.loc[ids,'activo']).sum())
            avg=float(daily.loc[start:end,ids].mul(idx.loc[ids,'costo_unitario'],axis=1).sum(axis=1).mean()); cog=float(sub.loc[sub.tipo=='salida'].eval('cantidad*costo_unitario').sum()); rotation=cog/avg if avg else None
            clause=','.join(map(str,ids))
            sql=f"SELECT SUM(p.stock_inicial+COALESCE((SELECT SUM(CASE m.tipo WHEN 'entrada' THEN m.cantidad ELSE -m.cantidad END) FROM movimientos m WHERE m.producto_id=p.producto_id AND m.fecha<='{end}'),0)) FROM productos p WHERE p.producto_id IN ({clause})"
            assert db.execute(sql).fetchone()[0]==int(close.sum())
            sql_flow=f"SELECT SUM(CASE WHEN tipo='entrada' THEN cantidad ELSE 0 END),SUM(CASE WHEN tipo='salida' THEN cantidad ELSE 0 END),SUM(CASE WHEN tipo='salida' THEN cantidad*costo_unitario ELSE 0 END) FROM movimientos WHERE producto_id IN ({clause}) AND fecha BETWEEN '{start}' AND '{end}'"
            assert np.allclose(db.execute(sql_flow).fetchone(),[en,sa,cog])
            sql_cut=f"SELECT SUM(stock*costo_unitario),SUM(CASE WHEN activo AND stock<stock_minimo THEN 1 ELSE 0 END) FROM (SELECT p.*,p.stock_inicial+COALESCE((SELECT SUM(CASE m.tipo WHEN 'entrada' THEN m.cantidad ELSE -m.cantidad END) FROM movimientos m WHERE m.producto_id=p.producto_id AND m.fecha<='{end}'),0) stock FROM productos p WHERE p.producto_id IN ({clause})) q"
            assert np.allclose(db.execute(sql_cut).fetchone(),[val,low_count])
            sqlavg=f"SELECT AVG(valor) FROM (SELECT c.fecha,SUM(p.costo_unitario*(p.stock_inicial+COALESCE((SELECT SUM(CASE m.tipo WHEN 'entrada' THEN m.cantidad ELSE -m.cantidad END) FROM movimientos m WHERE m.producto_id=p.producto_id AND m.fecha<=c.fecha),0))) valor FROM calendario c CROSS JOIN productos p WHERE c.fecha BETWEEN '{start}' AND '{end}' AND p.producto_id IN ({clause}) GROUP BY c.fecha)"
            assert abs(db.execute(sqlavg).fetchone()[0]-avg)<1e-7
            rows.append([start,end,label,en,sa,int(close.sum()),round(val,2),low_count,round(avg,6),round(rotation,9) if rotation else 0]); scenarios+=1
    expected=pd.DataFrame(rows,columns=['desde','hasta','filtro','entradas','salidas','stock','valor_pen','productos_bajo','inventario_promedio_pen','rotacion']);expected.to_csv(BASE/'pruebas/resultados_esperados.csv',index=False)
    # Casos corruptos: debe fallar por cada defecto real.
    mutations=[('PK duplicada',lambda x:x['movimientos'].__setitem__('movimiento_id',1)),('FK inválida',lambda x:x['movimientos'].loc.__setitem__((0,'producto_id'),999)),('Cantidad cero',lambda x:x['movimientos'].loc.__setitem__((0,'cantidad'),0)),('Costo negativo',lambda x:x['movimientos'].loc.__setitem__((0,'costo_unitario'),-1)),('Fecha inválida',lambda x:x['movimientos'].loc.__setitem__((0,'fecha'),'2026-01-01')),('Tipo inválido',lambda x:x['movimientos'].loc.__setitem__((0,'tipo'),'ajuste')),('Nulo',lambda x:x['productos'].loc.__setitem__((0,'producto'),None)),('Saldo negativo',lambda x:(x['movimientos'].loc.__setitem__((0,'tipo'),'salida'),x['movimientos'].loc.__setitem__((0,'cantidad'),999999)))]
    rejected=[]
    for name,mutate in mutations:
        x={k:v.copy(deep=True) for k,v in t.items()};mutate(x)
        try: validar(x)
        except (AssertionError,ValueError,TypeError): rejected.append(name)
        else: raise AssertionError(f'No se detectó: {name}')
    rotation=float(m.loc[m.tipo=='salida'].eval('cantidad*costo_unitario').sum()/daily.mul(idx.costo_unitario,axis=1).sum(axis=1).mean())
    result={'estado':'PASS','filas':{k:len(v) for k,v in t.items()},'stock_inicial':int(p.stock_inicial.sum()),'entradas':int(m.loc[m.tipo=='entrada','cantidad'].sum()),'salidas':int(m.loc[m.tipo=='salida','cantidad'].sum()),'stock_final':int(stock.sum()),'valor_inventario_pen':round(value,2),'productos_stock_bajo':low,'porcentaje_bajo':low/len(p),'rotacion_anual':rotation,'saldo_minimo_observado':int(saldo.min()),'escenarios_mensuales_conciliados':scenarios,'datos_corruptos_rechazados':rejected,'motor_SQL_ejecutado':'SQLite '+sqlite3.sqlite_version,'PostgreSQL_ejecutado':False,'DAX_ejecutado':False,'PowerQuery_ejecutado':False,'PowerBI_Desktop_ejecutado':False,'versiones':{'python':sys.version.split()[0],'pandas':pd.__version__,'numpy':np.__version__}}
    (BASE/'pruebas/resultados.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    daily.to_csv(BASE/'pruebas/saldos_diarios_control.csv')
    (BASE/'pruebas/informe.md').write_text('# Informe de ejecución\n\n```json\n'+json.dumps(result,indent=2,ensure_ascii=False)+'\n```\n\nSe validaron tipos, nulos, claves, duplicados, fechas, costos constantes, cantidades y cada saldo ordenado por fecha + ID. Conciliación pandas/SQLite: saldos de 40 productos, flujos de 12 meses, atribución por proveedor, 144 contextos de flujos, stock, valor, stock bajo, costo de salidas y promedio diario (componentes de rotación); 8 alteraciones inválidas detectadas. SQL 03 y las 8 consultas de SQL 04 ejecutadas en SQLite.\n\nLas reglas propuestas en DAX se reproducen en Python; NO se ejecutó el motor DAX. resultados_esperados.csv es el oráculo para comprobar Desktop. No se ejecutaron PostgreSQL ni sus triggers/carga, Power Query, importación TMSL ni renderizado Power BI. Ver esquema_json.json para validación estructural separada del PBIP.\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
