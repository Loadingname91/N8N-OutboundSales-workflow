from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/gmail.modify",
]

flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)

auth_url, _ = flow.authorization_url(prompt="consent")
print("Go to this URL:", auth_url)

code = input("Enter the authorization code: ")
flow.fetch_token(code=code)

creds = flow.credentials
print(creds.to_json())
