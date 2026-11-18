-- Stock al cierre del conjunto completo (2025-12-31).
SELECT * FROM v_stock ORDER BY codigo;
-- Flujos mensuales; nunca sumar saldos mensuales.
SELECT * FROM v_mensual ORDER BY anio_mes;
SELECT * FROM v_stock WHERE activo AND stock<stock_minimo ORDER BY stock;
SELECT p.codigo,p.producto,SUM(m.cantidad) salidas FROM movimientos m JOIN productos p USING(producto_id) WHERE m.tipo='salida' GROUP BY p.codigo,p.producto ORDER BY salidas DESC;
SELECT * FROM v_kpi;
-- Atribución al proveedor principal: las salidas NO representan compras al proveedor.
SELECT pr.proveedor,m.tipo,COUNT(*) movimientos,SUM(m.cantidad) unidades,SUM(m.cantidad*m.costo_unitario) importe
FROM movimientos m JOIN productos p USING(producto_id) JOIN proveedores pr USING(proveedor_id) GROUP BY pr.proveedor,m.tipo ORDER BY pr.proveedor,m.tipo;
-- Saldo histórico: cambiar la fecha literal, incluye toda la historia previa.
SELECT p.codigo,p.stock_inicial+COALESCE(SUM(CASE m.tipo WHEN 'entrada' THEN m.cantidad ELSE -m.cantidad END),0) stock
FROM productos p LEFT JOIN movimientos m ON p.producto_id=m.producto_id AND m.fecha<='2025-06-30' GROUP BY p.codigo,p.stock_inicial;
-- Rotación del año: costo de salidas / promedio diario de valor al cierre.
WITH diario AS (
 SELECT c.fecha,p.producto_id,p.costo_unitario*(p.stock_inicial+COALESCE((SELECT SUM(CASE m.tipo WHEN 'entrada' THEN m.cantidad ELSE -m.cantidad END) FROM movimientos m WHERE m.producto_id=p.producto_id AND m.fecha<=c.fecha),0)) valor
 FROM calendario c CROSS JOIN productos p
), promedio AS (SELECT AVG(valor) valor FROM (SELECT fecha,SUM(valor) valor FROM diario GROUP BY fecha) q)
SELECT (SELECT SUM(cantidad*costo_unitario) FROM movimientos WHERE tipo='salida')/NULLIF(valor,0) rotacion FROM promedio;
