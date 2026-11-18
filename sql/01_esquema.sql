-- PostgreSQL 14+. Ejecutar en una base dedicada vacía.
BEGIN;
CREATE TABLE categorias (categoria_id integer PRIMARY KEY, categoria text NOT NULL UNIQUE CHECK (btrim(categoria)<>''));
CREATE TABLE proveedores (proveedor_id integer PRIMARY KEY, proveedor text NOT NULL UNIQUE, ciudad text NOT NULL);
CREATE TABLE calendario (fecha date PRIMARY KEY CHECK(fecha BETWEEN DATE '2025-01-01' AND DATE '2025-12-31'), anio integer NOT NULL CHECK(anio=2025), mes integer NOT NULL CHECK(mes BETWEEN 1 AND 12), anio_mes char(7) NOT NULL, mes_nombre varchar(3) NOT NULL, CHECK (anio=EXTRACT(YEAR FROM fecha) AND mes=EXTRACT(MONTH FROM fecha)), CHECK (anio_mes=to_char(fecha,'YYYY-MM')));
CREATE TABLE productos (
 producto_id integer PRIMARY KEY, codigo varchar(12) NOT NULL UNIQUE, producto text NOT NULL,
 categoria_id integer NOT NULL REFERENCES categorias, proveedor_id integer NOT NULL REFERENCES proveedores,
 costo_unitario numeric(12,2) NOT NULL CHECK(costo_unitario>0), precio_referencia numeric(12,2) NOT NULL CHECK(precio_referencia>=costo_unitario),
 stock_minimo integer NOT NULL CHECK(stock_minimo>0), stock_inicial integer NOT NULL CHECK(stock_inicial>=0), activo boolean NOT NULL,
 UNIQUE(producto_id,costo_unitario)
);
CREATE TABLE movimientos (
 movimiento_id integer PRIMARY KEY, fecha date NOT NULL REFERENCES calendario,
 producto_id integer NOT NULL REFERENCES productos,
 tipo varchar(7) NOT NULL CHECK(tipo IN ('entrada','salida')), cantidad integer NOT NULL CHECK(cantidad>0),
 costo_unitario numeric(12,2) NOT NULL CHECK(costo_unitario>0),
 FOREIGN KEY(producto_id,costo_unitario) REFERENCES productos(producto_id,costo_unitario)
);
CREATE INDEX ix_mov_producto_fecha ON movimientos(producto_id,fecha,movimiento_id);
CREATE INDEX ix_mov_fecha ON movimientos(fecha);
-- Protege el saldo después de cada movimiento, incluidos movimientos retroactivos.
-- Trigger diferido: valida estado final de la transacción. Serializa por producto.
CREATE FUNCTION comprobar_saldo() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE pid integer;
BEGIN
 FOR pid IN SELECT DISTINCT x FROM unnest(ARRAY[CASE WHEN TG_OP<>'INSERT' THEN OLD.producto_id END,CASE WHEN TG_OP<>'DELETE' THEN NEW.producto_id END]) x WHERE x IS NOT NULL ORDER BY x LOOP
  PERFORM 1 FROM productos WHERE producto_id=pid FOR UPDATE;
  IF EXISTS (SELECT 1 FROM (SELECT p.stock_inicial+SUM(CASE m.tipo WHEN 'entrada' THEN m.cantidad ELSE -m.cantidad END) OVER (ORDER BY m.fecha,m.movimiento_id ROWS UNBOUNDED PRECEDING) saldo FROM movimientos m JOIN productos p USING(producto_id) WHERE m.producto_id=pid) q WHERE saldo<0) THEN
   RAISE EXCEPTION 'Inventario negativo para producto %',pid;
  END IF;
 END LOOP;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER saldo_no_negativo AFTER INSERT OR UPDATE OR DELETE ON movimientos DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION comprobar_saldo();
-- Stock inicial inmutable una vez que existen movimientos.
CREATE FUNCTION proteger_apertura() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NEW.stock_inicial<>OLD.stock_inicial AND EXISTS (SELECT 1 FROM movimientos WHERE producto_id=OLD.producto_id) THEN RAISE EXCEPTION 'Stock inicial con movimientos: no modificable'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER apertura_fija BEFORE UPDATE ON productos FOR EACH ROW EXECUTE FUNCTION proteger_apertura();
COMMIT;
