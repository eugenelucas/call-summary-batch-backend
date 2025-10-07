from dbs.db_connections import get_db_connection

def save_token_email(email: str, token: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    insert_query = """
    INSERT INTO Survey (Email, Token)
    VALUES (?, ?)
    """
    cursor.execute(insert_query, (email, token))
    conn.commit()

    cursor.close()
    conn.close()
    
def update_feedback(token: str, feedback: str) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    update_query = """
        UPDATE Survey
        SET Feedback = ?
        WHERE Token = ?
    """
    cursor.execute(update_query, (feedback, token))
    conn.commit()
    updated = cursor.rowcount > 0
    cursor.close()
    conn.close()
    return updated

def get_all_feedback():
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
        SELECT Email, Feedback, CreatedAt
        FROM Survey
        WHERE Feedback IS NOT NULL
        ORDER BY CreatedAt DESC
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    return [
        {"email": row[0], "feedback": row[1], "submitted_at": row[2].isoformat()}
        for row in rows
    ]

def get_email_by_token(token: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT Email FROM Survey WHERE Token = ?"
    cursor.execute(query, (token,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row[0] if row else None