# Informe de ejecución

```json
{
  "estado": "PASS",
  "filas": {
    "categorias": 5,
    "proveedores": 6,
    "productos": 40,
    "movimientos": 4000,
    "calendario": 365
  },
  "stock_inicial": 8840,
  "entradas": 52263,
  "salidas": 49610,
  "stock_final": 11493,
  "valor_inventario_pen": 186631.0,
  "productos_stock_bajo": 8,
  "porcentaje_bajo": 0.2,
  "rotacion_anual": 4.079823746439755,
  "saldo_minimo_observado": 13,
  "escenarios_mensuales_conciliados": 144,
  "datos_corruptos_rechazados": [
    "PK duplicada",
    "FK inválida",
    "Cantidad cero",
    "Costo negativo",
    "Fecha inválida",
    "Tipo inválido",
    "Nulo",
    "Saldo negativo"
  ],
  "motor_SQL_ejecutado": "SQLite 3.53.1",
  "PostgreSQL_ejecutado": false,
  "DAX_ejecutado": false,
  "PowerQuery_ejecutado": false,
  "PowerBI_Desktop_ejecutado": false,
  "versiones": {
    "python": "3.12.14",
    "pandas": "2.2.3",
    "numpy": "2.3.5"
  }
}
```

Se validaron tipos, nulos, claves, duplicados, fechas, costos constantes, cantidades y cada saldo ordenado por fecha + ID. Conciliación pandas/SQLite: saldos de 40 productos, flujos de 12 meses, atribución por proveedor, 144 contextos de flujos, stock, valor, stock bajo, costo de salidas y promedio diario (componentes de rotación); 8 alteraciones inválidas detectadas. SQL 03 y las 8 consultas de SQL 04 ejecutadas en SQLite.

Las reglas propuestas en DAX se reproducen en Python; NO se ejecutó el motor DAX. resultados_esperados.csv es el oráculo para comprobar Desktop. No se ejecutaron PostgreSQL ni sus triggers/carga, Power Query, importación TMSL ni renderizado Power BI. Ver esquema_json.json para validación estructural separada del PBIP.

Validación estructural: PASS en 30 documentos PBIP/PBIR/PBISM contra esquemas públicos de Microsoft. Revisión estática: 22 visuales referencian campos/medidas existentes, caben en el lienzo, tres relaciones referencian columnas existentes y el SVG es XML válido. Segunda generación de los cinco CSV produjo hashes SHA-256 idénticos (revision_estatica.json). Estas comprobaciones no ejecutan el motor Power BI.
