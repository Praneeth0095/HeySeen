# Token is valid!
# Maybe the Account ID is mismatched or permission is missing for Tunnels?
# The errors says "Authentication error" on the /accounts/{id}/tunnels endpoint.
# It could be that the Token does not have "Cloudflare Tunnel" permissions.
# Or "Account Settings" permissions?

# Let's try listing accounts to see what this token can see.
import requests

API_TOKEN = "NhzrJ173o98_-NPgmsVQ_h0p3080tNgceGgMHJlM"

def list_accounts():
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    resp = requests.get("https://api.cloudflare.com/client/v4/accounts", headers=headers)
    print(f"Status: {resp.status_code}")
    print(f"Body: {resp.json()}")

if __name__ == "__main__":
    list_accounts()
