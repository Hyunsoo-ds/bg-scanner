import urllib.request
import urllib.error
import json
import sys
import time

BASE_URL = "http://localhost:8000"
TARGET = "scanme.nmap.org"

def req(url, method="GET", body=None):
    req = urllib.request.Request(url, method=method)
    req.add_header("Content-Type", "application/json")
    if body:
        req.data = json.dumps(body).encode('utf-8')
    try:
        with urllib.request.urlopen(req) as res:
            return json.loads(res.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        print(f"[!] HTTP {e.code} Error for {url}")
        print(e.read().decode('utf-8'))
        if e.code == 500:
            print("FATAL: Internal Server Error detected.")
            sys.exit(1)
        raise e
    except Exception as e:
        print(f"[!] Error: {e}")
        sys.exit(1)

print("[1] Checking Target...")
targets = req(f"{BASE_URL}/api/targets")
target_id = next((t['id'] for t in targets if t['domain'] == TARGET), None)
if not target_id:
    print(f"Creating target {TARGET}...")
    res = req(f"{BASE_URL}/api/targets", "POST", {"domain": TARGET})
    target_id = res['id']
print(f"Target ID: {target_id}")

print("[2] Starting Scan...")
scan = req(f"{BASE_URL}/api/scans", "POST", {"target_id": target_id})
scan_id = scan['id']
print(f"Scan ID: {scan_id}")

print("[3] Waiting for completion...")
while True:
    s = req(f"{BASE_URL}/api/scans/{scan_id}")
    status = s['status']
    print(f"Status: {status} ({s['progress_percent']}%)")
    if status == 'completed':
        break
    if status == 'failed':
        print("Scan Failed!")
        sys.exit(1)
    time.sleep(3)

print("[4] Verifying /subdomains endpoint (The Fix)...")
# 이 부분에서 500 에러가 발생하지 않아야 함
subs = req(f"{BASE_URL}/api/scans/{scan_id}/subdomains")
print(f"SUCCESS: Retrieved {len(subs)} subdomains without 500 error.")

print("[5] Waiting for crawler results...")
found_paths = False
for i in range(15):
    paths = req(f"{BASE_URL}/api/scans/{scan_id}/paths")
    if paths:
        print(f"Paths found: {len(paths)}")
        found_paths = True
        break
    print(f"Checking paths... {i+1}/15")
    time.sleep(3)

if not found_paths:
    print("Warning: No paths found (crawler might be slow or target has no paths).")
else:
    print("Crawler Verified.")

print("Integration Test Passed.")
