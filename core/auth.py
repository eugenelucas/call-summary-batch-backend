# auth.py

from fastapi import Header, HTTPException, status, Request
from msal import ConfidentialClientApplication
from dotenv import load_dotenv
import os
import jwt
import requests
from jwt import PyJWKClient

load_dotenv(override=True)

# MSAL configuration
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
AUTHORITY = os.getenv("AUTHORITY")
REDIRECT_URI = os.getenv("REDIRECT_URI")
SCOPE = [os.getenv("SCOPE")]

# Create MSAL app instance
msal_app = ConfidentialClientApplication(
    client_id=CLIENT_ID,
    client_credential=CLIENT_SECRET,
    authority=AUTHORITY
)

# Generate auth URL
def get_auth_url():
    return msal_app.get_authorization_request_url(
        scopes=SCOPE,
        redirect_uri=REDIRECT_URI
    )

# Handle redirect and token acquisition
def handle_auth_redirect(code: str):
    result = msal_app.acquire_token_by_authorization_code(
        code,
        scopes=SCOPE,
        redirect_uri=REDIRECT_URI
    )
    return result

TENANT_ID = os.getenv("TENANT_ID")  # add this to your .env file

def verify_bearer_token(authorization: str = Header(...)) -> dict:
    # if not authorization.startswith("Bearer "):
    #     raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization header")

    try:
        # token = authorization.split("Bearer ")[1]
        # # Get the JWKS URL from Azure AD
        # openid_config_url = f"https://login.microsoftonline.com/{TENANT_ID}/v2.0/.well-known/openid-configuration"
        # openid_config = requests.get(openid_config_url).json()
        # jwks_uri = openid_config["jwks_uri"]

        # # Load public keys and verify the token
        # jwk_client = PyJWKClient(jwks_uri)
        # # signing_key = jwk_client.get_signing_key_from_jwt(token)
        # decoded = jwt.decode(token, options={"verify_signature": False})
        # return decoded
        return "true"

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Token validation failed")
