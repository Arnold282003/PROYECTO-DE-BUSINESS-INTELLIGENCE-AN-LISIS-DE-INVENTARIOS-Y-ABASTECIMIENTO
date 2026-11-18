# Apertura, ensamblaje alternativo y comprobación

## Estado de la entrega
Generados: PBIP, definición PBIR de **dos páginas y 22 visuales**, modelo TMSL con cuatro tablas, tres relaciones, 17 medidas, consultas M, tema y especificación de campos/posiciones. La fuente CSV y los cálculos de referencia fueron ejecutados. El archivo `pruebas/esquema_json.json` registra validación estructural contra esquemas oficiales, no una prueba de apertura. No se dispone de Power BI Desktop en este entorno Linux.

Requiere Desktop: abrir, refrescar, revisar DAX/M/modelo, aplicar el tema auxiliar y comprobar las interacciones y formatos de segmentadores. No se entrega una captura de Desktop ni se representa una maqueta como si fuese un reporte ejecutado.

Primero seguir la ruta PBIP del README. Solo si el proyecto no abre, usar el montaje siguiente. Si informa un error, conservar el texto del error y la versión de Desktop: la validez JSON no garantiza compatibilidad del motor tabular o del visual.

## 1. Importación CSV en un informe vacío
1. Archivo → Nuevo. Inicio → Transformar datos → Editor de Power Query.
2. Crear consulta en blanco y renombrar `RutaDatos`. Editor avanzado: pegar `powerbi/powerquery/RutaDatos.m`, cambiando la cadena a una ruta absoluta local terminada en `/datos`, sin barra al final. Usar barras `/` aun en Windows.
3. Crear consulta en blanco `fxCSV` y pegar su `.m`. Es una función, no una tabla para cargar.
4. Crear, en este orden, `Categorias`, `Proveedores`, `Calendario`, `Productos`, `Movimientos` pegando cada archivo M homónimo en el Editor avanzado de la consulta. Los nombres distinguen mayúsculas y no llevan tildes.
5. Deshabilitar carga para `Categorias`; habilitar para las otras cuatro tablas. Los tipos están explícitos; no usar la detección automática ni reemplazar errores por cero. La función rechaza nulos obligatorios. Ejecutar `python/validar.py` antes de importar archivos modificados para comprobar además claves y reglas de saldo.
6. Cerrar y aplicar. Esperado: Productos 40, Proveedores 6, Calendario 365, Movimientos 4,000. No cargar los CSV de `pruebas` como fuentes de datos del modelo.

## 2. Modelo
Crear las tres relaciones de `modelo.md`, activas y dirección única. No relacionar directamente Proveedores con Movimientos. Comprobar unicidad en el lado 1. Marcar Calendario como tabla de fechas por `[fecha]`. Desactivar Fecha/hora automática para este archivo en Opciones → Carga de datos. Usar `Calendario[fecha]`, no la jerarquía automática.

Ordenar `Calendario[mes_nombre]` por `[mes]`; `anio_mes` se ordena alfabéticamente porque YYYY-MM coincide con cronología. Configurar las columnas numéricas como **No resumir**; las medidas controlan las agregaciones. Ocultar claves de dimensión y stock_inicial del panel de informe para no confundir apertura con saldo; mostrar temporalmente movimiento_id si hace falta añadirlo a una tabla.

## 3. Medidas
En Movimientos, Modelado → Nueva medida. Pegar **una definición a la vez** de `medidas.dax` (la línea `Nombre =` y su fórmula, sin las demás medidas). Crear en el orden del archivo para resolver dependencias. Usar separadores DAX predeterminados de coma; si Desktop está configurado para separadores regionales, deshabilitar esa opción o adaptar los separadores.

Aplicar los formatos indicados en `medidas.json`: unidades enteras; porcentaje con un decimal; moneda `"S/ "#,0.00`; rotación `0.00" x"`. Las medidas no requieren columnas calculadas DAX. `[cantidad_neta]` e `[importe]` ya provienen de M.

## 4. Diseño de las dos páginas
Crear páginas **Resumen de inventario** y **Movimientos y abastecimiento**, tamaño personalizado 1440 × 900. Fondo `#F2F5FA`, visuales blancos, títulos Segoe UI 12 color `#142D4E`; texto 10–11; tarjetas con valor 28. Importar `powerbi/tema.json` desde Vista → Temas. Entradas en azul petróleo `#147D92`, salidas en ámbar `#EF9D39`. No usar unidades automáticas K/M en las tarjetas de control; moneda con dos decimales.

El archivo `configuracion_visuales.json` contiene para cada visual: página, tipo interno, campos/medidas, orden, filtros y posición exacta (x, y, ancho, alto). Traducir los tipos: `card` = Tarjeta clásica, `slicer` = Segmentador, `clusteredColumnChart` = Columnas agrupadas, `clusteredBarChart` = Barras agrupadas, `tableEx` = Tabla. `Category` es el eje categórico; `Y` son medidas; `Values` son campos de tarjeta, segmentador o tabla. Un campo marcado `true` es medida.

En ambas páginas, colocar arriba tres segmentadores de categoría, proveedor y fecha. Usar `Productos[categoria]`, `Proveedores[proveedor]` y `Calendario[fecha]` (campo fecha simple). Categoría y proveedor: desplegable con selección múltiple; fecha: **Entre**, inicialmente todo 2025. Vista → Sincronización de segmentadores: sincronizar cada uno en las dos páginas y mantenerlos visibles en ambas.

### Página 1
| Visual | Eje/columnas | Valores / regla |
|---|---|---|
| Tarjeta Productos activos | — | Productos activos |
| Tarjeta Unidades al corte | — | Stock actual |
| Tarjeta Productos bajo mínimo | — | Productos stock bajo |
| Tarjeta Inventario al costo | — | Valor inventario |
| Columnas agrupadas mensuales | Calendario[anio_mes], ascendente | Total entradas, Total salidas |
| Barras agrupadas por categoría | Productos[categoria] | Total entradas, Salidas por categoria |
| Tabla stock bajo | Productos[codigo], [producto], [categoria] | Stock actual, Stock minimo, Unidades reposicion, Valor inventario; **filtro visual Requiere reposicion = 1** |

La tabla de stock bajo se evalúa a la fecha de corte, no desde un CSV de saldo final. No cambiar este filtro a una columna de saldo estático.

### Página 2
| Visual | Eje/columnas | Valores / regla |
|---|---|---|
| Cuatro tarjetas | — | Rotacion inventario, Costo salidas, Importe entradas, Unidades reposicion |
| Ranking de barras | Productos[producto] | Total salidas, orden descendente; todos los productos, desplazamiento vertical |
| Barras entradas por proveedor | Proveedores[proveedor] | Total entradas, descendente |
| Columnas comparación | Calendario[anio_mes], ascendente | Total entradas, Total salidas |
| Tabla movimientos | Movimientos[movimiento_id], [fecha], Productos[producto], Movimientos[tipo], [cantidad], [costo_unitario] | **No resumir**; ID descendente; no mezclar medidas de stock en esta tabla |
| Tabla reposición | Productos[producto] | Stock actual, Unidades reposicion; filtro visual Requiere reposicion = 1 |

Usar las pestañas inferiores para navegar. No se necesitan botones adicionales. En Formato → Editar interacciones, seleccionar la tabla de movimientos y establecer **Ninguno** hacia todos los demás visuales; evita que elegir una operación altere los KPI. Mantener filtros de los segmentadores en todos los visuales. No seleccionar tipo de movimiento como filtro de página: cada medida de flujo ya elige su tipo.

## 5. Comprobación en Desktop
Sin filtros deben verse 40 productos, 11,493 unidades al cierre, 8 productos bajo mínimo y S/ 186,631.00 de inventario. Para el año: 52,263 entradas, 49,610 salidas, rotación 4.0798237464. El saldo de apertura es 8,840 unidades.

- Seleccionar un mes: comparar con la fila `Todos` de `pruebas/resultados_esperados.csv` para ese mes.
- Añadir una categoría/proveedor: usar su fila correspondiente en el mismo CSV. Los IDs de categoría/proveedor se encuentran en sus CSV maestros.
- En una tabla temporal colocar `Calendario[anio_mes]` y Stock actual: el total debe mostrar el saldo de diciembre, nunca la suma de los doce saldos.
- Seleccionar marzo–abril: los flujos son solo marzo–abril y stock incluye enero–abril. En junio consultar también la séptima consulta de `sql/04_analisis.sql`.
- Comparar los 40 saldos de fin de año con la última fila de `pruebas/saldos_diarios_control.csv`.
- Una tabla de stock bajo debe mostrar ocho productos al cierre, PRD-001 a PRD-008, y respetar el proveedor/categoría.
- En Vista de consultas DAX, ejecutar los bloques de `powerbi/comprobar.dax` por separado. Los bloques no fueron ejecutados aquí. Si falta esta vista, usar las tablas temporales indicadas arriba.

## 6. PostgreSQL como origen alternativo
Después de crear y cargar la base, crear consulta-función `fxPG` pegando solo el código activo de `PostgreSQL_alternativa.m` (los comentarios de abajo son instrucciones). Cambiar servidor/base. Guardar credenciales en el diálogo de Power BI, no en M.

Reemplazar el código de `fxCSV` por:
```powerquery
(nombre as text, tipos as list) as table =>
    Table.TransformColumnTypes(fxPG(nombre), tipos, "en-US")
```
Mantener las consultas Productos y Movimientos completas: conservan la expansión de categoría y columnas derivadas. La conexión es Import, no DirectQuery. Actualizar y repetir conciliación. Dependiendo de la instalación, Desktop puede solicitar componentes del conector; seguir su diálogo y documentación oficial. No está verificada esta conexión en el entorno de generación.
