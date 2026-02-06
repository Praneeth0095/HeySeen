# The token returns an empty list of accounts.
# This means the token does not have permissions to LIST accounts, OR it is scoped to a specific account but not this one?
# Actually, if it's fine-grained, maybe it can only access specific resources.
# The Account ID user provided is: 6950e81586db847aaa38425fc72c2ed1

# If the token is valid but returns 0 accounts, it usually means it wasn't granted "Account.Read" or similar.
# But for Tunnels, it needs "Account - Cloudflare Tunnel - Edit".
# And for DNS, "Zone - DNS - Edit".

# If I try to access the specific account directly, maybe it works if I have permission on that resource but not "List Accounts".

# Let's try to verify DNS access on the Zone ID provided.
ZONE_ID = "72731de3f08d42d689f39c81a9e4f42c"

import requests
API_TOKEN = "NhzrJ173o98_-NPgmsVQ_h0p3080tNgceGgMHJlM"

def check_dns():
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    resp = requests.get(f"https://api.cloudflare.com/client/v4/zones/{ZONE_ID}/dns_records", headers=headers)
    print(f"DNS Check Status: {resp.status_code}")
    # print(resp.text[:200]) # dont leak too much

if __name__ == "__main__":
    check_dns()
