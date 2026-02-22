import webbrowser
import urllib.parse
from fyers_apiv3 import fyersModel
from backtest.config import CLIENT_ID, SECRET_KEY, REDIRECT_URL

def generate_token():
    print("="*50)
    print("Fyers Access Token Generator")
    print("="*50)
    
    # Check if config has values
    if CLIENT_ID == "YOUR_CLIENT_ID" or not SECRET_KEY:
        print("Please update backtest/config.py with your CLIENT_ID and SECRET_KEY first.")
        return

    print(f"Using Client ID: {CLIENT_ID}")
    print(f"Using Redirect URI: {REDIRECT_URL}")
    print("-" * 50)

    # Create session model
    session = fyersModel.SessionModel(
        client_id=CLIENT_ID,
        secret_key=SECRET_KEY,
        redirect_uri=REDIRECT_URL,
        response_type="code",
        grant_type="authorization_code"
    )

    # Generate the auth link
    response = session.generate_authcode()
    
    print("\n" + "="*50)
    print("authorize this link in your browser:")
    print(response)
    print("="*50)
    
    # Try to open the link
    try:
        webbrowser.open(response)
    except:
        pass
        
    print("\nAfter logging in, you will be redirected to a URL like:")
    print(f"{REDIRECT_URL}?auth_code=YOUR_AUTH_CODE&state=...")
    print("\nCopy the WHOLE URL from your browser address bar and paste it below.")
    print("-" * 50)
    
    auth_input = input("Enter Full Redirect URL (or just Auth Code): ").strip()
    
    # Extract auth_code if a URL is provided
    if "auth_code=" in auth_input:
        try:
            parsed = urllib.parse.urlparse(auth_input)
            params = urllib.parse.parse_qs(parsed.query)
            if 'auth_code' in params:
                auth_code = params['auth_code'][0]
                print(f"Extracted Auth Code: {auth_code[:10]}...")
            else:
                print("Could not find 'auth_code' in the URL. Trying to use input as is.")
                auth_code = auth_input
        except Exception:
            print("Error parsing URL. Trying to use input as is.")
            auth_code = auth_input
    else:
        auth_code = auth_input
    
    # Set the auth code in the session
    session.set_token(auth_code)
    
    # Generate the access token
    try:
        response = session.generate_token()
        access_token = response['access_token']
        
        print("\n" + "="*50)
        print("SUCCESS! Access Token Generated.")
        print("="*50)
        
        # Auto-update config file
        try:
            with open("backtest/config.py", "r") as f:
                lines = f.readlines()
            
            with open("backtest/config.py", "w") as f:
                for line in lines:
                    if line.startswith("ACCESS_TOKEN ="):
                        f.write(f'ACCESS_TOKEN = "{access_token}"\n')
                    else:
                        f.write(line)
            print("Successfully updated backtest/config.py with your new Access Token!")
            print("="*50)
            print("You can now run the backtest using: python3 -m backtest.main")
            
        except Exception as file_error:
            print(f"Token generated but failed to update file: {file_error}")
            print(f"Here is your token manually:\n{access_token}")
        
    except Exception as e:
        print(f"\nError generating token: {e}")
        print("Please check your inputs and try again.")

if __name__ == "__main__":
    generate_token()
