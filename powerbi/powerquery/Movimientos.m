let
    Base = fxCSV("movimientos",{{"movimiento_id",Int64.Type},{"fecha",type date},{"producto_id",Int64.Type},{"tipo",type text},{"cantidad",Int64.Type},{"costo_unitario",Currency.Type}}),
    Signo = Table.AddColumn(Base,"cantidad_neta",each if [tipo]="entrada" then [cantidad] else if [tipo]="salida" then -[cantidad] else error "Tipo inválido",Int64.Type),
    Importe = Table.AddColumn(Signo,"importe",each [cantidad]*[costo_unitario],Currency.Type)
in Importe
