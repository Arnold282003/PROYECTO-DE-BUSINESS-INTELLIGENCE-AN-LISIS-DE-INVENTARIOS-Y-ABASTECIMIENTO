"""Validación JSON Schema oficial; requiere jsonschema. No valida DAX/M/TMSL."""
from pathlib import Path
from urllib.request import urlopen
from urllib.parse import urljoin, urldefrag
import json, hashlib
import jsonschema
from referencing import Registry, Resource
BASE=Path(__file__).resolve().parents[1]; cache=BASE/'pruebas/schemas';cache.mkdir(exist_ok=True)
def retrieve(uri):
    uri=urldefrag(uri)[0]; path=cache/(hashlib.sha256(uri.encode()).hexdigest()+'.json')
    if path.exists(): s=json.loads(path.read_text())
    else:
        s=json.load(urlopen(uri,timeout=45));path.write_text(json.dumps(s,ensure_ascii=False,indent=2),encoding='utf-8')
    # Embedded schemas sometimes omit dialect; needed for referencing.
    return Resource.from_contents(s,default_specification=__import__('referencing.jsonschema',fromlist=['DRAFT7']).DRAFT7)
def main():
    results=[];registry=Registry(retrieve=retrieve)
    files=sorted((BASE/'powerbi').rglob('*.json'))+sorted((BASE/'powerbi').rglob('*.pbip'))+sorted((BASE/'powerbi').rglob('*.pbir'))+sorted((BASE/'powerbi').rglob('*.pbism'))
    for f in files:
        doc=json.loads(f.read_text());uri=doc.get('$schema') if isinstance(doc,dict) else None
        if not uri:continue
        try:
            resource=retrieve(uri); reg=registry.with_resource(uri,resource)
            validator=jsonschema.Draft7Validator({'$ref':uri},registry=reg)
            errors=[str(e.message)+' @ '+str(list(e.path)) for e in validator.iter_errors(doc)]
        except Exception as e: errors=[str(e)]
        results.append({'archivo':str(f.relative_to(BASE)),'errores':errors})
        if errors:print(f.name,errors[:2],flush=True)
    result={'estado':'PASS' if all(not x['errores'] for x in results) else 'FAIL','archivos':len(results),'alcance':'JSON Schema Microsoft; no ejecución de Power BI, M, DAX o TMSL','resultados':results}
    (BASE/'pruebas/esquema_json.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8');print(result['estado'],result['archivos'])
    assert result['estado']=='PASS'
if __name__=='__main__':main()
