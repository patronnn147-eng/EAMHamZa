import urllib.request, urllib.parse, base64, json

host = 'http://localhost:9090'
token = 'sqa_8916bef9a37bd94652264d41a9f1529f2a3b86c6'

def call(path):
    url = host + path
    req = urllib.request.Request(url, headers={'Authorization': 'Basic ' + base64.b64encode((token + ':').encode()).decode()})
    with urllib.request.urlopen(req, timeout=45) as r:
        text = r.read().decode()
    return text

for path in ['/api/system/health', '/api/projects/search?ps=20', '/api/project_branches/list?project=eamsagemcom-phase-2']:
    print('---', path)
    try:
        body = call(path)
        print(body[:5000])
    except Exception as e:
        print('ERR', e)
