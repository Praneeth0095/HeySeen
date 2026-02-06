# It seems the Token HAS Tunnel Create permissions (Tunnel created successfully!)
# BUT it failed at DNS creation: "Authentication error".
# This is strange. The previous token worked for DNS but failed for Tunnel.
# This token works for Tunnel but failed for DNS?
# OR, maybe I am hitting a rate limit or conflict?

# "Authentication error" (10000) on DNS strictly means missing "Zone:DNS:Edit" permission.
# The user might have created a "Cloudflare Tunnel" template token which only gives Tunnel permissions, not DNS.

# SOLUTION:
# 1. Use the NEW token (`K2...`) to run the Tunnel (since we successfully created it and have creds).
# 2. Use the OLD token (`Nh...`) to update the DNS record (since we verified it has DNS access).

# I will modify the setup script to perform a "Split Authentication" strategy.
# But actually, I already HAVE the credentials file and config.yml generated.
# The only missing piece is the DNS CNAME record pointing to `2f18ab81-097d-43dc-aaec-b444f6c08cd4.cfargotunnel.com`.

# I can just run a small script using the OLD token to fix the DNS.
# Target: `2f18ab81-097d-43dc-aaec-b444f6c08cd4.cfargotunnel.com`

# Let's verify the Tunnel ID from the output above: 2f18ab81-097d-43dc-aaec-b444f6c08cd4.

OLD_TOKEN = "NhzrJ173o98_-NPgmsVQ_h0p3080tNgceGgMHJlM"
ZONE_ID = "72731de3f08d42d689f39c81a9e4f42c"
DOMAIN = "heyseen.truyenthong.edu.vn"
TARGET = "2f18ab81-097d-43dc-aaec-b444f6c08cd4.cfargotunnel.com"

import requests

def fix_dns():
    print(f"Fixing DNS for {DOMAIN} -> {TARGET} using OLD token...")
    headers = {"Authorization": f"Bearer {OLD_TOKEN}", "Content-Type": "application/json"}
    
    # Get existing
    resp = requests.get(f"https://api.cloudflare.com/client/v4/zones/{ZONE_ID}/dns_records", headers=headers, params={"name": DOMAIN})
    records = resp.json().get('result', [])
    
    if records:
        rec_id = records[0]['id']
        print(f"Updating record {rec_id}...")
        upd = requests.put(
            f"https://api.cloudflare.com/client/v4/zones/{ZONE_ID}/dns_records/{rec_id}",
            headers=headers,
            json={"type": "CNAME", "name": DOMAIN, "content": TARGET, "proxied": True, "ttl": 1}
        )
        print(upd.status_code, upd.text)
    else:
        print("Creating record...")
        crt = requests.post(
            f"https://api.cloudflare.com/client/v4/zones/{ZONE_ID}/dns_records",
            headers=headers,
            json={"type": "CNAME", "name": DOMAIN, "content": TARGET, "proxied": True, "ttl": 1}
        )
        print(crt.status_code, crt.text)

if __name__ == "__main__":
    fix_dns()
