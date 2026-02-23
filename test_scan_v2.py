import urllib.request
import json
import sys
import time

def request(method, url, data=None):
    req = urllib.request.Request(url, method=method)
    if data:
        req.data = json.dumps(data).encode('utf-8')
    req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req) as f:
            res = f.read().decode('utf-8')
            return json.loads(res)
    except Exception as e:
        print(f"Error {method} {url}: {e}")
        if hasattr(e, 'read'):
            print(e.read().decode('utf-8'))
        sys.exit(1)

print("1. Creating Target...")
target_res = request('POST', 'http://localhost:8000/api/targets', {'domain': 'api-test.com'})
target_id = target_res['id']
print(f"Target Created: {target_id}")

print("2. Creating Scan...")
scan_res = request('POST', 'http://localhost:8000/api/scans', {'target_id': target_id})
scan_id = scan_res['id']
print(f"Scan Created: {scan_id}")

print("3. Waiting for scan to complete...")
for i in range(20):
    scan_status = request('GET', f'http://localhost:8000/api/scans/{scan_id}')
    status = scan_status['status']
    print(f"Status: {status}")
    if status == 'completed':
        break
    time.sleep(2)

print("4. Fetching Subdomains...")
subdomains = request('GET', f'http://localhost:8000/api/scans/{scan_id}/subdomains')
print(f"Found {len(subdomains)} subdomains")
print(subdomains)
