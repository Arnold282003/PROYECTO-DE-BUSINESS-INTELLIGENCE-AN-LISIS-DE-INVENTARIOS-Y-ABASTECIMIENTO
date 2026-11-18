(nombre as text, tipos as list) as table =>
let
    Fuente = Csv.Document(File.Contents(RutaDatos & "/" & nombre & ".csv"),[Delimiter=",",Encoding=65001,QuoteStyle=QuoteStyle.Csv]),
    Cabeceras = Table.PromoteHeaders(Fuente,[PromoteAllScalars=true]),
    Limpio = Table.TransformColumns(Cabeceras,List.Transform(Table.ColumnNames(Cabeceras),(c)=>{c,each if _ = null then null else Text.Trim(Text.Clean(Text.From(_))),type nullable text})),
    SinVacios = Table.ReplaceValue(Limpio,"",null,Replacer.ReplaceValue,Table.ColumnNames(Limpio)),
    Validado = if List.AnyTrue(List.Transform(Table.ToRows(SinVacios),(r)=>List.Contains(r,null))) then error "Hay valores nulos obligatorios en " & nombre else SinVacios,
    Tipado = Table.TransformColumnTypes(Validado,tipos,"en-US")
in Tipado
