"""Genera M, DAX, modelo TMSL y dos páginas PBIR. No ejecuta Power BI."""
from pathlib import Path
import json, argparse, uuid
BASE=Path(__file__).resolve().parents[1]; OUT=BASE/'powerbi'
def write(p,s):
    p=OUT/p;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s,encoding='utf-8')
def js(p,v):write(p,json.dumps(v,ensure_ascii=False,indent=2))
def schema(kind,version='1.0.0'): return f'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/{kind}/{version}/schema.json'
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--datos',default='C:/inventario-bi/datos');args=parser.parse_args();ruta=args.datos.replace('\\','/').rstrip('/').replace('"','""')
    types={
     'Categorias':[('categoria_id','Int64.Type'),('categoria','type text')],
     'Proveedores':[('proveedor_id','Int64.Type'),('proveedor','type text'),('ciudad','type text')],
     'Productos':[('producto_id','Int64.Type'),('codigo','type text'),('producto','type text'),('categoria_id','Int64.Type'),('proveedor_id','Int64.Type'),('costo_unitario','Currency.Type'),('precio_referencia','Currency.Type'),('stock_minimo','Int64.Type'),('stock_inicial','Int64.Type'),('activo','type logical')],
     'Calendario':[('fecha','type date'),('anio','Int64.Type'),('mes','Int64.Type'),('anio_mes','type text'),('mes_nombre','type text')],
     'Movimientos':[('movimiento_id','Int64.Type'),('fecha','type date'),('producto_id','Int64.Type'),('tipo','type text'),('cantidad','Int64.Type'),('costo_unitario','Currency.Type')]
    }
    expr={'RutaDatos':f'"{ruta}" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]', 'fxCSV':'''(nombre as text, tipos as list) as table =>
let
    Fuente = Csv.Document(File.Contents(RutaDatos & "/" & nombre & ".csv"),[Delimiter=",",Encoding=65001,QuoteStyle=QuoteStyle.Csv]),
    Cabeceras = Table.PromoteHeaders(Fuente,[PromoteAllScalars=true]),
    Limpio = Table.TransformColumns(Cabeceras,List.Transform(Table.ColumnNames(Cabeceras),(c)=>{c,each if _ = null then null else Text.Trim(Text.Clean(Text.From(_))),type nullable text})),
    SinVacios = Table.ReplaceValue(Limpio,"",null,Replacer.ReplaceValue,Table.ColumnNames(Limpio)),
    Validado = if List.AnyTrue(List.Transform(Table.ToRows(SinVacios),(r)=>List.Contains(r,null))) then error "Hay valores nulos obligatorios en " & nombre else SinVacios,
    Tipado = Table.TransformColumnTypes(Validado,tipos,"en-US")
in Tipado'''}
    for name,cols in types.items():
        type_str='{'+','.join('{"'+c+'",'+t+'}' for c,t in cols)+'}'
        query=f'fxCSV("{name.lower()}",{type_str})'
        if name=='Productos': query='let\n    Base = '+query+',\n    Union = Table.NestedJoin(Base,{"categoria_id"},Categorias,{"categoria_id"},"Cat",JoinKind.LeftOuter),\n    Resultado = Table.ExpandTableColumn(Union,"Cat",{"categoria"},{"categoria"})\nin Resultado'
        if name=='Movimientos':query='let\n    Base = '+query+',\n    Signo = Table.AddColumn(Base,"cantidad_neta",each if [tipo]="entrada" then [cantidad] else if [tipo]="salida" then -[cantidad] else error "Tipo inválido",Int64.Type),\n    Importe = Table.AddColumn(Signo,"importe",each [cantidad]*[costo_unitario],Currency.Type)\nin Importe'
        expr[name]=query
    for name,q in expr.items():write(Path('powerquery')/(name+'.m'),q+'\n')
    write(Path('powerquery/PostgreSQL_alternativa.m'),'''// Crear como consulta fxPG, configurar servidor/base; no guardar credenciales en código.
(tabla as text) as table =>
let Fuente=PostgreSQL.Database("localhost:5432","inventario_bi"),
    Datos=Fuente{[Schema="public",Item=tabla]}[Data]
in Datos
// Reemplazar fxCSV por: (nombre as text, tipos as list) as table =>
// Table.TransformColumnTypes(fxPG(nombre),tipos,"en-US")
// Mantener Productos y Movimientos para conservar uniones y columnas derivadas.
''')
    measures={
     'Total entradas':('COALESCE(CALCULATE(SUM(Movimientos[cantidad]), Movimientos[tipo] = "entrada"), 0)','#,0','Flujo de entradas dentro de fechas seleccionadas.'),
     'Total salidas':('COALESCE(CALCULATE(SUM(Movimientos[cantidad]), Movimientos[tipo] = "salida"), 0)','#,0','Flujo de salidas dentro del periodo.'),
     'Stock actual':('''VAR Corte = MAX(Calendario[fecha])
RETURN SUM(Productos[stock_inicial]) + COALESCE(CALCULATE(
    SUM(Movimientos[cantidad_neta]),
    REMOVEFILTERS(Movimientos[tipo]),
    FILTER(ALL(Calendario), Calendario[fecha] <= Corte)
), 0)''','#,0','Saldo al fin de la última fecha visible. Ignora inicio del filtro de fechas; apertura anterior a 2025-01-01.'),
     'Valor inventario':('SUMX(VALUES(Productos[producto_id]), [Stock actual] * CALCULATE(MAX(Productos[costo_unitario])))','"S/ "#,0.00','Valor a costo fijo por producto; no precio de venta.'),
     'Productos activos':('CALCULATE(COUNTROWS(Productos), Productos[activo] = TRUE())','#,0','Catálogo activo filtrado por categoría/proveedor, independiente de movimientos del periodo.'),
     'Productos stock bajo':('COALESCE(COUNTROWS(FILTER(FILTER(Productos, Productos[activo] = TRUE()), [Stock actual] < Productos[stock_minimo])), 0)','#,0','Activos con saldo estrictamente menor al mínimo; incluye saldo cero.'),
     'Porcentaje stock bajo':('DIVIDE([Productos stock bajo], [Productos activos], 0)','0.0%','Misma población activa en numerador y denominador.'),
     'Salidas por categoria':('[Total salidas]','#,0','Usar Productos[categoria] como eje; no suprime filtros.'),
     'Costo salidas':('COALESCE(CALCULATE(SUM(Movimientos[importe]), Movimientos[tipo] = "salida"), 0)','"S/ "#,0.00','Costo de unidades retiradas durante el periodo.'),
     'Inventario promedio':('AVERAGEX(VALUES(Calendario[fecha]), [Valor inventario])','"S/ "#,0.00','Media de saldos valorizados al cierre de cada día seleccionado; incluye días sin movimientos.'),
     'Rotacion inventario':('DIVIDE([Costo salidas], [Inventario promedio])','0.00" x"','Veces en el periodo; sin anualizar. BLANK si denominador cero.'),
     'Requiere reposicion':('IF(HASONEVALUE(Productos[producto_id]), IF(SELECTEDVALUE(Productos[activo]) = TRUE() && [Stock actual] < SELECTEDVALUE(Productos[stock_minimo]), 1, 0))','0','Indicador para filtrar tablas de productos = 1.'),
     'Unidades reposicion':('SUMX(FILTER(Productos, Productos[activo] = TRUE()), MAX(0, Productos[stock_minimo] - [Stock actual]))','#,0','Brecha hasta mínimo, no punto óptimo de pedido.'),
     'Importe entradas':('COALESCE(CALCULATE(SUM(Movimientos[importe]), Movimientos[tipo] = "entrada"), 0)','"S/ "#,0.00','Importe de recepciones; compras aproximadas, sin órdenes ni facturas.'),
     'Ranking salidas':('RANKX(ALLSELECTED(Productos[producto]), [Total salidas], , DESC, DENSE)','0','Ranking dentro de selección, con empates.'),
     'Stock minimo':('SUM(Productos[stock_minimo])','#,0','Umbral; usar por producto.'),
     'Comparacion neta':('[Total entradas] - [Total salidas]','#,0','Flujo neto del periodo; no es el stock.'),
    }
    write(Path('medidas.dax'),'\n\n'.join('// '+desc+'\n'+n+' =\n'+v for n,(v,fmt,desc) in measures.items())+'\n')
    js(Path('medidas.json'),{n:{'expression':v,'formatString':f,'description':d} for n,(v,f,d) in measures.items()})
    model={'name':'Inventario','compatibilityLevel':1567,'model':{'culture':'es-PE','defaultPowerBIDataSourceVersion':'powerBI_V3','sourceQueryCulture':'en-US','dataAccessOptions':{'legacyRedirects':True,'returnErrorValuesAsNull':True},'expressions':[],'tables':[],'relationships':[]}}
    for n in ['RutaDatos','fxCSV','Categorias']:model['model']['expressions'].append({'name':n,'kind':'m','expression':expr[n]})
    for n in ['Productos','Proveedores','Calendario','Movimientos']:
        cols=list(types[n])
        if n=='Productos':cols+=[('categoria','type text')]
        if n=='Movimientos':cols+=[('cantidad_neta','Int64.Type'),('importe','Currency.Type')]
        table={'name':n,'columns':[],'partitions':[{'name':n,'mode':'import','source':{'type':'m','expression':expr[n]}}]}
        for c,t in cols:
            col={'name':c,'sourceColumn':c,'dataType':{'Int64.Type':'int64','type text':'string','type date':'dateTime','Currency.Type':'decimal','type logical':'boolean'}[t],'summarizeBy':'none'}
            if c.endswith('_id') or c=='stock_inicial':col['isHidden']=True
            if t=='Currency.Type':col['formatString']='"S/ "#,0.00'
            if t=='type date':col['formatString']='dd/MM/yyyy'
            if n=='Calendario' and c=='fecha':col['isKey']=True
            if n=='Calendario' and c=='mes_nombre':col['sortByColumn']='mes'
            table['columns'].append(col)
        if n=='Calendario':table['dataCategory']='Time'
        if n=='Movimientos':table['measures']=[{'name':name,'expression':v,'formatString':fmt,'description':desc,'displayFolder':'Inventario'} for name,(v,fmt,desc) in measures.items()]
        model['model']['tables'].append(table)
    for ft,fc,tt,tc in [('Productos','proveedor_id','Proveedores','proveedor_id'),('Movimientos','producto_id','Productos','producto_id'),('Movimientos','fecha','Calendario','fecha')]:
        model['model']['relationships'].append({'name':str(uuid.uuid5(uuid.NAMESPACE_URL,ft+fc+tt)),'fromTable':ft,'fromColumn':fc,'toTable':tt,'toColumn':tc,'fromCardinality':'many','toCardinality':'one','crossFilteringBehavior':'oneDirection','isActive':True})
    js(Path('Inventario.SemanticModel/model.bim'),model)
    js(Path('Inventario.SemanticModel/definition.pbism'),{'$schema':'https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json','version':'1.0','settings':{}})
    js(Path('Inventario.pbip'),{'$schema':'https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json','version':'1.0','artifacts':[{'report':{'path':'Inventario.Report'}}],'settings':{'enableAutoRecovery':True}})
    js(Path('Inventario.Report/definition.pbir'),{'$schema':'https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json','version':'4.0','datasetReference':{'byPath':{'path':'../Inventario.SemanticModel'}}})
    root=Path('Inventario.Report/definition')
    js(root/'version.json',{'$schema':schema('versionMetadata'),'version':'4.0.0'})
    js(root/'report.json',{'$schema':schema('report','2.0.0'),'themeCollection':{'baseTheme':{'name':'CY24SU10','reportVersionAtImport':'4.0.0','type':'SharedResources'}},'settings':{'useStylableVisualContainerHeader':True,'exportDataMode':'AllowSummarized','defaultDrillFilterOtherVisuals':True}})
    js(root/'pages/pages.json',{'$schema':schema('pagesMetadata'),'pageOrder':['Resumen','Abastecimiento'],'activePageName':'Resumen'})
    def field(tab,col,measure=False):return {('Measure' if measure else 'Column'):{'Expression':{'SourceRef':{'Entity':tab}},'Property':col}}
    def lit(x):return {'expr':{'Literal':{'Value':x}}}
    def projection(tab,col,measure=False):return {'field':field(tab,col,measure),'queryRef':tab+'.'+col,'nativeQueryRef':col}
    specs=[]
    def visual(page,key,kind,title,x,y,w,h,roles,sort=None,low=False):
        q={'queryState':{role:{'projections':[projection(*f) for f in fs]} for role,fs in roles.items()}}
        if sort:q['sortDefinition']={'sort':[{'field':field(*sort[:3]),'direction':sort[3]}],'isDefaultSort':False}
        obj={'$schema':schema('visualContainer','2.4.0'),'name':key,'position':{'x':x,'y':y,'z':len(specs),'width':w,'height':h,'tabOrder':len(specs)},'visual':{'visualType':kind,'query':q,'visualContainerObjects':{'title':[{'properties':{'show':lit('true'),'text':lit("'"+title+"'"),'fontSize':lit('12D'),'fontColor':{'solid':{'color':lit("'#142D4E'")}}}}],'background':[{'properties':{'show':lit('true'),'color':{'solid':{'color':lit("'#FFFFFF'")}},'transparency':lit('0D')}}]}}}
        if low:
            obj['filterConfig']={'filters':[{'name':page+key+'SoloReposicion','field':field('Movimientos','Requiere reposicion',True),'type':'Advanced','filter':{'Version':2,'From':[{'Name':'m','Entity':'Movimientos','Type':0}],'Where':[{'Condition':{'Comparison':{'ComparisonKind':0,'Left':{'Measure':{'Expression':{'SourceRef':{'Source':'m'}},'Property':'Requiere reposicion'}},'Right':{'Literal':{'Value':'1L'}}}}}]}}]}
        if kind=='slicer':obj['visual']['syncGroup']={'groupName':key,'fieldChanges':True,'filterChanges':True}
        js(root/f'pages/{page}/visuals/{key}/visual.json',obj)
        specs.append({'pagina':page,'visual':key,'tipo':kind,'titulo':title,'x':x,'y':y,'ancho':w,'alto':h,'campos':roles,'orden':sort,'filtro':'Requiere reposicion = 1' if low else None})
    M=lambda n:('Movimientos',n,True)
    for page,title in [('Resumen','Resumen de inventario'),('Abastecimiento','Movimientos y abastecimiento')]:
        js(root/f'pages/{page}/page.json',{'$schema':schema('page','2.0.0'),'name':page,'displayName':title,'displayOption':'FitToPage','width':1440,'height':900,'objects':{'background':[{'properties':{'color':{'solid':{'color':lit("'#F2F5FA'")}},'transparency':lit('0D')}}]}})
        for key,label,x,w,tab,col in [('Categoria','Categoría',24,400,'Productos','categoria'),('Proveedor','Proveedor principal',440,480,'Proveedores','proveedor'),('Fecha','Periodo / fecha de corte',936,480,'Calendario','fecha')]:
            visual(page,key,'slicer',label,x,20,w,80,{'Values':[(tab,col,False)]})
    for j,(title,metric) in enumerate([('Productos activos','Productos activos'),('Unidades al corte','Stock actual'),('Productos bajo mínimo','Productos stock bajo'),('Inventario al costo · PEN','Valor inventario')]):visual('Resumen','KPI'+str(j),'card',title,24+j*352,116,336,116,{'Values':[M(metric)]})
    visual('Resumen','Mensual','clusteredColumnChart','Entradas y salidas · unidades del periodo',24,248,864,290,{'Category':[('Calendario','anio_mes',False)],'Y':[M('Total entradas'),M('Total salidas')]},('Calendario','anio_mes',False,'Ascending'))
    visual('Resumen','Categorias','clusteredBarChart','Movimientos por categoría',904,248,512,290,{'Category':[('Productos','categoria',False)],'Y':[M('Total entradas'),M('Salidas por categoria')]})
    visual('Resumen','BajoStock','tableEx','Productos con stock bajo · saldo al corte',24,554,1392,322,{'Values':[('Productos','codigo',False),('Productos','producto',False),('Productos','categoria',False),M('Stock actual'),M('Stock minimo'),M('Unidades reposicion'),M('Valor inventario')]},low=True)
    for j,(title,metric) in enumerate([('Rotación · veces en periodo','Rotacion inventario'),('Costo salidas · PEN','Costo salidas'),('Recepciones · PEN','Importe entradas'),('Brecha de reposición · unidades','Unidades reposicion')]):visual('Abastecimiento','KPI'+str(j),'card',title,24+j*352,116,336,108,{'Values':[M(metric)]})
    visual('Abastecimiento','Ranking','clusteredBarChart','Productos ordenados por salidas',24,240,448,260,{'Category':[('Productos','producto',False)],'Y':[M('Total salidas')]},('Movimientos','Total salidas',True,'Descending'))
    visual('Abastecimiento','EntradasProveedor','clusteredBarChart','Entradas por proveedor · unidades',488,240,448,260,{'Category':[('Proveedores','proveedor',False)],'Y':[M('Total entradas')]},('Movimientos','Total entradas',True,'Descending'))
    visual('Abastecimiento','Comparacion','clusteredColumnChart','Entradas vs. salidas · unidades',952,240,464,260,{'Category':[('Calendario','anio_mes',False)],'Y':[M('Total entradas'),M('Total salidas')]},('Calendario','anio_mes',False,'Ascending'))
    visual('Abastecimiento','Detalle','tableEx','Movimientos del periodo',24,516,864,360,{'Values':[('Movimientos','movimiento_id',False),('Movimientos','fecha',False),('Productos','producto',False),('Movimientos','tipo',False),('Movimientos','cantidad',False),('Movimientos','costo_unitario',False)]},('Movimientos','movimiento_id',False,'Descending'))
    visual('Abastecimiento','Reposicion','tableEx','Reposición al corte',904,516,512,360,{'Values':[('Productos','producto',False),M('Stock actual'),M('Unidades reposicion')]},low=True)
    js(Path('configuracion_visuales.json'),specs)
    js(Path('tema.json'),{'name':'Inventario · Lima','dataColors':['#147D92','#EF9D39','#4673C8','#2E9675','#985B9E'],'background':'#F2F5FA','foreground':'#142D4E','tableAccent':'#147D92','textClasses':{'title':{'fontFace':'Segoe UI','fontSize':12},'label':{'fontFace':'Segoe UI','fontSize':10},'callout':{'fontFace':'Segoe UI','fontSize':28}}})
    # Incluir tema y desactivar selección de operaciones hacia indicadores.
    theme=json.loads((OUT/'tema.json').read_text())
    js(Path('Inventario.Report/StaticResources/RegisteredResources/InventarioTema.json'),theme)
    rp=root/'report.json'; report=json.loads((OUT/rp).read_text())
    report['themeCollection']['customTheme']={'name':'InventarioTema','reportVersionAtImport':'4.0.0','type':'RegisteredResources'}
    report['resourcePackages']=[{'name':'RegisteredResources','type':'RegisteredResources','items':[{'name':'InventarioTema','path':'InventarioTema.json','type':'CustomTheme'}]}]
    js(rp,report)
    pp=root/'pages/Abastecimiento/page.json'; page=json.loads((OUT/pp).read_text())
    page['visualInteractions']=[{'source':'Detalle','target':v['visual'],'type':'NoFilter'} for v in specs if v['pagina']=='Abastecimiento' and v['visual']!='Detalle']
    js(pp,page)
    write(Path('.gitignore'),'**/.pbi/localSettings.json\n**/.pbi/cache.abf\n')
    print('PBIP, TMSL, PBIR, M y DAX generados. RutaDatos = '+args.datos+'. Requieren validación Desktop.')
if __name__=='__main__': main()
