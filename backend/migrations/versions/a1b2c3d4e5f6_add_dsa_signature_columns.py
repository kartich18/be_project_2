"""Add DSA signature columns to transactions

Revision ID: a1b2c3d4e5f6
Revises: 32e59cb40f96
Create Date: 2026-04-19 11:33:00.000000

Adds five nullable columns to the `transactions` table to store
digital signature telemetry for both the classical (RSA-PSS) and
post-quantum (ML-DSA) pipelines:

  sign_time_ms         — time in ms to produce the signature
  verify_time_ms       — time in ms to verify the signature
  dsa_algorithm        — algorithm used ("RSA-PSS" / "ML-DSA-44/65/87")
  dsa_public_key_bytes — DSA public key size in bytes
  signature_size_bytes — signature output size in bytes

All columns are nullable and default to NULL, making this migration
fully backward-compatible with existing rows.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '32e59cb40f96'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('transactions', sa.Column('sign_time_ms',         sa.Float(),      nullable=True))
    op.add_column('transactions', sa.Column('verify_time_ms',       sa.Float(),      nullable=True))
    op.add_column('transactions', sa.Column('dsa_algorithm',        sa.String(16),   nullable=True))
    op.add_column('transactions', sa.Column('dsa_public_key_bytes', sa.Integer(),    nullable=True))
    op.add_column('transactions', sa.Column('signature_size_bytes', sa.Integer(),    nullable=True))


def downgrade() -> None:
    op.drop_column('transactions', 'signature_size_bytes')
    op.drop_column('transactions', 'dsa_public_key_bytes')
    op.drop_column('transactions', 'dsa_algorithm')
    op.drop_column('transactions', 'verify_time_ms')
    op.drop_column('transactions', 'sign_time_ms')
