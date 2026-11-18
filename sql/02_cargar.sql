\set ON_ERROR_STOP on
-- Ejecutar psql desde la raíz inventario-bi. Transacción atómica, falla si ya hay datos.
BEGIN;
\copy categorias FROM 'datos/categorias.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
\copy proveedores FROM 'datos/proveedores.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
\copy calendario FROM 'datos/calendario.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
\copy productos FROM 'datos/productos.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
\copy movimientos FROM 'datos/movimientos.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
COMMIT;
