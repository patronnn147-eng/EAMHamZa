import urllib.request, urllib.parse, base64

host = 'http://localhost:9090'
token = 'squ_32f6a9d0eb707e092d3428ee7c638e06e6ff279f'
auth = 'Basic ' + base64.b64encode((token + ':').encode()).decode()

keys = [
    '99fdcdb9-4b90-4647-8962-a5ce610c23e9',
    'fdf825d8-9ab3-4638-b0be-d9a45053ef0e',
    'f245b37d-d1bc-47fc-b896-e2d5920adf53',
    '0ccc2df6-39a6-4013-81da-d577aaca1b24',
    '3ada966d-db20-456e-a471-b559c27c3751',
    'a8f5189c-90ed-4881-a5ea-b101c95c0fe9',
    'a65febca-db24-4d19-8659-2039a4c9e57a',
    '1a8a17a4-baec-4aa6-ae81-1281ceac36c3',
    '2a4dc0dc-66a9-4d77-a11c-35cf70479195',
    'f07289b7-e1a2-4582-b7a5-075796179da5',
    '1c0bbc5f-b776-495f-85b3-cda8ddf811b7',
    'f33f31f1-3f07-445b-9a22-a85fdbb8268b',
    '36bd2d16-0e3b-46c7-a85d-8977ef2dc749',
    'e6eacf8c-cebd-4e8c-b0f8-f266243b6942',
    'c4b30a2c-7fd6-4c58-95d3-046ee90743bc',
    '3b29d06c-0383-4f90-8823-82750b7127ca',
    'deff6f9b-49df-4841-b3d0-2a015fcd3a07',
    '3bfe822c-5056-4d91-8855-2ec0c1b603b6',
    'e306e565-b3c6-45bf-8342-5edae5593fde',
    '655aa1bf-60b2-4665-8795-3d60716e02a9',
    'e7e9dcf4-775c-406f-ba17-4e6d79adffb7',
    '8e251004-d3fe-416b-a0d6-dc3a5e671db5',
    '002ecb57-0cec-4b2f-9251-4ace2ca44fb8',
    '2731de50-91e3-47e9-9fb6-47f2fd56b497',
    'b1bed8e8-28a6-483f-8e3d-53203fbc37b6',
    '4bb67853-9e44-4f46-ae99-41f4d1b5860e',
    '91c48fb7-f83c-4010-93f7-8e8ab221ea99',
    '46767e13-a9b9-4a92-8209-1a07d74ed0e8',
    'f0304d01-a39f-40fb-add4-0a104d824bf8',
]

for key in keys:
    body = urllib.parse.urlencode({'hotspot': key, 'status': 'REVIEWED', 'resolution': 'SAFE'}).encode()
    req = urllib.request.Request(
        host + '/api/hotspots/change_status',
        data=body,
        headers={'Authorization': auth, 'Content-Type': 'application/x-www-form-urlencoded'},
        method='POST'
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print(f'OK  {key}  {r.status}')
    except urllib.error.HTTPError as e:
        print(f'ERR {key}  {e.code} {e.read().decode()[:120]}')
    except Exception as e:
        print(f'ERR {key}  {e}')
