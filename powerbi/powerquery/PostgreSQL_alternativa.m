// Crear como consulta fxPG, configurar servidor/base; no guardar credenciales en código.
(tabla as text) as table =>
let Fuente=PostgreSQL.Database("localhost:5432","inventario_bi"),
    Datos=Fuente{[Schema="public",Item=tabla]}[Data]
in Datos
// Reemplazar fxCSV por: (nombre as text, tipos as list) as table =>
// Table.TransformColumnTypes(fxPG(nombre),tipos,"en-US")
// Mantener Productos y Movimientos para conservar uniones y columnas derivadas.
