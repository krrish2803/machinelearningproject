import os
import requests
import base64
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
FITBIT_CLIENT_ID = os.getenv("FITBIT_CLIENT_ID")
FITBIT_CLIENT_SECRET = os.getenv("FITBIT_CLIENT_SECRET")
FITBIT_REDIRECT_URI = os.getenv("FITBIT_REDIRECT_URI")

# Authorization URL (for reference)
auth_url = f"https://www.fitbit.com/oauth2/authorize?response_type=code&client_id={FITBIT_CLIENT_ID}&redirect_uri={FITBIT_REDIRECT_URI}&scope=activity+heartrate"

print(f"1. Visit this URL to get the code: {auth_url}")
print("2. After authorizing, copy the 'code' from the redirect URI (e.g., http://localhost:8080?code=your_code)")

# Get the authorization code from user input
auth_code = input("Enter the authorization code: ")

# Exchange code for token
token_url = "https://api.fitbit.com/oauth2/token"
auth_header = f"Basic {base64.b64encode(f'{FITBIT_CLIENT_ID}:{FITBIT_CLIENT_SECRET}'.encode()).decode()}"
data = {
    "client_id": FITBIT_CLIENT_ID,
    "grant_type": "authorization_code",
    "redirect_uri": FITBIT_REDIRECT_URI,
    "code": auth_code
}
headers = {
    "Authorization": auth_header,
    "Content-Type": "application/x-www-form-urlencoded"
}

response = requests.post(token_url, data=data, headers=headers)
if response.status_code == 200:
    token_data = response.json()
    access_token = token_data["access_token"]
    refresh_token = token_data["refresh_token"]
    print(f"Access Token: {access_token}")
    print(f"Refresh Token: {refresh_token}")
    # Update .env file
    with open(".env", "a") as f:
        f.write(f"\nFITBIT_ACCESS_TOKEN={access_token}")
        f.write(f"\nFITBIT_REFRESH_TOKEN={refresh_token}")
    print("Tokens saved to .env file.")
else:
    print(f"Error: {response.status_code} - {response.text}")