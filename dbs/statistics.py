from dbs.db_connections import get_db_connection
import json

def insert_statistics(audiofilename: str, duration:int = None, agentrating: int = None, sentirating: int = None,
                      anomaly: bool = None, anomaly_reasons: list[str] | None = None) -> int:
    """
    Insert a record into the Statistic table.
    anomaly_reasons can now be a list of strings, stored as JSON in the database.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Convert list to JSON string if not None
    anomaly_reasons_json = json.dumps(anomaly_reasons) if anomaly_reasons else None

    # Check if the record already exists
    cursor.execute("SELECT ID FROM Statistic WHERE AudioFileName = ?", (audiofilename,))
    row = cursor.fetchone()

    if row:
        # Update existing record
        record_id = row[0]
        update_query = """
            UPDATE Statistic
            SET Duration = ?,
                AgentRating = ?,
                SentiRating = ?,
                Anomaly = ?,
                AnomalyReason = ?
            WHERE ID = ?
        """
        cursor.execute(update_query, (duration, agentrating, sentirating, anomaly, anomaly_reasons_json, record_id))
    else:
        # Insert new record
        insert_query = """
            INSERT INTO Statistic (AudioFileName, Duration, AgentRating, SentiRating, Anomaly, AnomalyReason)
            OUTPUT INSERTED.ID
            VALUES (?, ?, ?, ?, ?, ?)
        """
        cursor.execute(insert_query, (audiofilename, duration, agentrating, sentirating, anomaly, anomaly_reasons_json))
        record_id = cursor.fetchone()[0]

    conn.commit()
    cursor.close()
    conn.close()

    return record_id

def get_agent_statistics(start_datetime=None, end_datetime=None):
    """
    Returns statistics per agent, including:
      - Number of audio files handled
      - Average AgentRating
      - Average SentiRating
      - Average Duration (seconds)
      - Number of anomalies
      - List of detected audio files with anomalies
    If start_datetime and end_datetime are provided, only includes records within that range based on CreatedAt.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        WITH AgentStats AS (
            SELECT 
                a.id AS agent_id,
                a.name AS agent_name,
                s.ID AS stat_id,
                s.AudioFileName,
                s.AgentRating,
                s.SentiRating,
                s.Anomaly,
                s.Duration,
                s.CreatedAt,
                r.value AS reason
            FROM Agents a
            LEFT JOIN audio_files af ON af.agent_id = a.id
            LEFT JOIN Statistic s ON s.AudioFileName = af.filename
            OUTER APPLY OPENJSON(s.AnomalyReason) r
            {created_filter}
        ),
        AudioFilesWithAnomaly AS (
            SELECT DISTINCT agent_id, AudioFileName
            FROM AgentStats
            WHERE Anomaly = 1
        )
        SELECT
            a.agent_id,
            a.agent_name,
            COUNT(DISTINCT stat_id) AS total_calls,
            AVG(AgentRating * 1.0) AS avg_agent_rating,
            AVG(SentiRating * 1.0) AS avg_sentiment_rating,
            AVG(Duration * 1.0) AS avg_duration_seconds,
            COUNT(reason) AS total_anomalies,
            STUFF((
                SELECT ', ' + af.AudioFileName
                FROM AudioFilesWithAnomaly af
                WHERE af.agent_id = a.agent_id
                FOR XML PATH(''), TYPE
            ).value('.', 'NVARCHAR(MAX)'), 1, 2, '') AS detected_audiofiles
        FROM AgentStats a
        GROUP BY a.agent_id, a.agent_name
        ORDER BY a.agent_name;
    """

    # Dynamic CreatedAt filter
    if start_datetime and end_datetime:
        created_filter = "WHERE s.CreatedAt BETWEEN ? AND ?"
        query = query.format(created_filter=created_filter)
        params = (start_datetime, end_datetime)
    else:
        query = query.format(created_filter="")
        params = ()

    cursor.execute(query, params)
    rows = cursor.fetchall()

    # Convert to list of dicts
    stats = []
    for row in rows:
        audio_files_list = row[7].split(", ") if row[7] else []

        stats.append({
            "agent_id": row[0],
            "agent_name": row[1],
            "total_calls": row[2],
            "avg_agent_rating": float(row[3]) if row[3] is not None else None,
            "avg_sentiment_rating": float(row[4]) if row[4] is not None else None,
            "avg_duration_seconds": float(row[5]) if row[5] is not None else None,
            "total_anomalies": row[6],
            "detected_audiofiles": audio_files_list
        })

    cursor.close()
    conn.close()
    return stats
