# CodeShare — FastAPI + PostgreSQL + Vercel

CodeShare is a no-registration code snippet sharing app. A creator saves code and gets a unique link. Anyone with the link can view and copy it. The creator receives an edit key, stored in the creator's browser, to update or delete the snippet.

## Features

- HTML/CSS/JavaScript responsive interface
- FastAPI backend
- PostgreSQL persistence (Neon or Supabase)
- Unique 12-character share IDs
- Copy code and copy link actions
- Language selection and syntax highlighting
- Local library for snippets created in this browser
- Edit/delete protection with a one-time edit token
- Snippet size limit of 100,000 characters
- No code execution

## Files

- `index.py` — FastAPI app and API endpoints
- `public/index.html` — main dashboard/editor
- `public/view.html` — share page
- `public/styles.css` — responsive styling
- `public/app.js` — create/list/edit/delete/copy UI
- `public/view.js` — shared snippet view
- `database/schema.sql` — PostgreSQL schema
- `.env.example` — environment variable example
- `vercel.json` — shared URL rewrite

## 1. Create PostgreSQL database

### Neon (recommended)
1. Create a project at https://neon.tech.
2. Open the project and click **Connect**.
3. Select your branch, database, and role.
4. Copy the PostgreSQL connection string. Keep `sslmode=require`; use the pooled connection string for a serverless app if available.
5. Keep the connection string private.

Supabase also works: create a PostgreSQL project and copy its connection string from the database connection settings.

The app creates its table on first database-backed request. You can also run `database/schema.sql` in your provider's SQL editor.

## 2. Configure environment

For local development, copy `.env.example` to `.env` and set `DATABASE_URL` to your real connection string. The app does not automatically load `.env`; install `python-dotenv` and add `from dotenv import load_dotenv; load_dotenv()` at the top of `index.py` if you want to use `.env` locally, or export the variable in your terminal.

For Vercel:
1. Open your Vercel project.
2. Go to **Settings → Environment Variables**.
3. Add `DATABASE_URL` with the complete connection string.
4. Enable it for Production and Preview as appropriate.
5. Redeploy after adding or changing the variable.

Never commit `.env` or publish the database URL.

## 3. Deploy with GitHub + Vercel

1. Extract this project ZIP.
2. Create a new GitHub repository.
3. Upload the project files to the repository root (not inside an extra nested folder).
4. Open https://vercel.com/new and import that repository.
5. Keep the project root at the folder containing `index.py`, `requirements.txt`, `vercel.json`, and `public/`.
6. Vercel should detect FastAPI/Python automatically. Do not set a frontend-only framework preset or a custom output directory.
7. Add `DATABASE_URL` in Environment Variables.
8. Deploy.
9. Test `https://YOUR-APP.vercel.app/api/health` and then create a test snippet.

Current Vercel FastAPI docs: https://vercel.com/docs/frameworks/backend/fastapi

## 4. Local development

Use Python 3.12.

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

Set `DATABASE_URL` in your shell before running locally. To use a local `.env`, install `python-dotenv` and add `from dotenv import load_dotenv; load_dotenv()` near the top of `index.py`.

```bash
# Windows PowerShell
$env:DATABASE_URL="postgresql://USER:PASSWORD@HOST:5432/DATABASE?sslmode=require"
uvicorn index:app --reload
```

Open http://127.0.0.1:8000 for API docs and endpoints. The frontend files are served as static files by Vercel in production; for a full local frontend preview, use a static server from the `public` directory (for example, `python -m http.server 5500 --directory public`) and proxy `/api` to the FastAPI server, or use the Vercel CLI to mirror production routing.

## 5. How sharing works

- `POST /api/snippets` creates a snippet and returns its share ID and edit token.
- `GET /api/snippets/{id}` returns public code and increments views.
- `PUT /api/snippets/{id}` updates a snippet when the `Authorization: Bearer <edit_token>` header is valid.
- `DELETE /api/snippets/{id}` deletes a snippet when the edit token is valid.
- `/s/{id}` serves the share page.

The creator's edit token is only returned when a snippet is created. The frontend stores it in local storage. If browser storage is cleared or the user switches devices, the app cannot recover that token. Keep a private backup if you need edit access later.

## Security notes

- The app stores code as text and never executes it.
- The edit token is stored as a SHA-256 hash in PostgreSQL; the raw token is returned once to the creator.
- The share URL is unlisted rather than truly private: anyone who obtains it can read the snippet.
- Avoid sharing passwords, API keys, private certificates, customer data, or other secrets in snippets.
- For a public production service, consider adding rate limiting, abuse reporting, retention controls, and CAPTCHA to prevent spam.
- Public view counts can be inflated by repeated requests; they are informational, not audited analytics.

## Troubleshooting

- **503 Database is not configured:** set `DATABASE_URL` in Vercel Environment Variables and redeploy.
- **Could not connect to PostgreSQL:** verify the URL, password, SSL parameter, network/database status, and whether your provider's pooled connection string is suitable.
- **Static page loads but API fails:** inspect the Vercel Function logs and verify the project root contains `index.py` and `requirements.txt`.
- **Share link returns 404:** verify the deployed `vercel.json` rewrite exists and that the ID is 12 lowercase letters/digits.
