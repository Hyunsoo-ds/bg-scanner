import urllib.request
import json
import sys

def post(url, data):
    req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'))
    req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req) as f:
            res = f.read().decode('utf-8')
            print(res)
            return json.loads(res)
    except Exception as e:
        print(f"Error: {e}")
        if hasattr(e, 'read'):
            print(e.read().decode('utf-8'))
        sys.exit(1)

print("Creating Target...")
target_res = post('http://localhost:8000/api/targets', {'domain': 'manual-test.com'})
target_id = target_res['id']
print(f"Target Created: {target_id}")

print("Creating Scan...")
scan_res = post('http://localhost:8000/api/scans', {'target_id': target_id})
print(f"Scan Created: {scan_res['id']}")
