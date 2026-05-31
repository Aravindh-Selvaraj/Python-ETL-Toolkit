# Python ETL Toolkit

A production-ready scaffold for building clean, reproducible, and resilient Python data pipelines. Designed with modular architecture, config-driven behaviour, `.env`-based secret management, Pydantic schema validation, and structured logging out of the box.

---

## Architecture

```
Python-ETL Toolkit/
├── config/
│   ├── base_config.json          # Pipeline settings (URL, path, column selection)
│   └── logging_config.json       # Rotating file + console log handlers
├── data/output/                  # Pipeline output (CSV files written here)
├── logs/                         # Rotating log files (auto-created at runtime)
├── requirements/
│   ├── prod.txt                  # Pinned production dependencies
│   └── dev.txt                   # Prod + linting + testing tools
├── src/
│   ├── schemas.py                # Pydantic input validation model
│   ├── extract.py                # HTTP fetch with auth headers + retry logic
│   ├── transform.py              # Config-driven cleaning and normalisation
│   ├── load.py                   # CSV persistence with directory auto-creation
│   └── __init__.py
├── tests/
│   └── test_pipeline.py          # Unit tests: all three ETL phases
├── .env                          # Your local secrets — NEVER commit this
├── .env.example                  # Safe template — commit this
├── .gitignore                    # Excludes .env, __pycache__, logs, outputs
├── run_pipeline.py               # Pipeline entrypoint / orchestrator
└── setup.ps1                     # Windows PowerShell bootstrap script
```

---

## Key Design Principles

| Principle | Implementation |
|---|---|
| **Modular** | Each ETL phase is an independent, swappable module |
| **Config-driven** | Column selection, URLs, paths all live in `base_config.json` |
| **Secrets-safe** | All API keys and tokens live in `.env` — never in config or code |
| **Schema-validated** | Pydantic `UserRecord` guards every incoming record |
| **Resilient** | Exponential-backoff retry on transient network failures |
| **Observable** | Structured rotating logs to console + file via `dictConfig` |
| **Tested** | Unit tests across Extract, Transform, and Load phases |

---

## Quickstart

### Step 1 — Bootstrap (Windows PowerShell)

```powershell
# Development (includes pytest, black, flake8)
./setup.ps1 --dev

# Production only
./setup.ps1
```

This will:
- Create and activate `.venv`
- Install all dependencies
- Auto-create `.env` from `.env.example` if it doesn't exist

### Step 2 — Fill in your credentials

Open `.env` and add your values:

```env
ETL_SOURCE_URL=https://api.example.com/data
ETL_API_KEY=your_api_key_here
ETL_BEARER_TOKEN=your_bearer_token_here
```

### Step 3 — Run the pipeline

```bash
python run_pipeline.py
```

### Step 4 — Run the tests

```bash
pytest tests/ -v
```

---

## Environment Variables Reference

All secrets and runtime overrides go in `.env`. Copy `.env.example` to get started.

| Variable | Required | Description |
|---|---|---|
| `ETL_SOURCE_URL` | ✅ | API endpoint to extract data from |
| `ETL_API_KEY` | Optional | Sent as `x-api-key` header |
| `ETL_BEARER_TOKEN` | Optional | Sent as `Authorization: Bearer <token>` |
| `ETL_API_TOKEN` | Optional | Sent as `Authorization: Token <token>` |
| `ETL_TARGET_PATH` | Optional | Overrides `target_path` in `base_config.json` |
| `ETL_ENV` | Optional | Environment label (`development`, `production`) |

> **Rule:** API keys and tokens always go in `.env`. Non-sensitive settings go in `base_config.json`.

---

## Configuration Reference

### `config/base_config.json`

```json
{
  "pipeline_name": "User_Data_Ingestion_Pipeline",
  "environment": "development",
  "source_url": "https://jsonplaceholder.typicode.com/users",
  "target_path": "data/output/processed_users.csv",
  "transformation_settings": {
    "target_columns": ["id", "name", "username", "email", "phone", "website"],
    "standardize_strings": true,
    "drop_duplicates": true
  }
}
```

| Key | Type | Description |
|---|---|---|
| `source_url` | string | Fallback URL if `ETL_SOURCE_URL` is not set in `.env` |
| `target_path` | string | Output CSV file path |
| `target_columns` | list | Columns to select from the source data |
| `standardize_strings` | bool | Title-case names, lowercase emails |
| `drop_duplicates` | bool | Remove duplicate rows |

---

## Swapping the Extract Source

Only `extract.py` needs to change when switching data sources. Everything else stays the same.

| Source | Auth method | Change needed |
|---|---|---|
| REST API | API Key / Bearer Token | `.env` values only |
| Google Sheets | Service Account JSON | `extract.py` + `.env` |
| PostgreSQL | DB URL + password | `extract.py` + `.env` |
| AWS S3 | Access Key + Secret | `extract.py` + `.env` |
| CSV / Excel file | None | `extract.py` only |

---

## Example Output

```
id,name,username,email,phone,website
1,Leanne Graham,Bret,sincere@april.biz,1-770-736-8031 x56442,hildegard.org
2,Ervin Howell,Antonette,shanna@melissa.tv,010-692-6593 x09125,anastasia.net
```

---

## Dependencies

| Package | Version | Purpose |
|---|---|---|
| `pandas` | 2.2.3 | DataFrame operations |
| `requests` | 2.32.3 | HTTP extraction |
| `pydantic` | 2.10.0 | Input schema validation |
| `python-dotenv` | 1.0.1 | `.env` file loading |
| `pytest` *(dev)* | 8.2.0 | Test runner |
| `black` *(dev)* | 24.4.2 | Code formatter |
| `flake8` *(dev)* | 7.0.0 | Linter |
