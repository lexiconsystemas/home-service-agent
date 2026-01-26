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
        
        # Create demo client
        demo_client = ClientConfig(
            client_id='demo',
            to_number='+15550001111',
            greeting='Thanks for calling.',
            rules_json=json.dumps({
                'service_types_allowed': ['plumbing', 'electrical', 'hvac'],
                'service_area_zip_prefixes': ['90210', '90211', '90212'],
                'min_budget': 100,
                'urgency_allowed': ['low', 'medium', 'high']
            }),
            webhook_url='http://requestbin.local/',
            followup_enabled=False,
            followup_confirmation_enabled=False,
            followup_reminder_enabled=False,
            followup_escalation_enabled=False
        )
        
        session.add(demo_client)
        await session.commit()
        print('Demo client created successfully')

asyncio.run(seed_data())
"

echo "Database initialization complete!"
