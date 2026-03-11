"""Add missing indexes on c_invoiceline and c_orderline for query performance.

The JOIN c_invoiceline → m_product was doing a seq scan because m_product_id
had no index. This caused 90-100s response times on supply purchase queries.

Revision ID: 005_invoiceline_indexes
Revises: 004_historical
Create Date: 2026-03-11
"""
from alembic import op

revision = "005_invoiceline_indexes"
down_revision = "004_historical"
branch_labels = None
depends_on = None


def upgrade():
    # c_invoiceline.m_product_id — used by 4 queries that JOIN to m_product
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_hist_cinvl_product "
        "ON adempiere.c_invoiceline(m_product_id)"
    )

    # c_orderline.m_product_id — used by purchase order queries
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_hist_cordl_product "
        "ON adempiere.c_orderline(m_product_id)"
    )

    # c_orderline.c_order_id — used by JOINs from c_order to c_orderline
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_hist_cordl_order "
        "ON adempiere.c_orderline(c_order_id)"
    )

    # c_allocationline.c_invoice_id — used by payment status queries
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_hist_allocl_invoice "
        "ON adempiere.c_allocationline(c_invoice_id)"
    )


def downgrade():
    op.execute("DROP INDEX IF EXISTS adempiere.idx_hist_cinvl_product")
    op.execute("DROP INDEX IF EXISTS adempiere.idx_hist_cordl_product")
    op.execute("DROP INDEX IF EXISTS adempiere.idx_hist_cordl_order")
    op.execute("DROP INDEX IF EXISTS adempiere.idx_hist_allocl_invoice")
