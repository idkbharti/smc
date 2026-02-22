from fyers_apiv3 import fyersModel
from backtest.config import CLIENT_ID, SECRET_KEY, REDIRECT_URL, ACCESS_TOKEN

def exchange_code():
    with open("exchange_log.txt", "w") as log:
        log.write("Attempting to exchange Auth Code for Access Token...\n")
        
        # The user pasted the Auth Code into the ACCESS_TOKEN field
        auth_code = ACCESS_TOKEN
        log.write(f"Auth Code Length: {len(auth_code)}\n")
        
        session = fyersModel.SessionModel(
            client_id=CLIENT_ID,
            secret_key=SECRET_KEY,
            redirect_uri=REDIRECT_URL,
            response_type="code",
            grant_type="authorization_code"
        )
        
        session.set_token(auth_code)
        
        try:
            response = session.generate_token()
            log.write(f"Response: {response}\n")
            
            if "access_token" in response:
                access_token = response['access_token']
                log.write("\nSUCCESS! Access Token Generated.\n")
                
                # Update config file
                with open("backtest/config.py", "r") as f:
                    lines = f.readlines()
                
                with open("backtest/config.py", "w") as f:
                    for line in lines:
                        if line.startswith("ACCESS_TOKEN ="):
                            f.write(f'ACCESS_TOKEN = "{access_token}"\n')
                        else:
                            f.write(line)
                log.write("Updated backtest/config.py with the new Access Token.\n")
            else:
                log.write("Failed to generate token.\n")
                
        except Exception as e:
            log.write(f"Error: {e}\n")

if __name__ == "__main__":
    exchange_code()
