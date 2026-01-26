# Lexicon Systemas Intake System (Home Services Edition)

A production-ready, repeatable intake MVP for home service businesses. This system accepts inbound call events, applies deterministic rule-based qualification and classification, and delivers structured lead payloads via multiple channels with automated follow-up and scheduling capabilities.

## Architecture

- **Stateless Core**: All request handling is stateless with externalized state (DB/Redis)
- **Event-Driven Flow**: Inbound calls progress through Intake → Qualification → Classification → Delivery → Follow-up → Scheduling
- **Idempotency**: Duplicate call events do not duplicate lead delivery
- **Retry-Safe**: Webhook delivery includes automatic retry with backoff and dead letter queue
- **Multi-Channel**: Support for Webhook, SMS, and Email delivery
- **Follow-Up Automation**: Configurable confirmation, reminder, and escalation messages
- **Routing Profiles**: Configuration-only routing by service type and business hours
- **Service Type Normalization**: Deterministic keyword-based service type detection
- **Scheduling-Lite**: Time window selection via SMS for qualified leads
- **Client Provisioning**: One-command client setup with templates
- **Config Versioning**: Full audit trail and rollback capabilities
- **Multi-Tenant Safety**: Per-client API keys and access controls

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
- ruff (linting)
- Prometheus (metrics)

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

# Initialize database with seed data
docker compose exec api bash scripts/init_db.sh
```

## Phase 3 Features

### 🚀 **What This Is / Is Not**

**This IS:**
- A repeatable intake product for home service businesses
- Configuration-only routing and scheduling system
- Multi-tenant platform with audit trails
- Production-ready operations tooling

**This IS NOT:**
- A CRM system
- A calendar or full scheduling system
- A UI/UX product
- Custom integration platform

### 🏢 **Client Onboarding**

#### One-Command Client Provisioning

```bash
# Provision a new HVAC client
python scripts/provision_client.py \
  --client-id "hvac-pro-company" \
  --to-number "+15550000001" \
  --template "hvac"
```

**Available Templates:**
- `hvac` - HVAC repair and installation
- `plumbing` - Plumbing services  
- `pressure_wash` - Pressure washing
- `restoration` - Water/fire damage restoration

Each template includes:
- Pre-configured qualification rules
- Service-specific routing profiles
- Business hours and timezone settings
- Default delivery channels
- Scheduling window configurations

#### Client API Keys

Each client gets a unique API key for webhook verification:
```
lexicon_client_{client_id}_{random_token}
```

### 📅 **Scheduling-Lite Explained**

**Not a calendar system** - Simple time window selection for qualified leads.

#### How It Works

1. **Qualified Lead Detection**: System identifies qualified leads based on rules
2. **Window Generation**: Creates time windows based on routing configuration
3. **SMS Selection**: Sends SMS with numbered options:
   ```
   We can help. Reply with your preferred time:
   1. Today 2-4pm
   2. Today 4-6pm  
   3. Tomorrow Morning
   ```
4. **Response Processing**: Caller replies with number (1, 2, 3)
5. **Confirmation**: System confirms selection and updates lead

#### Scheduling Configuration

```json
{
  "scheduling": {
    "enabled": true,
    "windows": [
      {"label": "Today 2–4pm", "start_offset_min": 0, "end_offset_min": 120},
      {"label": "Today 4–6pm", "start_offset_min": 120, "end_offset_min": 240},
      {"label": "Tomorrow Morning", "start_offset_min": 1440, "end_offset_min": 1800}
    ]
  }
}
```

### 🔄 **Routing + Business Hours Recap**

#### Service Type Normalization

Automatic keyword-based detection:
- **HVAC Repair**: "ac", "air conditioner", "hvac", "furnace", "heat"
- **Plumbing**: "pipe", "leak", "drain", "toilet", "water heater"
- **Pressure Wash**: "pressure wash", "power wash", "driveway"
- **Restoration**: "mold", "water damage", "fire damage"

#### Routing Profiles

Configuration-driven routing based on:
1. **Service Type**: Normalized service category
2. **Time Window**: IN_HOURS vs AFTER_HOURS (based on business hours)
3. **Urgency**: SAME_DAY urgency can override after-hours routing

#### Example Routing Profile

```json
{
  "name": "hvac_urgent_after_hours",
  "match": {
    "service_type_in": ["hvac_repair", "hvac_install"],
    "time_window": "AFTER_HOURS"
  },
  "delivery": {
    "channels": ["SMS"],
    "sms_to_numbers": ["+15550009999"]
  },
  "escalation": {
    "urgent_escalation": true,
    "urgent_override_recipients": ["+15550009999"]
  },
  "scheduling": {
    "enabled": true,
    "windows": [
      {"label": "Tomorrow Morning", "start_offset_min": 1440, "end_offset_min": 1800}
    ]
  }
}
```

### 🛠️ **Ops Playbook**

#### Dead Letter Queue (DLQ) Monitoring

```bash
# Get failed deliveries
curl -H "X-Admin-API-Key: your_key" \
  http://localhost:8000/v1/dlq

# Response includes:
- delivery_id
- failure_reason  
- attempt_count
- last_attempt_at
```

#### Delivery Replay

```bash
# Replay a failed delivery
curl -X POST \
  -H "X-Admin-API-Key: your_key" \
  http://localhost:8000/v1/delivery/{delivery_id}/replay
```

**Rules:**
- Only FAILED_FINAL deliveries can be replayed
- Creates new delivery attempt (doesn't modify original)
- Enforces idempotency per delivery_id + replay_count
- Logs audit event REPLAY_DELIVERY

#### Configuration Rollback

```bash
# View config history
curl -H "X-Admin-API-Key: your_key" \
  http://localhost:8000/v1/admin/clients/{client_id}/config-history

# Rollback to specific version
curl -X POST \
  -H "X-Admin-API-Key: your_key" \
  http://localhost:8000/v1/admin/clients/{client_id}/rollback/{version}
```

#### Audit Logs

```bash
# Get audit logs
curl -H "X-Admin-API-Key: your_key" \
  "http://localhost:8000/v1/audit-logs?target_type=client_config&limit=100"
```

**Audit Events:**
- CONFIG_UPDATE - Any configuration change
- REPLAY_DELIVERY - Delivery replay operations
- CREATE_CLIENT - New client provisioning
- SCHEDULING_RESPONSE - SMS scheduling responses

### 📊 **Production Monitoring**

#### Metrics Endpoint

```bash
# Prometheus metrics
curl http://localhost:8000/metrics
```

**Key Metrics:**
- `lexicon_inbound_calls_total` - Inbound call volume
- `lexicon_leads_qualified_total` - Qualified leads by service type
- `lexicon_deliveries_sent_total` - Successful deliveries
- `lexicon_deliveries_failed_total` - Failed deliveries
- `lexicon_dlq_size` - Dead letter queue size
- `lexicon_queue_depth` - Worker queue depth
- `lexicon_scheduling_responses_total` - Scheduling SMS responses
- `lexicon_config_updates_total` - Configuration changes
- `lexicon_delivery_replays_total` - Delivery replays

#### Health Checks

```bash
# Application health
curl http://localhost:8000/healthz

# Database health
curl http://localhost:8000/healthz/db

# Redis health  
curl http://localhost:8000/healthz/redis
```

#### Structured Logging

All logs include:
- `ts` - Timestamp
- `level` - Log level
- `request_id` - Request correlation ID
- `call_id` - Call identifier
- `lead_id` - Lead identifier
- `client_id` - Client identifier
- `event` - Event type
- `details` - Event details

### 🔒 **Security & Multi-Tenant Safety**

#### API Key Management

- **Admin API Key**: Full system access (configuration, ops)
- **Client API Keys**: Per-client access (read-only config, delivery status)

#### Client Access Boundaries

```bash
# Client can access their own data
curl -H "X-Client-API-Key: client_key" \
  http://localhost:8000/v1/clients/me

# Admin can access any client
curl -H "X-Admin-API-Key: admin_key" \
  http://localhost:8000/v1/admin/clients/{client_id}
```

#### Webhook Security

- HMAC signature verification for outbound webhooks
- Rate limiting on inbound endpoints
- Input sanitization on all external inputs
- CORS disabled by default

### 📋 **Production Checklist**

#### Security
- [ ] Set strong `ADMIN_API_KEY` in environment
- [ ] Enable webhook signature verification
- [ ] Configure rate limiting for inbound calls
- [ ] Set CORS to specific origins only (if needed)
- [ ] Validate all phone numbers (E.164) and emails

#### Monitoring
- [ ] Monitor `/healthz` and `/readyz` endpoints
- [ ] Set up log aggregation for JSON structured logs
- [ ] Monitor `/metrics` endpoint (Prometheus format)
- [ ] Set up alerts for delivery failures
- [ ] Monitor Redis queue sizes and DLQ

#### Reliability
- [ ] Configure database backups
- [ ] Set up Redis persistence
- [ ] Monitor worker queue processing
- [ ] Set up retry policies for external services
- [ ] Configure dead-letter handling

#### Operations
- [ ] Test client provisioning script
- [ ] Verify rollback functionality
- [ ] Test delivery replay workflow
- [ ] Monitor audit log volume
- [ ] Set up scheduling response monitoring

### 📚 **API Endpoints**

#### Core API
- `POST /v1/calls/inbound` - Process inbound call events
- `GET /healthz` - Health check endpoints
- `GET /metrics` - Prometheus metrics

#### Admin API (Protected)
```bash
# Configuration management
PUT /v1/admin/clients/{client_id}/routing
GET /v1/admin/clients/{client_id}/routing
POST /v1/admin/clients/{client_id}/rollback/{version}
GET /v1/admin/clients/{client_id}/config-history

# Operations
GET /v1/dlq
POST /v1/delivery/{delivery_id}/replay
GET /v1/audit-logs
```

#### Client API (Per-Client)
```bash
GET /v1/clients/me
GET /v1/clients/me/delivery-status
```

#### SMS Webhooks
```bash
POST /v1/sms/inbound - Twilio SMS responses for scheduling
```

### 🧪 **Testing**

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test suites
pytest app/tests/test_dlq_behavior.py
pytest app/tests/test_delivery_replay.py
pytest app/tests/test_scheduling_flow.py
pytest app/tests/test_client_provisioning.py
pytest app/tests/test_config_versioning.py
```

### 📖 **Environment Variables**

```bash
# Core Configuration
DATABASE_URL=postgresql+asyncpg://lexicon:lexicon@localhost:5432/lexicon_intake
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-secret-key

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=false

# Security
WEBHOOK_SIGNING_SECRET=your-webhook-secret
ADMIN_API_KEY=your-admin-api-key

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60

# CORS (disabled by default for security)
CORS_ENABLED=false
CORS_ORIGINS=

# Twilio SMS
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_FROM_NUMBER=+15550000000

# SendGrid Email
SENDGRID_API_KEY=your_sendgrid_api_key
EMAIL_FROM=noreply@yourcompany.com

# Logging
LOG_LEVEL=INFO
```

### 🏗️ **Database Schema**

#### Key Tables

- **client_configs**: Client configuration with versioning
- **config_snapshots**: Configuration history for rollback
- **audit_logs**: Complete audit trail of all actions
- **call_records**: Inbound call events
- **lead_records**: Qualified leads with routing and scheduling
- **delivery_records**: Delivery attempts with DLQ tracking

#### Phase 3 Schema Additions

- **config_snapshots**: Version history and rollback support
- **audit_logs**: Comprehensive audit trail
- **delivery_records.failed_final**: DLQ marking
- **delivery_records.failure_reason**: Detailed failure context
- **lead_records.scheduled_***: Scheduling window selection

### 🎯 **Architecture Principles**

#### Stateless Design
- All request handling is stateless
- No in-memory session persistence
- All state externalized to database or Redis
- Workers use stored routing decisions (no recomputation)

#### Deterministic Behavior
- Service type normalization uses keyword matching only
- Routing profile selection is first-match-wins (ordered)
- Business hours calculation is deterministic based on timezone
- Scheduling windows are calculated from fixed offsets
- No ML/AI - rule-based only

#### Idempotency
- Call ID deduplication prevents duplicate lead creation
- Delivery records track attempts and prevent duplicate delivery
- Follow-up messages are tied to lead classification
- Delivery replay creates new attempts (idempotent per delivery_id)

#### Auditability
- All configuration changes are logged with before/after states
- All routing decisions are persisted with reason codes
- Service type normalization is logged with matched keywords
- Scheduling responses are tracked with audit events
- Delivery replays are logged with full context

### 🔧 **Troubleshooting**

#### Common Issues

1. **Scheduling Not Working**: Check `scheduling.enabled` in routing config
2. **DLQ Growing**: Monitor failure reasons and external service health
3. **Rollback Fails**: Verify snapshot exists for target version
4. **Client Access Denied**: Check API key format and client ID extraction
5. **Delivery Replays**: Ensure delivery is in FAILED_FINAL state

#### Debug Logs

Enable debug logging to see detailed operations:

```bash
LOG_LEVEL=DEBUG docker compose up api
```

Look for these log patterns:
- `Configuration updated` - Config changes with version
- `Delivery replay created` - Replay operations
- `Scheduling selection processed` - SMS responses
- `Configuration rolled back` - Rollback operations
- `Audit event` - All audit trail entries

### 📄 **License**

MIT License - see LICENSE file for details.

---

**Version**: v0.3.0 (Phase 3 Complete)

The system now provides a **fully productized, operationally safe, self-serve intake platform** with scheduling-lite, client provisioning, configuration versioning, dead letter queue handling, and comprehensive audit trails while maintaining all architectural constraints: stateless design, deterministic behavior, clear separation of concerns, and full auditability.

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
