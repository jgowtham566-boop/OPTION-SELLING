import os
import sys
import hashlib
import requests
import dotenv

APP_ID = "GOHBCRZYVM-100"
SECRET_KEY = "VAP9E0SERO"

def exchange_auth_code(code_or_url: str):
    code = code_or_url.strip()
    if "auth_code=" in code:
        code = code.split("auth_code=")[1].split("&")[0].strip()
    
    app_id_hash = hashlib.sha256(f"{APP_ID}:{SECRET_KEY}".encode("utf-8")).hexdigest()
    url = "https://api-t1.fyers.in/api/v3/validate-authcode"
    headers = {"Content-Type": "application/json"}
    payload = {
        "grant_type": "authorization_code",
        "appIdHash": app_id_hash,
        "code": code
    }
    print(f"Exchanging auth_code with appIdHash: {app_id_hash}...")
    resp = requests.post(url, headers=headers, json=payload, timeout=15)
    print("Status:", resp.status_code)
    data = resp.json()
    print("Response:", data)
    
    token = data.get("access_token")
    if token:
        env_path = r"C:\Users\Administrator\WORKSPACE 2\.env"
        # Update .env
        lines = []
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        
        new_lines = []
        replaced = False
        for line in lines:
            if line.startswith("FYERS_ACCESS_TOKEN="):
                new_lines.append(f"FYERS_ACCESS_TOKEN={token}\n")
                replaced = True
            else:
                new_lines.append(line)
        if not replaced:
            new_lines.append(f"FYERS_ACCESS_TOKEN={token}\n")
        
        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        print("Successfully updated FYERS_ACCESS_TOKEN in .env!")
        return token
    else:
        print("Failed to get access_token from FYERS.")
        return None

if __name__ == "__main__":
    if len(sys.argv) > 1:
        exchange_auth_code(sys.argv[1])
    else:
        print("Usage: python exchange_fyers_token.py <auth_code_or_url>")
