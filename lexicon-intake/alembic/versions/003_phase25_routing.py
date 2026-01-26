"""Phase 2.5 routing and service type normalization

Revision ID: 0003
Revises: 0002
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to client_configs
    op.add_column('client_configs', sa.Column('routing_json', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    
    # Add new columns to lead_records
    op.add_column('lead_records', sa.Column('service_type_normalized', sa.Enum('hvac_repair', 'hvac_install', 'plumbing', 'pressure_wash', 'restoration', 'unknown', name='servicetype'), nullable=True))
    op.add_column('lead_records', sa.Column('service_normalization_reason_codes', postgresql.ARRAY(sa.String()), nullable=True))
    op.add_column('lead_records', sa.Column('routing_profile_name', sa.String(length=255), nullable=True))
    op.add_column('lead_records', sa.Column('time_window', sa.Enum('IN_HOURS', 'AFTER_HOURS', name='timewindow'), nullable=True))
    op.add_column('lead_records', sa.Column('timezone_used', sa.String(length=50), nullable=True))
    op.add_column('lead_records', sa.Column('computed_local_time', sa.DateTime(timezone=True), nullable=True))
    op.add_column('lead_records', sa.Column('chosen_channels', postgresql.ARRAY(sa.String()), nullable=True))
    op.add_column('lead_records', sa.Column('chosen_destinations', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column('lead_records', sa.Column('routing_reason_codes', postgresql.ARRAY(sa.String()), nullable=True))
    
    # Update delivery_pending to be a string for better compatibility
    op.alter_column('lead_records', 'delivery_pending',
                    existing_type=sa.String(length=20),
                    type_=sa.String(length=20),
                    existing_nullable=False,
                    server_default='true')
    
    # Create indexes for new routing fields
    op.create_index('idx_lead_records_service_type', 'lead_records', ['service_type_normalized'], unique=False)
    op.create_index('idx_lead_records_routing_profile', 'lead_records', ['routing_profile_name'], unique=False)
    op.create_index('idx_lead_records_time_window', 'lead_records', ['time_window'], unique=False)


def downgrade() -> None:
    # Remove indexes
    op.drop_index('idx_lead_records_time_window', table_name='lead_records')
    op.drop_index('idx_lead_records_routing_profile', table_name='lead_records')
    op.drop_index('idx_lead_records_service_type', table_name='lead_records')
    
    # Remove new columns from lead_records
    op.drop_column('lead_records', 'routing_reason_codes')
    op.drop_column('lead_records', 'chosen_destinations')
    op.drop_column('lead_records', 'chosen_channels')
    op.drop_column('lead_records', 'computed_local_time')
    op.drop_column('lead_records', 'timezone_used')
    op.drop_column('lead_records', 'time_window')
    op.drop_column('lead_records', 'routing_profile_name')
    op.drop_column('lead_records', 'service_normalization_reason_codes')
    op.drop_column('lead_records', 'service_type_normalized')
    
    # Remove new column from client_configs
    op.drop_column('client_configs', 'routing_json')
    
    # Note: We don't drop the enum types as PostgreSQL doesn't support removing enum values
    # This is a known limitation and doesn't affect functionality
