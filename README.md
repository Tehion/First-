# Mini CRM

A mini CRM system built with Python/FastAPI for lead management, pipeline tracking, reminders, and email campaigns.

## Features

- **Lead Management** — Create, list, filter, update, and delete leads
- **Lookalike Search** — Find similar leads based on industry, location, company size, and tags
- **Pipeline Tracking** — Move leads through stages (new_lead → contacted → proposal → negotiation → won/lost) with automatic activity logging
- **Activity Log** — Record calls, emails, meetings, and notes per lead
- **Reminders** — Set due-date reminders on leads, view upcoming/overdue, background notification check
- **Email Campaigns** — Create campaigns with recipient filters, preview recipients, send bulk emails via SMTP

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://localhost:8000/docs for interactive API documentation (Swagger UI).

## Configuration

Copy `.env.example` to `.env` and fill in SMTP settings for email campaigns:

```bash
cp .env.example .env
```

## API Endpoints

### Leads
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/leads` | Create a lead |
| GET | `/leads` | List/filter leads (query: industry, location, stage, min_size, max_size, tag, q) |
| GET | `/leads/{id}` | Get lead with activities |
| PUT | `/leads/{id}` | Update lead |
| DELETE | `/leads/{id}` | Delete lead |
| POST | `/leads/lookalike` | Similarity search |

### Pipeline
| Method | Endpoint | Description |
|--------|----------|-------------|
| PUT | `/leads/{id}/stage` | Change pipeline stage |
| GET | `/pipeline/summary` | Leads count per stage |

### Activities
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/leads/{id}/activities` | Log an activity |
| GET | `/leads/{id}/activities` | List activities |

### Reminders
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/reminders` | Create reminder |
| GET | `/reminders` | List (filters: upcoming, overdue, lead_id) |
| PUT | `/reminders/{id}` | Update / mark done |
| DELETE | `/reminders/{id}` | Delete |

### Email Campaigns
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/emails/campaigns` | Create campaign |
| GET | `/emails/campaigns` | List campaigns |
| GET | `/emails/campaigns/{id}` | Campaign detail |
| POST | `/emails/campaigns/{id}/send` | Send campaign |
| POST | `/emails/campaigns/{id}/preview` | Preview recipients |

## Example Usage

```bash
# Create a lead
curl -X POST http://localhost:8000/leads \
  -H 'Content-Type: application/json' \
  -d '{"name":"Acme Corp","industry":"ecommerce","location":"PL","company_size":120,"tags":["b2b","saas"],"email":"contact@acme.com"}'

# Search for similar leads
curl -X POST http://localhost:8000/leads/lookalike \
  -H 'Content-Type: application/json' \
  -d '{"seed":{"industry":"ecommerce","location":"PL","company_size":100,"tags":["saas"]},"limit":5}'

# Move lead through pipeline
curl -X PUT http://localhost:8000/leads/1/stage \
  -H 'Content-Type: application/json' \
  -d '{"stage":"contacted"}'

# Set a reminder
curl -X POST http://localhost:8000/reminders \
  -H 'Content-Type: application/json' \
  -d '{"lead_id":1,"title":"Follow up call","due_at":"2026-03-20T10:00:00Z"}'
```

## Tech Stack

- **FastAPI** + **Uvicorn** — Web framework and ASGI server
- **SQLAlchemy** + **SQLite** — ORM and database
- **APScheduler** — Background reminder checks
- **smtplib** — Email sending (stdlib)
