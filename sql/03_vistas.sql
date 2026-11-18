CREATE VIEW v_stock AS
SELECT p.producto_id,p.codigo,p.producto,p.categoria_id,p.proveedor_id,p.activo,p.stock_minimo,p.costo_unitario,
 p.stock_inicial+COALESCE(SUM(CASE m.tipo WHEN 'entrada' THEN m.cantidad ELSE -m.cantidad END),0) AS stock
FROM productos p LEFT JOIN movimientos m ON m.producto_id=p.producto_id
GROUP BY p.producto_id,p.codigo,p.producto,p.categoria_id,p.proveedor_id,p.activo,p.stock_minimo,p.costo_unitario,p.stock_inicial;
CREATE VIEW v_mensual AS
SELECT c.anio_mes, SUM(CASE WHEN m.tipo='entrada' THEN m.cantidad ELSE 0 END) entradas,
 SUM(CASE WHEN m.tipo='salida' THEN m.cantidad ELSE 0 END) salidas
FROM calendario c LEFT JOIN movimientos m ON c.fecha=m.fecha GROUP BY c.anio_mes;
CREATE VIEW v_kpi AS SELECT SUM(stock) stock, SUM(stock*costo_unitario) valor_inventario,
 SUM(CASE WHEN activo THEN 1 ELSE 0 END) productos_activos,
 SUM(CASE WHEN activo AND stock<stock_minimo THEN 1 ELSE 0 END) productos_stock_bajo FROM v_stock;
