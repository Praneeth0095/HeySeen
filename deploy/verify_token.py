# Check if user needs to create a token with specific permissions.
# The previous error "Authentication error" suggests the token might be wrong or lacks permissions.
# However, usually API tokens are long. "NhzrJ173o98_-NPgmsVQ_h0p3080tNgceGgMHJlM" is 40 chars, which is typical.
# Maybe I need to use X-Auth-Key and X-Auth-Email if it's a Global Key?
# But User API Tokens (Bearer) are preferred.

# Let's try to verify the token validity with a simple request.
import requests

API_TOKEN = "NhzrJ173o98_-NPgmsVQ_h0p3080tNgceGgMHJlM"

def verify_token():
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    resp = requests.get("https://api.cloudflare.com/client/v4/user/tokens/verify", headers=headers)
    print(f"Status: {resp.status_code}")
    print(f"Body: {resp.text}")

if __name__ == "__main__":
    verify_token()
