import requests
import json
import secrets
import base64
import os
from pathlib import Path

# Config
ZONE_ID = "72731de3f08d42d689f39c81a9e4f42c"
ACCOUNT_ID = "6950e81586db847aaa38425fc72c2ed1"
API_TOKEN = "K2FfgxGYnn4SsPWK18Z1jCAUD2JhXq1B2gkKkLDv"
TUNNEL_NAME = "heyseen-tunnel"
DOMAIN = "heyseen.truyenthong.edu.vn"

HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

def generate_secret():
    # 32 bytes random string, base64 encoded
    random_bytes = secrets.token_bytes(32)
    return base64.b64encode(random_bytes).decode('utf-8')

def main():
    print(f"🚀 Setting up Cloudflare Tunnel '{TUNNEL_NAME}' via API...")
    
    # 1. Check if tunnel exists
    print("Checking existing tunnels...")
    resp = requests.get(
        f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/tunnels",
        headers=HEADERS,
        params={"name": TUNNEL_NAME, "is_deleted": "false"}
    )
    
    if resp.status_code != 200:
        print(f"Error checking tunnels: {resp.text}")
        return

    tunnels = resp.json().get('result', [])
    tunnel_id = None
    tunnel_secret = None
    
    if tunnels:
        print(f"Tunnel '{TUNNEL_NAME}' already exists.")
        tunnel_id = tunnels[0]['id']
        # We cannot retrieve the secret of an existing tunnel. 
        # If we don't have it, we must delete and recreate, or ask user.
        # For automation, let's delete and recreate to be safe (since we need the creds file).
        print("Deleting old tunnel to regenerate credentials...")
        del_resp = requests.delete(
            f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/tunnels/{tunnel_id}",
            headers=HEADERS
        )
        if del_resp.status_code == 200:
            print("Old tunnel deleted.")
        else:
            print(f"Failed to delete tunnel: {del_resp.text}")
            return
        tunnel_id = None # Reset to create new

    # 2. Create Tunnel
    if not tunnel_id:
        print("Creating new tunnel...")
        tunnel_secret = generate_secret()
        
        create_resp = requests.post(
            f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/tunnels",
            headers=HEADERS,
            json={
                "name": TUNNEL_NAME,
                "tunnel_secret": tunnel_secret,
                "config_src": "local" # We manage config locally
            }
        )
        
        if create_resp.status_code != 200:
            print(f"Failed to create tunnel: {create_resp.text}")
            return
            
        data = create_resp.json()['result']
        tunnel_id = data['id']
        print(f"✅ Tunnel Created! ID: {tunnel_id}")

    # 3. Create Credentials File
    print("Saving credentials file...")
    creds = {
        "AccountTag": ACCOUNT_ID,
        "TunnelSecret": tunnel_secret,
        "TunnelID": tunnel_id,
        "TunnelName": TUNNEL_NAME
    }
    
    deploy_dir = Path("deploy")
    deploy_dir.mkdir(exist_ok=True)
    
    creds_path = deploy_dir / f"{tunnel_id}.json"
    with open(creds_path, "w") as f:
        json.dump(creds, f, indent=2)
    print(f"Credentials saved to {creds_path}")

    # 4. Create DNS Record (CNAME)
    print(f"Creating DNS record for {DOMAIN}...")
    
    # Check existing DNS to avoid duplicates
    dns_check = requests.get(
        f"https://api.cloudflare.com/client/v4/zones/{ZONE_ID}/dns_records",
        headers=HEADERS,
        params={"name": DOMAIN}
    )
    
    existing_records = dns_check.json().get('result', [])
    target = f"{tunnel_id}.cfargotunnel.com"
    
    for record in existing_records:
        if record['type'] == 'CNAME' and record['content'] == target:
            print("DNS record already exists and is correct.")
            break
        else:
            print(f"Updating/Deleting existing DNS record: {record['id']}")
            requests.delete(
                f"https://api.cloudflare.com/client/v4/zones/{ZONE_ID}/dns_records/{record['id']}",
                headers=HEADERS
            )
    else:
        # Create new record
        dns_resp = requests.post(
            f"https://api.cloudflare.com/client/v4/zones/{ZONE_ID}/dns_records",
            headers=HEADERS,
            json={
                "type": "CNAME",
                "name": DOMAIN,
                "content": target,
                "proxied": True,
                "comment": "HeySeen Tunnel"
            }
        )
        if dns_resp.status_code == 200:
            print("✅ DNS Record Created!")
        else:
            print(f"Failed to create DNS: {dns_resp.text}")

    # 5. Generate Config YAML
    print("Generating config.yml...")
    config_content = f"""tunnel: {tunnel_id}
credentials-file: {creds_path.absolute()}

ingress:
  # API Endpoints mapped to Backend (5555)
  - hostname: {DOMAIN}
    path: /convert
    service: http://localhost:5555
  - hostname: {DOMAIN}
    path: /status/*
    service: http://localhost:5555
  - hostname: {DOMAIN}
    path: /download/*
    service: http://localhost:5555
  - hostname: {DOMAIN}
    path: /docs
    service: http://localhost:5555
  - hostname: {DOMAIN}
    path: /openapi.json
    service: http://localhost:5555
  - hostname: {DOMAIN}
    path: /health
    service: http://localhost:5555

  # Frontend mapped to Static Server (5556)
  - hostname: {DOMAIN}
    service: http://localhost:5556
  
  # Catch-all
  - service: http_status:404
"""
    
    config_path = deploy_dir / "config.yml"
    with open(config_path, "w") as f:
        f.write(config_content)
    
    print(f"✅ Config saved to {config_path}")
    print("\nSetup Complete! You can now run the tunnel.")

if __name__ == "__main__":
    main()
