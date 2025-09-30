from google_auth_oauthlib.flow import InstalledAppFlow
import json

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/gmail.modify",
]


def main():
    flow = InstalledAppFlow.from_client_secrets_file(
        "client_secret.json", SCOPES, redirect_uri="http://localhost:8080/"
    )

    # Generate the authorization URL
    auth_url, _ = flow.authorization_url(prompt="consent")

    print("Please go to this URL and authorize the application:")
    print(auth_url)
    print("-" * 30)

    # Wait for the user to paste the authorization code
    code = input("Enter the authorization code from the browser: ")

    # Exchange the code for a token
    flow.fetch_token(code=code)

    creds = flow.credentials
    token_json_string = creds.to_json()

    with open("token.json", "w") as token_file:
        token_file.write(token_json_string)

    print("\nSUCCESS! Token saved to token.json")
    print(f"\nToken content:\n{token_json_string}")


if __name__ == "__main__":
    main()
