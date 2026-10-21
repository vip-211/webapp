
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv

# Load .env from the project folder
BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"

load_dotenv(ENV_FILE, override=True)

# Read individual database settings
DB_HOST = os.getenv("DB_HOST", "").strip()
DB_PORT = os.getenv("DB_PORT", "5432").strip()
DB_NAME = os.getenv("DB_NAME", "").strip()
DB_USER = os.getenv("DB_USER", "").strip()
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_SSLMODE = os.getenv("DB_SSLMODE", "require").strip()

print("Checking CodeShare PostgreSQL connection...")
print("Environment file exists:", ENV_FILE.exists())
print("Host configured:", bool(DB_HOST))
print("Port:", DB_PORT)
print("Database configured:", bool(DB_NAME))
print("Username configured:", bool(DB_USER))
print("Password configured:", bool(DB_PASSWORD))
print("SSL mode:", DB_SSLMODE)

if not all([DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD]):
    print("\nFAILED: One or more required database fields are missing.")
else:
    try:
        with psycopg.connect(
            host=DB_HOST,
            port=int(DB_PORT),
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            sslmode=DB_SSLMODE,
            connect_timeout=10,
        ) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT current_database(), current_user, NOW()"
                )
                result = cur.fetchone()

        print("\nSUCCESS: PostgreSQL connection works!")
        print("Database:", result[0])
        print("User:", result[1])
        print("Server time:", result[2])

    except Exception as exc:
        print("\nFAILED: PostgreSQL connection could not be established.")
        print("Error type:", type(exc).__name__)
        print("Error:", str(exc))
