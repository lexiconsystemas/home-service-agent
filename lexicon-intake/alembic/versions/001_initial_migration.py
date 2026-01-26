"""Initial migration

Revision ID: 0001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create client_configs table
    op.create_table('client_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('client_id', sa.String(length=100), nullable=False),
        sa.Column('to_number', sa.String(length=20), nullable=False),
        sa.Column('greeting', sa.Text(), nullable=True),
        sa.Column('rules_json', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('webhook_url', sa.Text(), nullable=True),
        sa.Column('followup_enabled', sa.Boolean(), nullable=False),
        sa.Column('followup_confirmation_enabled', sa.Boolean(), nullable=False),
        sa.Column('followup_reminder_enabled', sa.Boolean(), nullable=False),
        sa.Column('followup_escalation_enabled', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('client_id')
    )
    op.create_index(op.f('ix_client_configs_client_id'), 'client_configs', ['client_id'], unique=False)
    op.create_index(op.f('ix_client_configs_to_number'), 'client_configs', ['to_number'], unique=False)

    # Create call_records table
    op.create_table('call_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('call_id', sa.String(length=255), nullable=False),
        sa.Column('from_number', sa.String(length=20), nullable=False),
        sa.Column('to_number', sa.String(length=20), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('call_id')
    )
    op.create_index(op.f('ix_call_records_call_id'), 'call_records', ['call_id'], unique=False)
    op.create_index('idx_call_records_processed_at', 'call_records', ['processed_at'], unique=False)

    # Create lead_records table
    op.create_table('lead_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('lead_id', sa.String(length=255), nullable=False),
        sa.Column('call_id', sa.String(length=255), nullable=False),
        sa.Column('client_id', sa.String(length=100), nullable=False),
        sa.Column('caller_name', sa.String(length=255), nullable=True),
        sa.Column('caller_phone', sa.String(length=20), nullable=False),
        sa.Column('service_requested', sa.String(length=100), nullable=True),
        sa.Column('urgency', sa.Enum('LOW', 'MEDIUM', 'HIGH', name='urgencylevel'), nullable=False),
        sa.Column('budget', sa.String(length=20), nullable=True),
        sa.Column('location_zip', sa.String(length=10), nullable=True),
        sa.Column('classification', sa.Enum('QUALIFIED', 'UNQUALIFIED', 'SPAM', 'DROPPED', name='callclassification'), nullable=False),
        sa.Column('reason_codes', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('qualification_outcome', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('lead_id')
    )
    op.create_index(op.f('ix_lead_records_call_id'), 'lead_records', ['call_id'], unique=False)
    op.create_index(op.f('ix_lead_records_client_id'), 'lead_records', ['client_id'], unique=False)
    op.create_index(op.f('ix_lead_records_classification'), 'lead_records', ['classification'], unique=False)
    op.create_index(op.f('ix_lead_records_lead_id'), 'lead_records', ['lead_id'], unique=False)
    op.create_index('idx_lead_records_created_at', 'lead_records', ['created_at'], unique=False)

    # Create delivery_records table
    op.create_table('delivery_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('lead_id', sa.String(length=255), nullable=False),
        sa.Column('webhook_url', sa.Text(), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'SENT', 'FAILED', 'RETRYING', name='deliverystatus'), nullable=False),
        sa.Column('attempt_count', sa.Integer(), nullable=False),
        sa.Column('last_attempt_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('response_status_code', sa.Integer(), nullable=True),
        sa.Column('response_body', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_delivery_records_lead_id'), 'delivery_records', ['lead_id'], unique=False)
    op.create_index(op.f('ix_delivery_records_status'), 'delivery_records', ['status'], unique=False)
    op.create_index('idx_delivery_records_created_at', 'delivery_records', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_delivery_records_created_at', table_name='delivery_records')
    op.drop_index(op.f('ix_delivery_records_status'), table_name='delivery_records')
    op.drop_index(op.f('ix_delivery_records_lead_id'), table_name='delivery_records')
    op.drop_table('delivery_records')
    op.drop_index('idx_lead_records_created_at', table_name='lead_records')
    op.drop_index(op.f('ix_lead_records_classification'), table_name='lead_records')
    op.drop_index(op.f('ix_lead_records_lead_id'), table_name='lead_records')
    op.drop_index(op.f('ix_lead_records_client_id'), table_name='lead_records')
    op.drop_index(op.f('ix_lead_records_call_id'), table_name='lead_records')
    op.drop_table('lead_records')
    op.drop_index('idx_call_records_processed_at', table_name='call_records')
    op.drop_index(op.f('ix_call_records_call_id'), table_name='call_records')
    op.drop_table('call_records')
    op.drop_index(op.f('ix_client_configs_to_number'), table_name='client_configs')
    op.drop_index(op.f('ix_client_configs_client_id'), table_name='client_configs')
    op.drop_table('client_configs')
    op.execute('DROP TYPE IF EXISTS deliverystatus')
    op.execute('DROP TYPE IF EXISTS callclassification')
    op.execute('DROP TYPE IF EXISTS urgencylevel')
