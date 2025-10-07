from dbs.db_connections import get_db_connection
import os


def get_audio_files() -> dict:
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT filename, file_path FROM audio_files")
    files = cursor.fetchall()

    cursor.close()
    conn.close()

    return {
        filename: os.path.normpath(path.replace("\\", "/"))
        for filename, path in files
    }

def insert_audio_metadata(filename: str, file_path: str):
    """Insert audio file metadata into SQL Server"""
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "INSERT INTO audio_files (filename, file_path) VALUES (?, ?)"
    cursor.execute(query, (filename, file_path))
    conn.commit()

    cursor.close()
    conn.close()