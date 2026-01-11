import os
import socket
import time
import psycopg2
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "appdb")
DB_USER = os.getenv("DB_USER", "appuser")
DB_PASS = os.getenv("DB_PASS", "apppass")

app = FastAPI()

class UserPayload(BaseModel):
    name: str

def connect():
    return psycopg2.connect(
        host=DB_HOST,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
    )

def init_db_with_retry(retries=20, delay=2):
    last = None
    for _ in range(retries):
        try:
            with connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS settings (
                            key TEXT PRIMARY KEY,
                            value TEXT NOT NULL
                        );
                    """)
                    cur.execute("""
                        INSERT INTO settings(key, value)
                        VALUES ('name', 'Sem Vanderlinden')
                        ON CONFLICT (key) DO NOTHING;
                    """)
            return
        except Exception as e:
            last = e
            time.sleep(delay)
    raise last

@app.on_event("startup")
def startup():
    try:
        init_db_with_retry()
    except Exception as e:
        print("DB init failed:", e)

@app.get("/health")
def health():
    try:
        with connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

# HTML gebruikt /user en verwacht JSON met "name"
@app.get("/user")
def get_user():
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT value FROM settings WHERE key='name';")
            row = cur.fetchone()
    return {"name": row[0] if row else ""}

# Handig voor demo: naam aanpassen en dan refresh op web
@app.post("/user")
def set_user(payload: UserPayload):
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO settings(key, value)
                VALUES ('name', %s)
                ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value;
            """, (payload.name,))
    return {"updated": True, "name": payload.name}

# Container ID endpoint (hostname in containers)
@app.get("/id")
def get_id():
    return {"container_id": socket.gethostname()}

@app.get("/api/user")
def get_user_api():
    return get_user()

@app.post("/api/user")
def set_user_api(payload: UserPayload):
    return set_user(payload)

@app.get("/api/id")
def get_id_api():
    return get_id()

@app.get("/api/health")
def health_api():
    return health()

