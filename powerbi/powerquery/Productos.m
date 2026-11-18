let
    Base = fxCSV("productos",{{"producto_id",Int64.Type},{"codigo",type text},{"producto",type text},{"categoria_id",Int64.Type},{"proveedor_id",Int64.Type},{"costo_unitario",Currency.Type},{"precio_referencia",Currency.Type},{"stock_minimo",Int64.Type},{"stock_inicial",Int64.Type},{"activo",type logical}}),
    Union = Table.NestedJoin(Base,{"categoria_id"},Categorias,{"categoria_id"},"Cat",JoinKind.LeftOuter),
    Resultado = Table.ExpandTableColumn(Union,"Cat",{"categoria"},{"categoria"})
in Resultado
