
import hashlib
import os
import re
import secrets
import string
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator


# --------------------------------------------------
# 1. LOAD ENVIRONMENT VARIABLES
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"

# Local development: load .env beside this file.
# Vercel: environment variables are supplied by Vercel.
if ENV_FILE.is_file():
    load_dotenv(ENV_FILE, override=True)


# --------------------------------------------------
# 2. APPLICATION CONFIGURATION
# --------------------------------------------------

app = FastAPI(title="CodeShare API", version="1.0.0")

DB_HOST = os.getenv("DB_HOST", "").strip()
DB_PORT = os.getenv("DB_PORT", "5432").strip()
DB_NAME = os.getenv("DB_NAME", "").strip()
DB_USER = os.getenv("DB_USER", "").strip()
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_SSLMODE = os.getenv("DB_SSLMODE", "require").strip() or "require"

MAX_CODE_CHARS = 100_000
MAX_TITLE_CHARS = 120

ALLOWED_LANGUAGES = {
    "python", "javascript", "typescript", "java",
    "c", "cpp", "csharp", "go", "rust", "ruby",
    "php", "sql", "html", "css", "json", "yaml",
    "bash", "powershell", "plaintext",
}


# --------------------------------------------------
# 3. DATABASE SCHEMA
# --------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS snippets (
    id VARCHAR(20) PRIMARY KEY,
    title VARCHAR(120) NOT NULL,
    language VARCHAR(30) NOT NULL DEFAULT 'plaintext',
    code TEXT NOT NULL,
    edit_token_hash CHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    views BIGINT NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_snippets_created_at
ON snippets (created_at DESC);
"""


# --------------------------------------------------
# 4. DATABASE CONFIGURATION AND CONNECTION
# --------------------------------------------------

def database_configured():
    """Check that the required database settings exist."""
    return all([
        DB_HOST,
        DB_PORT,
        DB_NAME,
        DB_USER,
        DB_PASSWORD,
        DB_SSLMODE,
    ])


def connect():
    """Connect to PostgreSQL using individual settings."""
    if not database_configured():
        raise HTTPException(
            status_code=503,
            detail=(
                "Database is not configured. Set DB_HOST, DB_PORT, "
                "DB_NAME, DB_USER, DB_PASSWORD, and DB_SSLMODE."
            ),
        )

    try:
        port = int(DB_PORT)

        if not 1 <= port <= 65535:
            raise ValueError("DB_PORT must be between 1 and 65535.")

        return psycopg.connect(
            host=DB_HOST,
            port=port,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            sslmode=DB_SSLMODE,
            connect_timeout=10,
            row_factory=dict_row,
        )

    except HTTPException:
        raise

    except (ValueError, TypeError):
        raise HTTPException(
            status_code=503,
            detail="Invalid database port configuration.",
        )

    except Exception:
        # Never expose database credentials to public clients.
        raise HTTPException(
            status_code=503,
            detail=(
                "Could not connect to PostgreSQL. Check the database "
                "host, credentials, SSL settings, and network access."
            ),
        )


def ensure_schema():
    """Create the snippets table and index if needed."""
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(SCHEMA)


def ensure_ready():
    """Verify the database is available and the schema exists."""
    try:
        ensure_schema()
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Database is unavailable or the schema could not be initialized.",
        )


@app.on_event("startup")
def startup():
    """Best-effort database initialization at startup."""
    if database_configured():
        try:
            ensure_schema()
        except Exception:
            # A database error is reported when a database route is used.
            pass


# --------------------------------------------------
# 5. HELPER FUNCTIONS
# --------------------------------------------------

def public_snippet(row):
    """Format a database record for the API response."""
    return {
        "id": row["id"],
        "title": row["title"],
        "language": row["language"],
        "code": row["code"],
        "created_at": (
            row["created_at"].isoformat()
            if row.get("created_at") else None
        ),
        "updated_at": (
            row["updated_at"].isoformat()
            if row.get("updated_at") else None
        ),
        "views": row.get("views", 0),
        "share_url": f"/s/{row['id']}",
    }


def hash_token(token: str) -> str:
    """Hash an edit token before storing it."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def make_id(length=12):
    """Generate a random, URL-friendly snippet ID."""
    alphabet = string.ascii_lowercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def extract_bearer_token(authorization):
    """Read the edit token from the Authorization header."""
    if not authorization:
        return ""

    scheme, separator, token = authorization.partition(" ")

    if not separator or scheme.lower() != "bearer":
        return ""

    return token.strip()


# --------------------------------------------------
# 6. REQUEST VALIDATION
# --------------------------------------------------

class SnippetCreate(BaseModel):
    title: str = Field(
        default="Untitled snippet",
        min_length=1,
        max_length=MAX_TITLE_CHARS,
    )
    language: str = Field(default="plaintext", max_length=30)
    code: str = Field(min_length=1, max_length=MAX_CODE_CHARS)

    @field_validator("title")
    @classmethod
    def clean_title(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Title cannot be empty.")
        return value

    @field_validator("language")
    @classmethod
    def clean_language(cls, value):
        value = value.strip().lower()
        if value not in ALLOWED_LANGUAGES:
            return "plaintext"
        return value


class SnippetUpdate(BaseModel):
    title: str = Field(
        min_length=1,
        max_length=MAX_TITLE_CHARS,
    )
    language: str = Field(default="plaintext", max_length=30)
    code: str = Field(min_length=1, max_length=MAX_CODE_CHARS)

    @field_validator("title")
    @classmethod
    def clean_title(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Title cannot be empty.")
        return value

    @field_validator("language")
    @classmethod
    def clean_language(cls, value):
        value = value.strip().lower()
        if value not in ALLOWED_LANGUAGES:
            return "plaintext"
        return value


# --------------------------------------------------
# 7. HEALTH CHECK
# --------------------------------------------------

@app.get("/api/health")
def health():
    """
    Check application status and whether database settings
    are configured. This endpoint does not expose credentials.
    """
    return {
        "status": "ok",
        "database_configured": database_configured(),
        "environment_file_exists": ENV_FILE.is_file(),
    }


@app.get("/api/health/db")
def database_health():
    """Check whether PostgreSQL is reachable."""
    ensure_ready()

    try:
        with connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT current_database(), current_user"
                )
                result = cur.fetchone()

        return {
            "status": "connected",
            "database": result["current_database"],
            "user": result["current_user"],
        }

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Database health check failed.",
        )


# --------------------------------------------------
# 8. CREATE A SNIPPET
# --------------------------------------------------

@app.post("/api/snippets")
def create_snippet(payload: SnippetCreate):
    ensure_ready()

    # Return the edit token only when creating the snippet.
    edit_token = secrets.token_urlsafe(32)

    for _ in range(5):
        snippet_id = make_id()

        try:
            with connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO snippets (
                            id,
                            title,
                            language,
                            code,
                            edit_token_hash
                        )
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING
                            id, title, language, code,
                            created_at, updated_at, views
                        """,
                        (
                            snippet_id,
                            payload.title,
                            payload.language,
                            payload.code,
                            hash_token(edit_token),
                        ),
                    )
                    row = cur.fetchone()

            result = public_snippet(row)
            result["edit_token"] = edit_token

            return JSONResponse(
                status_code=201,
                content=result,
            )

        except psycopg.errors.UniqueViolation:
            # A random ID collision: try another ID.
            continue

        except HTTPException:
            raise

        except Exception:
            raise HTTPException(
                status_code=503,
                detail="Could not save the snippet. Please try again.",
            )

    raise HTTPException(
        status_code=503,
        detail="Could not create a unique share ID. Please retry.",
    )


# --------------------------------------------------
# 9. VIEW A SNIPPET
# --------------------------------------------------

@app.get("/api/snippets/{snippet_id}")
def get_snippet(snippet_id: str):
    if not re.fullmatch(r"[a-z0-9]{12}", snippet_id):
        raise HTTPException(
            status_code=404,
            detail="Snippet not found.",
        )

    ensure_ready()

    try:
        with connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE snippets
                    SET views = views + 1
                    WHERE id = %s
                    RETURNING
                        id, title, language, code,
                        created_at, updated_at, views
                    """,
                    (snippet_id,),
                )
                row = cur.fetchone()

        if not row:
            raise HTTPException(
                status_code=404,
                detail="Snippet not found.",
            )

        return public_snippet(row)

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Could not load the snippet.",
        )


# --------------------------------------------------
# 10. UPDATE A SNIPPET
# --------------------------------------------------

@app.put("/api/snippets/{snippet_id}")
def update_snippet(
    snippet_id: str,
    payload: SnippetUpdate,
    authorization: str | None = Header(default=None),
):
    if not re.fullmatch(r"[a-z0-9]{12}", snippet_id):
        raise HTTPException(
            status_code=404,
            detail="Snippet not found.",
        )

    token = extract_bearer_token(authorization)

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Edit token required. Only the creator can edit this snippet.",
        )

    ensure_ready()

    try:
        with connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE snippets
                    SET title = %s,
                        language = %s,
                        code = %s,
                        updated_at = NOW()
                    WHERE id = %s
                      AND edit_token_hash = %s
                    RETURNING
                        id, title, language, code,
                        created_at, updated_at, views
                    """,
                    (
                        payload.title,
                        payload.language,
                        payload.code,
                        snippet_id,
                        hash_token(token),
                    ),
                )
                row = cur.fetchone()

        if not row:
            raise HTTPException(
                status_code=403,
                detail="Invalid edit token or snippet not found.",
            )

        return public_snippet(row)

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Could not update the snippet.",
        )


# --------------------------------------------------
# 11. DELETE A SNIPPET
# --------------------------------------------------

@app.delete("/api/snippets/{snippet_id}")
def delete_snippet(
    snippet_id: str,
    authorization: str | None = Header(default=None),
):
    if not re.fullmatch(r"[a-z0-9]{12}", snippet_id):
        raise HTTPException(
            status_code=404,
            detail="Snippet not found.",
        )

    token = extract_bearer_token(authorization)

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Edit token required.",
        )

    ensure_ready()

    try:
        with connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM snippets
                    WHERE id = %s
                      AND edit_token_hash = %s
                    RETURNING id
                    """,
                    (
                        snippet_id,
                        hash_token(token),
                    ),
                )
                row = cur.fetchone()

        if not row:
            raise HTTPException(
                status_code=403,
                detail="Invalid edit token or snippet not found.",
            )

        return {
            "deleted": True,
            "id": snippet_id,
        }

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Could not delete the snippet.",
        )
