import requests
import time
import sys

BASE_URL = "http://localhost:8000/api"
DOMAIN = "hackthissite.org"

def main():
    print(f"Checking targets for {DOMAIN}...")
    target_id = None
    try:
        targets = requests.get(f"{BASE_URL}/targets").json()
        for t in targets:
            if t['domain'] == DOMAIN:
                target_id = t['id']
                break
    except Exception as e:
        print(f"Failed to connect to API: {e}")
        return

    if not target_id:
        print("Creating target...")
        res = requests.post(f"{BASE_URL}/targets", json={"domain": DOMAIN})
        target_id = res.json()['id']
    
    print(f"Target ID: {target_id}")

    print("Creating/Getting latest scan...")
    # List scans and find one or create
    scans = requests.get(f"{BASE_URL}/scans").json()
    scan_id = None
    for s in scans:
        if s['target_id'] == target_id:
            scan_id = s['id']
            break
            
    if not scan_id:
        res = requests.post(f"{BASE_URL}/scans", json={"target_id": target_id})
        scan_id = res.json()['id']
        print(f"Created new scan: {scan_id}")
    else:
        print(f"Using existing scan: {scan_id}")

    # Ensure we have a path to test
    # We can't easily inject a path via API (read-only usually populated by crawler)
    # But we can try to find one. If none, we might be stuck unless we run crawler/subfinder first.
    # Let's check existing paths.
    paths_res = requests.get(f"{BASE_URL}/scans/{scan_id}/paths")
    paths = paths_res.json()['items']
    
    path_id_to_test = None
    if not paths:
        print("No paths found. Running subdomain scan first to get something... (might take long)")
        # This might be too long. 
        # Alternatively, direct database injection? Or assume user will do it.
        # Let's try to inject a path directly if I can, but I can't via API.
        # I'll try to run Subdomain scan quickly if I can.
        # Or better, just create a dummy path using python code accessing DB directly?
        # No, better to test API.
        pass
    else:
        path_id_to_test = paths[0]['id']
        print(f"Found existing path: {paths[0]['url']}")

    # If still no path, we can't test "selected paths".
    # But wait, I can use the `run_nuclei_scan` directly from `test_scan.py` style script if I want to verify the worker.
    # But testing integration requires API.
    
    # If no path, let's try to use sql to insert one?
    # Or just tell user "Please run subdomain/crawl first".
    # Actually I can modify the crawler/subdomain task to be quick?
    # Let's just create a test path directly in DB using sqlalchemy if I can import app.
    pass

    if path_id_to_test:
        print(f"Triggering Nuclei scan on path {path_id_to_test}...")
        res = requests.post(
            f"{BASE_URL}/scans/{scan_id}/actions",
            json={
                "subdomain_ids": [],
                "path_ids": [path_id_to_test],
                "action": "nuclei_scan"
            }
        )
        print(res.text)
    else:
        print("Skipping trigger (no path). Please run a scan/crawl first.")

if __name__ == "__main__":
    main()
