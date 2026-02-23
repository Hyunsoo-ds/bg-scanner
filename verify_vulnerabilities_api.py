import requests
import json

BASE_URL = "http://localhost:8000/api"
SCAN_ID = "9e39158a-88fd-4a1f-b8f9-552b4300fe2e"

def main():
    print(f"Checking vulnerabilities for Scan ID: {SCAN_ID}")
    try:
        res = requests.get(f"{BASE_URL}/scans/{SCAN_ID}/vulnerabilities")
        if res.status_code == 200:
            data = res.json()
            print(f"Status: {res.status_code}")
            print(json.dumps(data, indent=2))
        else:
            print(f"Failed: {res.status_code} - {res.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
