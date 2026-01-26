# Lexicon Systemas Intake System (Home Services Edition)

A production-ready, repeatable intake MVP for home service businesses. This system accepts inbound call events, applies deterministic rule-based qualification and classification, and delivers structured lead payloads via webhooks.

## Architecture

- **Stateless Core**: All request handling is stateless with externalized state (DB/Redis)
- **Event-Driven Flow**: Inbound calls progress through Intake → Qualification → Classification → Delivery
- **Idempotency**: Duplicate call events do not duplicate lead delivery
- **Retry-Safe**: Webhook delivery includes automatic retry with backoff

## Tech Stack

- Python 3.12
- FastAPI
- Pydantic v2
- SQLAlchemy 2.0 + Alembic
- Postgres (docker)
- Redis + RQ (worker queue)
- httpx (webhook delivery)
- pytest (tests)

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.12 (for local development)

### Running with Docker Compose

```bash
# Clone and navigate to project
cd lexicon-intake

# Copy environment file
cp .env.example .env

# Start all services
docker compose up --build

# Initialize database (in separate terminal)
docker compose exec api bash scripts/init_db.sh
```

Services will be available at:
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Database: localhost:5432
- Redis: localhost:6379

### Local Development

```bash
# Install dependencies
pip install -e .

# Start database and Redis
docker compose up db redis -d

# Run database migrations
alembic upgrade head

# Seed demo client
python scripts/init_db.sh

# Start API server
uvicorn app.main:app --reload

# Start worker (in separate terminal)
python -m app.workers.queue
```

## API Endpoints

### Health Checks

```bash
# Basic health check
curl http://localhost:8000/healthz

# Readiness check (includes database)
curl http://localhost:8000/healthz/ready
```

### Inbound Call Processing

```bash
curl -X POST http://localhost:8000/v1/calls/inbound \
  -H "Content-Type: application/json" \
  -d '{
    "call_id": "call-12345",
    "from_number": "+15551234567",
    "to_number": "+15550001111",
    "timestamp": "2024-01-01T12:00:00Z",
    "caller_name": "John Doe",
    "service_requested": "plumbing",
    "urgency": "medium",
    "budget": 200,
    "location_zip": "90210"
  }'
```

**Response:**
```json
{
  "lead_id": "lead-67890",
  "classification": "QUALIFIED",
  "message": "Call processed successfully. Classification: QUALIFIED"
}
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Postgres connection URL | `postgresql+asyncpg://lexicon:lexicon@localhost:5432/lexicon_intake` |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379/0` |
| `SECRET_KEY` | Application secret key | `change-in-production` |
| `WEBHOOK_SIGNING_SECRET` | Webhook signature secret | `change-in-production` |
| `RATE_LIMIT_REQUESTS` | Rate limit requests per window | `100` |
| `RATE_LIMIT_WINDOW` | Rate limit window in seconds | `60` |
| `LOG_LEVEL` | Logging level | `INFO` |

### Client Configuration

The system uses client configurations stored in the `client_configs` table. A demo client is automatically seeded:

```json
{
  "client_id": "demo",
  "to_number": "+15550001111",
  "greeting": "Thanks for calling.",
  "rules_json": {
    "service_types_allowed": ["plumbing", "electrical", "hvac"],
    "service_area_zip_prefixes": ["90210", "90211", "90212"],
    "min_budget": 100,
    "urgency_allowed": ["low", "medium", "high"]
  },
  "webhook_url": "http://requestbin.local/",
  "followup_enabled": false
}
```

## Classification Logic

Calls are classified as:

- **QUALIFIED**: Passes all qualification rules
- **UNQUALIFIED**: Fails qualification rules
- **SPAM**: Detected spam patterns (fake phone, suspicious names)
- **DROPPED**: Invalid data (missing fields, invalid phone)

## Webhook Delivery

Qualified leads are delivered via webhook with the following payload:

```json
{
  "lead_id": "lead-67890",
  "call_id": "call-12345",
  "caller_name": "John Doe",
  "caller_phone": "+15551234567",
  "service_requested": "plumbing",
  "qualification_outcome": "qualified",
  "urgency": "medium",
  "timestamp": "2024-01-01T12:00:00+00:00",
  "classification": "QUALIFIED",
  "reason_codes": []
}
```

**Headers:**
- `Content-Type: application/json`
- `X-Lexicon-Signature`: HMAC SHA256 signature of payload body
- `User-Agent: Lexicon-Intake/1.0`

## Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest app/tests/test_rules.py

# Run with coverage
pytest --cov=app
```

## Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

## Monitoring

### Health Endpoints

- `/healthz` - Basic health check
- `/healthz/ready` - Readiness check with database connectivity

### Logging

Structured JSON logging includes:
- Request ID
- Call ID
- Lead ID
- Classification results
- Error details

## Rate Limiting

Redis-based rate limiting using sliding window algorithm:
- Default: 100 requests per 60 seconds per IP
- Configurable via environment variables

## Idempotency

Call events are deduplicated using the `call_id` field:
- Duplicate calls return 409 Conflict
- No duplicate lead records or webhook deliveries

## Security

- Input sanitization on all external inputs
- HMAC signature verification for webhooks
- Environment-based secrets
- Rate limiting protection

## Production Deployment

### Environment Setup

1. Set production environment variables
2. Use secure secrets management
3. Configure proper logging and monitoring
4. Set up database backups
5. Configure webhook endpoint security

### Scaling

- API: Horizontal scaling behind load balancer
- Database: Read replicas for read-heavy workloads
- Redis: Cluster for high availability
- Workers: Scale based on delivery queue length

## License

MIT License - see LICENSE file for details.
