# Formatos Power BI: decisión técnica
Documentación oficial consultada el 17/11/2026:

- [PBIP: descripción y apertura de proyectos](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-overview)
- [Carpeta de informe y formato PBIR](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-report)
- [Carpeta del modelo semántico: TMSL y TMDL](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-dataset)
- [TMDL: definición y serialización](https://learn.microsoft.com/en-us/analysis-services/tmdl/tmdl-overview)
- [Formato PBIR mejorado](https://learn.microsoft.com/en-us/power-bi/developer/embedded/projects-enhanced-report-format)

PBIP referencia las carpetas de informe/modelo; no contiene datos importados. PBIR distribuye páginas y visuales en archivos JSON con esquemas públicos. TMDL representa el modelo tabular como texto dividido por objetos; sustituye a model.bim, no debe coexistir con él como definición activa.

**Decisión:** proyecto PBIP, informe PBIR y modelo TMSL `model.bim`, con `definition.pbism` versión 1.0. Esta combinación está documentada por Microsoft y permite construir la definición sin simular un binario PBIX. Se investigó TMDL, pero no se incluye una segunda definición del modelo para evitar divergencia y ambigüedad. Desde Desktop, una vez revisado el proyecto, es posible guardar el modelo en TMDL si la versión lo permite.

Se descargaron esquemas oficiales mediante sus URLs `$schema`; quedan en `pruebas/schemas` con nombres hash para permitir repetir la validación sin descargas adicionales. El script usa esos esquemas y sus referencias. Validación JSON no prueba expresiones DAX/M, importación TMSL, presencia de recursos internos de una versión concreta ni comportamiento visual. Requiere validación final en Desktop. `pruebas/esquema_json.json` registra el resultado estructural.
