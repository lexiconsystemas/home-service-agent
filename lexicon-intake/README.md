# Lexicon Systemas Intake System (Home Services Edition)

A production-ready, repeatable intake MVP for home service businesses. This system accepts inbound call events, applies deterministic rule-based qualification and classification, and delivers structured lead payloads via multiple channels with automated follow-up.

## Architecture

- **Stateless Core**: All request handling is stateless with externalized state (DB/Redis)
- **Event-Driven Flow**: Inbound calls progress through Intake → Qualification → Classification → Delivery → Follow-up
- **Idempotency**: Duplicate call events do not duplicate lead delivery
- **Retry-Safe**: Webhook delivery includes automatic retry with backoff
- **Multi-Channel**: Support for Webhook, SMS, and Email delivery
- **Follow-Up Automation**: Configurable confirmation, reminder, and escalation messages

## Tech Stack

- Python 3.12
- FastAPI
- Pydantic v2
- SQLAlchemy 2.0 + Alembic
- Postgres (docker)
- Redis + RQ (worker queue)
- httpx (webhook delivery)
- Twilio (SMS)
- SendGrid (Email)
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

# Update .env with your API keys
# TWILIO_ACCOUNT_SID=your_twilio_account_sid
# TWILIO_AUTH_TOKEN=your_twilio_auth_token
# TWILIO_FROM_NUMBER=+15550000000
# SENDGRID_API_KEY=your_sendgrid_api_key
# EMAIL_FROM=noreply@yourcompany.com
# ADMIN_API_KEY=your_admin_api_key

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
    "urgency": "same_day",
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

## Phase 2 Configuration

### Multi-Channel Delivery Setup

Configure delivery channels per client using admin endpoints:

```bash
# Update delivery configuration
curl -X PUT http://localhost:8000/v1/admin/clients/demo/delivery \
  -H "Content-Type: application/json" \
  -H "X-Admin-API-Key: your_admin_api_key" \
  -d '{
    "delivery_channels": ["WEBHOOK", "SMS", "EMAIL"],
    "webhook_url": "https://yourcompany.com/webhook",
    "sms_to_numbers": ["+15550000001", "+15550000002"],
    "email_to_addresses": ["leads@yourcompany.com", "manager@yourcompany.com"]
  }'
```

### Follow-Up Automation Setup

```bash
# Update follow-up configuration
curl -X PUT http://localhost:8000/v1/admin/clients/demo/followup \
  -H "Content-Type: application/json" \
  -H "X-Admin-API-Key: your_admin_api_key" \
  -d '{
    "send_confirmation_to_caller": true,
    "send_reminder_to_caller": true,
    "reminder_delay_minutes": 30,
    "urgent_escalation": true
  }'
```

### Custom Message Templates

```bash
# Update message templates
curl -X PUT http://localhost:8000/v1/admin/clients/demo/templates \
  -H "Content-Type: application/json" \
  -H "X-Admin-API-Key: your_admin_api_key" \
  -d '{
    "sms_confirmation_template": "Thanks — we received your request for {service_requested}. We'\''ll follow up soon.",
    "sms_escalation_template": "URGENT lead: {service_requested} from {caller_phone} needs same-day service.",
    "email_subject_template": "New Lead: {service_requested} ({classification})",
    "email_body_template": "New lead received:\n\nService: {service_requested}\nPhone: {caller_phone}\nUrgency: {urgency}\nClassification: {classification}"
  }'
```

### Complete Client Configuration Example

```json
{
  "client_id": "demo",
  "delivery_channels": ["WEBHOOK", "SMS", "EMAIL"],
  "webhook_url": "https://yourcompany.com/webhook",
  "sms_to_numbers": ["+15550000001"],
  "email_to_addresses": ["leads@yourcompany.com"],
  "followup_flags": {
    "send_confirmation_to_caller": true,
    "send_reminder_to_caller": true,
    "reminder_delay_minutes": 30,
    "urgent_escalation": true
  },
  "message_templates": {
    "sms_confirmation_template": "Thanks — we received your request for {service_requested}. We'\''ll follow up soon.",
    "sms_reminder_template": "Quick check-in: we'\''re reviewing your request. Reply YES if you still need help today.",
    "sms_escalation_template": "URGENT lead: {service_requested} from {caller_phone} needs same-day service.",
    "email_subject_template": "New Lead: {service_requested} ({classification})",
    "email_body_template": "Lead Summary:\n\nLead ID: {lead_id}\nCaller: {caller_name}\nPhone: {caller_phone}\nService: {service_requested}\nUrgency: {urgency}\nClassification: {classification}\nTimestamp: {timestamp}"
  }
}
```

## Delivery Channels

### Webhook Delivery
- **Purpose**: Lead delivery to internal systems
- **Format**: JSON payload with HMAC signature
- **Retry**: Automatic with exponential backoff
- **Headers**: `X-Lexicon-Signature` for verification

### SMS Delivery
- **Purpose**: Lead summaries, confirmations, reminders, escalations
- **Provider**: Twilio
- **Limits**: 480 characters per message
- **Templates**: Customizable per client

### Email Delivery
- **Purpose**: Detailed lead summaries
- **Provider**: SendGrid
- **Format**: Plain text with structured data
- **Templates**: Customizable subject and body

## Follow-Up Automation

### Confirmation Messages
- **Trigger**: QUALIFIED or UNQUALIFIED classification
- **Recipient**: Original caller
- **Timing**: Immediate
- **Channel**: SMS
- **Template**: `sms_confirmation_template`

### Reminder Messages
- **Trigger**: QUALIFIED classification only
- **Recipient**: Original caller
- **Timing**: Delayed (configurable, default 30 minutes)
- **Channel**: SMS
- **Template**: `sms_reminder_template`

### Urgent Escalation
- **Trigger**: QUALIFIED + SAME_DAY urgency
- **Recipient**: Internal SMS numbers
- **Timing**: Immediate
- **Channel**: SMS
- **Template**: `sms_escalation_template`

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Postgres connection URL | `postgresql+asyncpg://lexicon:lexicon@localhost:5432/lexicon_intake` |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379/0` |
| `SECRET_KEY` | Application secret key | `change-in-production` |
| `WEBHOOK_SIGNING_SECRET` | Webhook signature secret | `change-in-production` |
| `ADMIN_API_KEY` | Admin API key | `change-in-production` |
| `TWILIO_ACCOUNT_SID` | Twilio account SID | `None` |
| `TWILIO_AUTH_TOKEN` | Twilio auth token | `None` |
| `TWILIO_FROM_NUMBER` | Twilio from number | `None` |
| `SENDGRID_API_KEY` | SendGrid API key | `None` |
| `EMAIL_FROM` | From email address | `None` |

### Client Configuration

The system uses client configurations stored in the `client_configs` table. Key fields:

- **delivery_channels**: Array of enabled channels (`["WEBHOOK", "SMS", "EMAIL"]`)
- **followup_flags**: Follow-up automation settings
- **message_templates**: Custom message templates
- **sms_to_numbers**: Internal SMS recipients
- **email_to_addresses**: Email recipients

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
  "urgency": "same_day",
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
pytest app/tests/test_delivery_fanout.py
pytest app/tests/test_followup_automation.py

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
- Delivery channel
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
- Admin API key protection for configuration endpoints
- Environment-based secrets
- Rate limiting protection

## Production Deployment

### Environment Setup

1. Set production environment variables
2. Configure Twilio and SendGrid API keys
3. Set secure admin API key
4. Configure proper logging and monitoring
5. Set up database backups
6. Configure webhook endpoint security

### Scaling

- API: Horizontal scaling behind load balancer
- Database: Read replicas for read-heavy workloads
- Redis: Cluster for high availability
- Workers: Scale based on delivery queue length

## Version History

### v0.2.0 (Phase 2)
- Multi-channel delivery (Webhook, SMS, Email)
- Follow-up automation (confirmation, reminder, escalation)
- Admin endpoints for configuration
- Custom message templates
- Enhanced delivery tracking

### v0.1.0 (Phase 1)
- Basic inbound call processing
- Rule-based qualification and classification
- Webhook delivery
- Idempotency and rate limiting
- Docker deployment

## License

MIT License - see LICENSE file for details.
