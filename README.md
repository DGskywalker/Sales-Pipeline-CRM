<div align="center">

# Sales Pipeline CRM

**Contact management, deal pipeline tracking and sales reporting in one lightweight platform.**

FastAPI &nbsp;·&nbsp; SQLAlchemy 2 &nbsp;·&nbsp; Pydantic v2 &nbsp;·&nbsp; Vanilla JavaScript &nbsp;·&nbsp; Docker &nbsp;·&nbsp; GitHub Actions

![Python](https://img.shields.io/badge/python-3.10%2B-3b5bdb?style=flat-square)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-3b5bdb?style=flat-square)
![Tests](https://img.shields.io/badge/tests-19%20passing-16a34a?style=flat-square)
![Coverage](https://img.shields.io/badge/coverage-95%25-16a34a?style=flat-square)

<br>

<img src="docs/dashboard.png" alt="Sales Pipeline CRM dashboard showing KPI cards, pipeline by stage, new pipeline by month, team leaderboard and recent activity" width="100%">

</div>

---

## Overview

Sales Pipeline CRM is an internal platform for business development and sales outreach teams. It tracks every lead from first contact to closed deal, records each touchpoint along the way, and turns that history into a live forecast.

The backend is a typed REST API built on FastAPI and SQLAlchemy. It runs on SQLite out of the box and on PostgreSQL in production. The frontend is a single-page web app written in plain JavaScript, so there is no build step and no frontend dependencies.

<br>

## Features

<table>
<tr>
<td width="50%" valign="top">

### Contacts
- Create, edit, search and delete contacts
- Search across name, email and company
- Paginated listing with total counts
- Duplicate-email protection
- Bulk CSV lead import that skips duplicates and reports invalid rows

</td>
<td width="50%" valign="top">

### Pipeline
- Stages: `Lead` → `Contacted` → `Qualified` → `Proposal` → `Won` / `Lost`
- Drag-and-drop Kanban board
- Filter by owner, search by deal, contact or company
- Automatic audit trail for every stage change
- Log calls, emails, meetings and notes per deal

</td>
</tr>
<tr>
<td width="50%" valign="top">

### Reporting
- Open pipeline value and probability-weighted forecast
- Win rate, won value and average deal size
- Deal count and value per stage
- Team leaderboard ranked by won value
- Recent activity feed and CSV export of all deals

</td>
<td width="50%" valign="top">

### Engineering
- Pydantic validation on every request
- 19 pytest tests with 95% coverage
- Non-root Docker image with a health check
- CI pipeline for linting, tests and the Docker build
- Seed script for realistic demo data

</td>
</tr>
</table>

<br>

## The web app

| View | What it does |
| :--- | :--- |
| **Dashboard** | KPI cards, pipeline-by-stage chart, monthly new-pipeline chart, team leaderboard and recent activity |
| **Pipeline** | Kanban board with one column per stage; drag a card to move the deal |
| **Contacts** | Searchable, paginated table with add, edit, delete and CSV import |
| **Activity** | Full activity history, filterable by type |
| **Detail panels** | Edit a deal or contact, jump between stages, log activity and read the timeline |

The interface supports light and dark themes and adapts down to phone width.

<br>

## Quick start

Requires **Python 3.10 or newer**.

```bash
# 1. Create a virtual environment and install dependencies
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Load demo data (optional)
python -m app.seed --reset

# 3. Start the server
uvicorn app.main:app --reload
```

| URL | Description |
| :--- | :--- |
| `http://localhost:8000` | Web app |
| `http://localhost:8000/docs` | Interactive API documentation |
| `http://localhost:8000/health` | Health check |

### Docker

```bash
docker build -t sales-pipeline-crm .
docker run -p 8000:8000 sales-pipeline-crm
```

<br>

## Configuration

| Variable | Default | Description |
| :--- | :--- | :--- |
| `DATABASE_URL` | `sqlite:///./crm.db` | Any SQLAlchemy URL, for example `postgresql+psycopg://user:pass@host/db` |
| `CORS_ORIGINS` | *(empty)* | Comma-separated list of allowed origins |
| `PORT` | `8000` | Port used by the Docker image |

<br>

## API reference

All endpoints are served under `/api`. Full schemas are available at `/docs`.

<details open>
<summary><b>Contacts</b></summary>

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/contacts` | Create a contact |
| `GET` | `/contacts?q=&limit=&offset=` | List and search contacts; total in the `X-Total-Count` header |
| `GET` | `/contacts/{id}` | Get a contact |
| `GET` | `/contacts/{id}/deals` | List a contact's deals |
| `PATCH` | `/contacts/{id}` | Update a contact |
| `DELETE` | `/contacts/{id}` | Delete a contact and their deals |
| `POST` | `/contacts/import` | Bulk import from raw CSV |

</details>

<details open>
<summary><b>Deals</b></summary>

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/deals` | Create a deal |
| `GET` | `/deals?stage=&owner=&q=` | List, filter and search deals |
| `GET` | `/deals/{id}` | Get a deal with contact details |
| `PATCH` | `/deals/{id}` | Update a deal; stage changes are logged automatically |
| `DELETE` | `/deals/{id}` | Delete a deal |
| `POST` | `/deals/{id}/activities` | Log a call, email, meeting or note |
| `GET` | `/deals/{id}/activities` | Get a deal's activity timeline |

</details>

<details open>
<summary><b>Reports</b></summary>

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/reports/summary` | Pipeline totals, weighted forecast and win rate |
| `GET` | `/reports/owners` | Per-owner leaderboard |
| `GET` | `/reports/activity?limit=` | Most recent activity across all deals |
| `GET` | `/reports/deals.csv` | CSV export of all deals |

</details>

### Forecast weights

The weighted forecast multiplies each open deal's value by the probability for its stage.

| Lead | Contacted | Qualified | Proposal | Won | Lost |
| :---: | :---: | :---: | :---: | :---: | :---: |
| 10% | 20% | 40% | 60% | 100% | 0% |

### Bulk import

```bash
curl -X POST localhost:8000/api/contacts/import \
  -H "Content-Type: text/csv" \
  --data-binary @leads.csv
```

The CSV header must include `name` and `email`. `company`, `phone` and `source` are optional.

```json
{ "created": 42, "skipped_duplicates": 3, "errors": [{ "row": 7, "reason": "missing name or invalid email" }] }
```

<br>

## Testing

```bash
pip install -r requirements-dev.txt
pytest --cov=app
```

CI runs `ruff`, the full test suite with an 85% coverage gate, and the Docker build on every push and pull request.

<br>

## Project structure

```
.
├── app/
│   ├── main.py            Application setup, routers and static files
│   ├── db.py              Engine, session and declarative base
│   ├── models.py          Contact, Deal and Activity models
│   ├── schemas.py         Request and response schemas
│   ├── seed.py            Demo data generator
│   └── routes/
│       ├── contacts.py    Contact CRUD, search and CSV import
│       ├── deals.py       Deal CRUD, filtering and activities
│       └── reports.py     Summary, leaderboard, feed and export
├── static/
│   ├── index.html         App shell
│   ├── app.js             Single-page frontend
│   └── app.css            Styles and light/dark themes
├── tests/                 Pytest suite
├── Dockerfile
└── .github/workflows/     CI pipeline
```

<br>

---

<div align="center">
<sub>Built with FastAPI and SQLAlchemy.</sub>
</div>
