import time
import subprocess
import re
import requests
import sys
from pathlib import Path

# Config
ZONE_ID = "72731de3f08d42d689f39c81a9e4f42c"
API_TOKEN = "NhzrJ173o98_-NPgmsVQ_h0p3080tNgceGgMHJlM"
DOMAIN = "heyseen.truyenthong.edu.vn"
LOCAL_PORT = 5555

def get_quick_tunnel_url():
    print(f"Starting cloudflared tunnel for port {LOCAL_PORT}...")
    # Start cloudflared
    cmd = f"cloudflared tunnel --url http://localhost:{LOCAL_PORT}"
    process = subprocess.Popen(
        cmd, 
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    # Read output to find URL
    url = None
    print("Waiting for Quick Tunnel URL...")
    
    start_time = time.time()
    while time.time() - start_time < 30: # 30s timeout
        line = process.stdout.readline()
        if not line:
            break
        print(f"cloudflared: {line.strip()}")
        
        match = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', line)
        if match:
            url = match.group(0)
            break
            
    if not url:
        print("❌ Failed to get tunnel URL.")
        process.terminate()
        sys.exit(1)
        
    print(f"✅ Tunnel URL: {url}")
    return url, process

def update_dns(target_url):
    print(f"Updating DNS {DOMAIN} -> {target_url}...")
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # 1. Get existing record
    resp = requests.get(
        f"https://api.cloudflare.com/client/v4/zones/{ZONE_ID}/dns_records",
        headers=headers,
        params={"name": DOMAIN}
    )
    
    records = resp.json().get('result', [])
    record_id = None
    
    # Extract hostname from URL (remove https://)
    target_host = target_url.replace("https://", "").replace("/", "")
    
    if records:
        record_id = records[0]['id']
        print(f"Updating existing record {record_id}...")
        update_resp = requests.put(
            f"https://api.cloudflare.com/client/v4/zones/{ZONE_ID}/dns_records/{record_id}",
            headers=headers,
            json={
                "type": "CNAME",
                "name": DOMAIN,
                "content": target_host,
                "proxied": True,
                "ttl": 1
            }
        )
    else:
        print("Creating new record...")
        update_resp = requests.post(
            f"https://api.cloudflare.com/client/v4/zones/{ZONE_ID}/dns_records",
            headers=headers,
            json={
                "type": "CNAME",
                "name": DOMAIN,
                "content": target_host,
                "proxied": True,
                "ttl": 1
            }
        )
        
    if update_resp.status_code == 200:
        print("✅ DNS Updated Successfully!")
    else:
        print(f"❌ DNS Update Failed: {update_resp.text}")

def main():
    url, process = get_quick_tunnel_url()
    try:
        update_dns(url)
        print("\n🚀 Service is LIVE at: https://heyseen.truyenthong.edu.vn")
        print("(Press Ctrl+C to stop)")
        process.wait()
    except KeyboardInterrupt:
        print("\nStopping tunnel...")
        process.terminate()

if __name__ == "__main__":
    main()
