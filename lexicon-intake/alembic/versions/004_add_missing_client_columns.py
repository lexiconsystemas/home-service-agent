"""Add missing client_configs columns and rename greeting to greeting_message

Revision ID: 0004
Revises: 0003
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rename greeting to greeting_message
    op.alter_column('client_configs', 'greeting', new_column_name='greeting_message')

    # Add missing columns
    op.add_column('client_configs', sa.Column('client_api_key', sa.String(length=255), nullable=True))
    op.add_column('client_configs', sa.Column('version', sa.Integer(), nullable=False, server_default='1'))

    # Create index on client_api_key for fast lookups
    op.create_index('idx_client_configs_api_key', 'client_configs', ['client_api_key'], unique=True)


def downgrade() -> None:
    # Remove index
    op.drop_index('idx_client_configs_api_key', table_name='client_configs')

    # Remove new columns
    op.drop_column('client_configs', 'version')
    op.drop_column('client_configs', 'client_api_key')

    # Rename greeting_message back to greeting
    op.alter_column('client_configs', 'greeting_message', new_column_name='greeting')
