from fastapi import APIRouter
from fastapi import Request
from fastapi.responses import RedirectResponse
from fastapi import Request
import os
from core.auth import get_auth_url, handle_auth_redirect

router = APIRouter()


FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


@router.get("/")
def home():
    return RedirectResponse(get_auth_url())

@router.get("/redirect")
def redirect(request: Request):
    code = request.query_params.get("code")
    if not code:
        return RedirectResponse(url=f"{FRONTEND_URL}/auth/error?reason=AuthorizationCodeMissing")

    result = handle_auth_redirect(code)

    if "access_token" in result:
        access_token = result["access_token"]
        return RedirectResponse(url=f"{FRONTEND_URL}/auth/callback?token={access_token}")
    else:
        error_description = result.get("error_description", "Unknown error")
        return RedirectResponse(url=f"{FRONTEND_URL}/auth/error?reason={error_description}")   
    