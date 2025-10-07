from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Query

from dbs.users import get_user_role

router = APIRouter()

@router.get("/get-user-role")
def get_user_role_endpoint(email: str = Query(..., description="Email ID of the user")):
    role = get_user_role(email)
    if not role:
        raise HTTPException(status_code=404, detail=f"No role found for user: {email}")
    return {"email": email, "role": role}