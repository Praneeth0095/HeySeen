import requests
API_TOKEN = "NhzrJ173o98_-NPgmsVQ_h0p3080tNgceGgMHJlM"
ZONE_ID = "72731de3f08d42d689f39c81a9e4f42c"
PROVIDED_ACCOUNT_ID = "6950e81586db847aaa38425fc72c2ed1"

def check_zone_details():
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    resp = requests.get(f"https://api.cloudflare.com/client/v4/zones/{ZONE_ID}", headers=headers)
    print(f"Zone Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()['result']
        real_account_id = data['account']['id']
        print(f"Zone Account ID: {real_account_id}")
        print(f"User Provided ID: {PROVIDED_ACCOUNT_ID}")
        
        if real_account_id != PROVIDED_ACCOUNT_ID:
            print("❌ Mismatch!")
        else:
            print("✅ Match!")

if __name__ == "__main__":
    check_zone_details()
