#!/bin/bash

# Initialize database with seed data

set -e

echo "Initializing database..."

# Wait for database to be ready
until python -c "
import asyncio
import asyncpg
async def check():
    try:
        conn = await asyncpg.connect('postgresql+asyncpg://lexicon:lexicon@localhost:5432/lexicon_intake')
        await conn.close()
        print('Database is ready')
    except Exception as e:
        print(f'Database not ready: {e}')
        exit(1)
asyncio.run(check())
"; do
    echo "Waiting for database..."
    sleep 2
done

# Run migrations
echo "Running migrations..."
alembic upgrade head

# Seed default client configuration
echo "Seeding default client configuration..."
python -c "
import asyncio
import json
from app.db.session import get_async_session
from app.db.tables.client_config import ClientConfig

async def seed_data():
    async with get_async_session() as session:
        # Check if demo client already exists
        existing = await session.execute(
            'SELECT client_id FROM client_configs WHERE client_id = :client_id',
            {'client_id': 'demo'}
        )
        if existing.fetchone():
            print('Demo client already exists')
            return
        
        # Create demo client with Phase 2 configuration
        demo_client = ClientConfig(
            client_id='demo',
            to_number='+15550001111',
            greeting='Thanks for calling.',
            rules_json=json.dumps({
                'service_types_allowed': ['plumbing', 'electrical', 'hvac'],
                'service_area_zip_prefixes': ['90210', '90211', '90212'],
                'min_budget': 100,
                'urgency_allowed': ['low', 'medium', 'high', 'same_day']
            }),
            delivery_channels=['WEBHOOK'],
            webhook_url='http://requestbin.local/',
            sms_to_numbers=[],
            email_to_addresses=[],
            message_templates={
                'sms_summary_template': 'New lead: {service_requested} from {caller_phone}. Urgency: {urgency}. Status: {classification}.',
                'sms_confirmation_template': 'Thanks — we received your request for {service_requested}. We\'ll follow up soon.',
                'sms_reminder_template': 'Quick check-in: we\'re reviewing your request. Reply YES if you still need help today.',
                'sms_escalation_template': 'URGENT lead: {service_requested} from {caller_phone} needs same-day service.',
                'email_subject_template': 'New Lead: {service_requested} ({classification})',
                'email_body_template': '''Lead Summary:

Lead ID: {lead_id}
Call ID: {call_id}
Caller: {caller_name}
Phone: {caller_phone}
Service: {service_requested}
Urgency: {urgency}
Budget: {budget}
Location: {location_zip}
Classification: {classification}
Qualification: {qualification_outcome}
Reason Codes: {reason_codes}
Timestamp: {timestamp}'''
            },
            followup_flags={
                'send_confirmation_to_caller': False,
                'send_reminder_to_caller': False,
                'reminder_delay_minutes': 30,
                'urgent_escalation': False
            },
            followup_enabled=False,
            followup_confirmation_enabled=False,
            followup_reminder_enabled=False,
            followup_escalation_enabled=False
        )
        
        session.add(demo_client)
        await session.commit()
        print('Demo client created successfully with Phase 2 configuration')

asyncio.run(seed_data())
"

echo "Database initialization complete!"
