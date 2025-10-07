from dbs.db_connections import get_db_connection

    
def upsert_feedback_email(email: str, feedback: str, rate:str) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()

    upsert_query = """
    MERGE FeedbackEmail AS target
    USING (SELECT ? AS Email, ? AS Feedback, ? AS Rate) AS source
    ON target.Email = source.Email
    WHEN MATCHED THEN
        UPDATE SET 
            Feedback = source.Feedback,
            Rate = source.Rate
    WHEN NOT MATCHED THEN
        INSERT (Email, Feedback, Rate)
        VALUES (source.Email, source.Feedback, source.Rate);
    """

    cursor.execute(upsert_query, (email, feedback, rate))
    conn.commit()

    updated = cursor.rowcount    > 0
    cursor.close()
    conn.close()
    return updated

def fetch_all_feedback_email():
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
        SELECT Email, Feedback,Rate, CreatedAt
        FROM FeedbackEmail
        ORDER BY CreatedAt DESC
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    return [
        {"email": row[0], "feedback": row[1], "Rate": row[2],"submitted_at": row[3].isoformat()}
        for row in rows
    ]

