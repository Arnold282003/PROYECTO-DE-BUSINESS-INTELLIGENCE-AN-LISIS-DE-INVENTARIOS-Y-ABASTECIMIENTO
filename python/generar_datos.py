"""Datos reproducibles; importes PEN, costos constantes y unidades enteras."""
from pathlib import Path
import numpy as np
import pandas as pd
BASE = Path(__file__).resolve().parents[1]
def main():
    rng = np.random.default_rng(2025)
    out = BASE / 'datos'; out.mkdir(exist_ok=True)
    cats = pd.DataFrame({'categoria_id':range(1,6),'categoria':['Abarrotes','Bebidas','Limpieza','Cuidado personal','Papelería']})
    prov = pd.DataFrame({'proveedor_id':range(1,7),'proveedor':['Abastos Rímac SAC','Bebidas del Valle SAC','Limpieza Norte SAC','Cuidado Andino SAC','Papeles Lima SAC','Mayorista Pacífico SAC'],'ciudad':['Lima','Lima','Callao','Lima','Lima','Callao']})
    names = [['Arroz 1 kg','Azúcar 1 kg','Fideos 500 g','Lentejas 500 g','Aceite 1 L','Avena 400 g','Sal 1 kg','Atún 170 g'],['Agua 625 ml','Agua 2.5 L','Gaseosa 500 ml','Gaseosa 3 L','Néctar 1 L','Té 500 ml','Bebida isotónica 500 ml','Agua con gas 500 ml'],['Detergente 800 g','Lejía 1 L','Lavavajilla 500 g','Desinfectante 1 L','Esponja x3','Bolsa basura x10','Limpiavidrios 500 ml','Jabón ropa 200 g'],['Jabón tocador 90 g','Champú 400 ml','Pasta dental 90 g','Cepillo dental','Papel higiénico x4','Toallas húmedas x40','Alcohol 250 ml','Acondicionador 400 ml'],['Cuaderno A4','Lapicero azul x12','Lápiz x12','Borrador x6','Papel A4 x500','Cinta adhesiva','Folder manila x10','Marcador negro']]
    products=[]; movements=[]
    dates=pd.date_range('2025-01-01','2025-12-31')
    for i in range(1,41):
        cat=(i-1)//8+1; segment='Alta' if i<=12 else 'Media' if i<=32 else 'Baja'
        cost=int(rng.integers(180,2600)); minimum=int(rng.integers(25,61)); initial=minimum*4 if segment!='Baja' else minimum*12
        products.append([i,f'PRD-{i:03}',names[cat-1][(i-1)%8],cat,6 if i%7==0 else cat,cost/100,round(cost*1.35)/100,minimum,initial,True])
        stock=initial
        event_days=sorted(rng.choice(np.arange(364),99,replace=False).tolist()+[364])
        for j,day in enumerate(event_days):
            demand=int(rng.integers(14,38) if segment=='Alta' else rng.integers(5,17) if segment=='Media' else rng.integers(1,4))
            if j==99 and i<=8:
                target=minimum//2
                if stock>target: typ='salida'; qty=stock-target
                else: typ='entrada'; qty=max(1,target-stock)
            elif stock<demand+minimum or (j%19==0 and segment!='Baja'):
                typ='entrada'; qty=minimum*int(rng.integers(3,7))
            else: typ='salida'; qty=min(stock,demand)
            assert qty>0
            stock+=qty if typ=='entrada' else -qty
            assert stock>=0
            movements.append([dates[day].strftime('%Y-%m-%d'),i,typ,qty,cost/100])
    p=pd.DataFrame(products,columns=['producto_id','codigo','producto','categoria_id','proveedor_id','costo_unitario','precio_referencia','stock_minimo','stock_inicial','activo'])
    m=pd.DataFrame(movements,columns=['fecha','producto_id','tipo','cantidad','costo_unitario']).sort_values(['fecha','producto_id'],kind='stable').reset_index(drop=True)
    m.insert(0,'movimiento_id',np.arange(1,len(m)+1))
    cal=pd.DataFrame({'fecha':dates.strftime('%Y-%m-%d'),'anio':dates.year,'mes':dates.month,'anio_mes':dates.strftime('%Y-%m'),'mes_nombre':[ ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'][d.month-1] for d in dates]})
    for name,df in [('categorias',cats),('proveedores',prov),('productos',p),('movimientos',m),('calendario',cal)]: df.to_csv(out/f'{name}.csv',index=False,encoding='utf-8',float_format='%.2f',lineterminator='\n')
    print('Generados: 4000 movimientos, 40 productos, 5 categorías, 6 proveedores, 365 fechas. Semilla 2025.')
if __name__=='__main__': main()
