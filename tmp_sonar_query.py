import urllib.request, urllib.parse, base64, json

host = 'http://localhost:9090'
token = 'sqa_8916bef9a37bd94652264d41a9f1529f2a3b86c6'
params = urllib.parse.urlencode({'componentKeys': 'eamsagemcom-phase-2', 'branch': 'Phase_2', 'ps': 100, 'p': 1})
url = host + '/api/issues/search?' + params
req = urllib.request.Request(url, headers={'Authorization': 'Basic ' + base64.b64encode((token + ':').encode()).decode()})
with urllib.request.urlopen(req, timeout=45) as r:
    data = r.read().decode()

obj = json.loads(data)
print('total', obj.get('paging', {}).get('total'))
for issue in obj.get('issues', [])[:20]:
    print(issue.get('key'), '|', issue.get('severity'), '|', issue.get('type'), '|', issue.get('component'), '|', issue.get('message'))
