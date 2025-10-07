import pyodbc
import os 
from dbs.db_connections import get_db_connection

def get_user_role(email_id: str) -> str:
    
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
    SELECT TOP 1 r.RoleName
    FROM UserRoles ur
    JOIN Roles r ON ur.RoleId = r.RoleId
    WHERE LOWER(ur.EmailId) = LOWER(?)
    """
    cursor.execute(query, (email_id,))
    row = cursor.fetchone()

    cursor.close()
    conn.close()

    if row:
        return row.RoleName
    else:
        return None