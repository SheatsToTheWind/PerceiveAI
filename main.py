import os
import psycopg2
import logging
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from psycopg2.pool import SimpleConnectionPool
from psycopg2.extensions import connection
from typing import Generator
from fastapi_jwt_auth import AuthJWT
from datetime import timedelta
import bcrypt

# ✅ Initialize FastAPI
app = FastAPI()

# ✅ Configure Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# ✅ Database Settings (Replace with your online DB)
DB_URL = "postgresql://your_user:your_password@your_host:your_port/your_database"

# ✅ PostgreSQL Connection Pool
try:
    DB_POOL = SimpleConnectionPool(1, 20, dsn=DB_URL)
    logging.info("✅ Connected to Remote PostgreSQL.")
except Exception as e:
    logging.error(f"❌ Database Connection Failed: {str(e)}")
    raise RuntimeError("Database Initialization Failed!")

# ✅ Dependency to Get DB Connection
def get_db() -> Generator[connection, None, None]:
    conn = DB_POOL.getconn()
    try:
        yield conn
    finally:
        DB_POOL.putconn(conn)

# ✅ JWT Authentication Settings
class Settings(BaseModel):
    authjwt_secret_key: str = os.getenv("JWT_SECRET", "your_secure_secret")
    authjwt_access_token_expires: timedelta = timedelta(hours=1)
    authjwt_refresh_token_expires: timedelta = timedelta(days=1)

@AuthJWT.load_config
def get_config():
    return Settings()

# ✅ User Authentication (Replace with database user check)
ADMIN_USER = "admin"
ADMIN_HASHED_PASSWORD = bcrypt.hashpw("password123".encode(), bcrypt.gensalt()).decode()

@app.post("/login")
def login(username: str, password: str, Authorize: AuthJWT = Depends()):
    if username == ADMIN_USER and bcrypt.checkpw(password.encode(), ADMIN_HASHED_PASSWORD.encode()):
        access_token = Authorize.create_access_token(subject=username)
        refresh_token = Authorize.create_refresh_token(subject=username)
        return {"access_token": access_token, "refresh_token": refresh_token}
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.post("/refresh-token")
def refresh_token(Authorize: AuthJWT = Depends()):
    Authorize.jwt_refresh_token_required()
    current_user = Authorize.get_jwt_subject()
    new_access_token = Authorize.create_access_token(subject=current_user)
    return {"access_token": new_access_token}

@app.get("/secure-data")
def secure_data(Authorize: AuthJWT = Depends()):
    Authorize.jwt_required()
    return {"message": "🔐 Secure AI Data Accessed!"}

# ✅ AI Memory Recall (JWT Protected)
@app.get("/recall/{input_text}")
def recall_memory(input_text: str, Authorize: AuthJWT = Depends(), conn: connection = Depends(get_db)):
    Authorize.jwt_required()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT response FROM memory WHERE input = %s ORDER BY weight DESC LIMIT 1;", (input_text,))
            memory = cursor.fetchone()
        if memory:
            return {"response": memory[0]}
        else:
            return {"response": "I don't remember that."}
    except Exception as e:
        logging.error(f"❌ Recall error: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error.")

# ✅ Root Endpoint
@app.get("/")
def root():
    return {"message": "🚀 Perceive AI is Running with JWT Authentication!"}