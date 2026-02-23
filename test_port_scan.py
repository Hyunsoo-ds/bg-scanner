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
        # 400 에러 등은 호출자가 처리할 수 있도록 raise
        if hasattr(e, 'code') and e.code == 400:
             raise e
             
        print(f"Error {method} {url}: {e}")
        if hasattr(e, 'read'):
            print(e.read().decode('utf-8'))
        sys.exit(1)

print("1. Creating Target (scanme.nmap.org)...")
target_domain = 'scanme.nmap.org'
try:
    target_res = request('POST', 'http://localhost:8000/api/targets', {'domain': target_domain})
    target_id = target_res['id']
except Exception as e:
    # 400 에러 발생 시 (이미 존재)
    print("Target already exists. Finding existing target...")
    # 타겟 리스트 조회
    targets = request('GET', 'http://localhost:8000/api/targets?limit=1000')
    target_id = None
    for t in targets:
        if t['domain'] == target_domain:
            target_id = t['id']
            break
    
    if not target_id:
        print("Could not find existing target ID.")
        sys.exit(1)

print(f"Target ID: {target_id}")

print("2. Creating Scan...")
scan_res = request('POST', 'http://localhost:8000/api/scans', {'target_id': target_id})
scan_id = scan_res['id']
print(f"Scan Created: {scan_id}")

print("3. Waiting for scan to complete...")
# Nmap 스캔이 포함되므로 시간이 좀 더 걸릴 수 있음
for i in range(60): 
    scan_status = request('GET', f'http://localhost:8000/api/scans/{scan_id}')
    status = scan_status['status']
    progress = scan_status['progress_percent']
    print(f"Status: {status} ({progress}%)")
    if status == 'completed':
        break
    if status == 'failed':
        print("Scan Failed!")
        sys.exit(1)
    time.sleep(5)

print("4. Fetching Subdomains and Ports...")
for i in range(10): # 포트 스캔이 비동기로 돌기 때문에 약간의 시간 필요
    subdomains = request('GET', f'http://localhost:8000/api/scans/{scan_id}/subdomains')
    found_ports = False
    for sub in subdomains:
        if sub.get('ports'):
            found_ports = True
            break
    
    if found_ports:
        print(f"Found ports after {i+1} attempts")
        break
    
    print(f"Waiting for port scan results... ({i+1}/10)")
    time.sleep(3)

print(f"Found {len(subdomains)} subdomains")

for sub in subdomains:
    print(f"\n[Subdomain] {sub['hostname']} ({sub.get('ip_address', 'N/A')})")
    ports = sub.get('ports', [])
    print(f"  - Open Ports: {len(ports)}")
    for port in ports:
        print(f"    * {port['port_number']}/{port['protocol']} - {port['service_name']} ({port['version']})")
    
    technologies = sub.get('technologies', [])
    print(f"  - Technologies: {len(technologies)}")
    for tech in technologies:
        print(f"    * {tech['name']} (v{tech['version'] or '?'}) - {', '.join(tech.get('categories', []))}")
