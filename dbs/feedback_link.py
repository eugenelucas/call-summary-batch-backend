from dbs.db_connections import get_db_connection

def save_token_email(email: str, token: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    insert_query = """
    INSERT INTO FeedbackLink (Email, Token)
    VALUES (?, ?)
    """
    cursor.execute(insert_query, (email, token))
    conn.commit()

    cursor.close()
    conn.close()
    
def update_feedback(token: str, feedback: str, rate: str) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    update_query = """
        UPDATE FeedbackLink
        SET Feedback = ?, Rate = ?
        WHERE Token = ?
    """
    cursor.execute(update_query, (feedback, rate, token))
    conn.commit()
    updated = cursor.rowcount > 0
    cursor.close()
    conn.close()
    return updated

def fetch_all_feedback():
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
        SELECT Email, Feedback,Rate, CreatedAt
        FROM FeedbackLink
        WHERE Rate IS NOT NULL
        ORDER BY CreatedAt DESC
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    return [
        {"email": row[0], "feedback": row[1],"rate":row[2], "submitted_at": row[3].isoformat()}
        for row in rows
    ]

def get_email_by_token(token: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT Email FROM FeedbackLink WHERE Token = ?"
    cursor.execute(query, (token,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row[0] if row else None