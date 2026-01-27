"""Phase 2 delivery channels and follow-up automation

Revision ID: 0002
Revises: 0001
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to client_configs
    op.add_column('client_configs', sa.Column('delivery_channels', postgresql.ARRAY(sa.String()), nullable=False, server_default=sa.text("ARRAY['WEBHOOK']")))
    op.add_column('client_configs', sa.Column('sms_to_numbers', postgresql.ARRAY(sa.String()), nullable=True))
    op.add_column('client_configs', sa.Column('email_to_addresses', postgresql.ARRAY(sa.String()), nullable=True))
    op.add_column('client_configs', sa.Column('message_templates', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column('client_configs', sa.Column('followup_flags', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    
    # Drop and recreate delivery_records table with new schema
    op.drop_table('delivery_records')
    
    op.create_table('delivery_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('lead_id', sa.String(length=255), nullable=False),
        sa.Column('channel', sa.Enum('WEBHOOK', 'SMS', 'EMAIL', name='deliverychannel'), nullable=False),
        sa.Column('purpose', sa.Enum('LEAD_DELIVERY', 'FOLLOWUP_CONFIRMATION', 'FOLLOWUP_REMINDER', 'URGENT_ESCALATION', name='deliverypurpose'), nullable=False),
        sa.Column('destination', sa.Text(), nullable=False),
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
    op.create_index(op.f('ix_delivery_records_channel'), 'delivery_records', ['channel'], unique=False)
    op.create_index(op.f('ix_delivery_records_lead_id'), 'delivery_records', ['lead_id'], unique=False)
    op.create_index(op.f('ix_delivery_records_purpose'), 'delivery_records', ['purpose'], unique=False)
    op.create_index(op.f('ix_delivery_records_status'), 'delivery_records', ['status'], unique=False)
    op.create_index('idx_delivery_records_created_at', 'delivery_records', ['created_at'], unique=False)
    
    # Add SAME_DAY to urgency enum
    op.execute("ALTER TYPE urgencylevel ADD VALUE 'SAME_DAY'")
    
    # Create indexes for new client_config columns
    op.create_index('idx_client_configs_delivery_channels', 'client_configs', ['delivery_channels'], unique=False)


def downgrade() -> None:
    # Remove indexes
    op.drop_index('idx_client_configs_delivery_channels', table_name='client_configs')
    op.drop_index('idx_delivery_records_created_at', table_name='delivery_records')
    op.drop_index(op.f('ix_delivery_records_status'), table_name='delivery_records')
    op.drop_index(op.f('ix_delivery_records_purpose'), table_name='delivery_records')
    op.drop_index(op.f('ix_delivery_records_lead_id'), table_name='delivery_records')
    op.drop_index(op.f('ix_delivery_records_channel'), table_name='delivery_records')
    
    # Drop and recreate delivery_records table with old schema
    op.drop_table('delivery_records')
    
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
    
    # Remove new columns from client_configs
    op.drop_column('client_configs', 'followup_flags')
    op.drop_column('client_configs', 'message_templates')
    op.drop_column('client_configs', 'email_to_addresses')
    op.drop_column('client_configs', 'sms_to_numbers')
    op.drop_column('client_configs', 'delivery_channels')
    
    # Note: We don't remove SAME_DAY from urgency enum as PostgreSQL doesn't support removing enum values
    # This is a known limitation and doesn't affect functionality
