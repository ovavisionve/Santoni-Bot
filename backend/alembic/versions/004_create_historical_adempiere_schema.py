"""Create adempiere schema in local DB for historical data snapshots.

Mirrors the iDempiere table structure (only columns used by agents)
so that existing SQL queries work unchanged against the local copy.

Data is populated by: scripts/extract_historical_data.py

Revision ID: 004_historical
Revises: 003_add_vendedor_role_and_salesrep
Create Date: 2026-03-10
"""
from alembic import op
import sqlalchemy as sa

revision = "004_historical"
down_revision = "003_add_vendedor_role_and_salesrep"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create the adempiere schema in the local DB
    op.execute("CREATE SCHEMA IF NOT EXISTS adempiere")

    # ── Reference / Dimension Tables (copied fully) ─────────────────────

    op.execute("""
        CREATE TABLE IF NOT EXISTS adempiere.ad_org (
            ad_org_id INTEGER PRIMARY KEY,
            value VARCHAR(60),
            name VARCHAR(120),
            isactive CHAR(1) DEFAULT 'Y',
            issummary CHAR(1) DEFAULT 'N'
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS adempiere.c_currency (
            c_currency_id INTEGER PRIMARY KEY,
            iso_code VARCHAR(3),
            cursymbol VARCHAR(10),
            description VARCHAR(255)
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS adempiere.c_bpartner (
            c_bpartner_id INTEGER PRIMARY KEY,
            ad_org_id INTEGER,
            value VARCHAR(60),
            name VARCHAR(120),
            isactive CHAR(1) DEFAULT 'Y',
            iscustomer CHAR(1) DEFAULT 'N',
            isvendor CHAR(1) DEFAULT 'N',
            isemployee CHAR(1) DEFAULT 'N',
            ismayorista CHAR(1),
            isclap CHAR(1),
            ispublico CHAR(1),
            codigoventas VARCHAR(60),
            codigoproductor VARCHAR(60),
            codigocompras VARCHAR(60),
            c_bp_group_id INTEGER,
            salesrep_id INTEGER
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS adempiere.c_bp_group (
            c_bp_group_id INTEGER PRIMARY KEY,
            name VARCHAR(120),
            isactive CHAR(1) DEFAULT 'Y'
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS adempiere.c_salesregion (
            c_salesregion_id INTEGER PRIMARY KEY,
            name VARCHAR(120),
            isactive CHAR(1) DEFAULT 'Y'
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS adempiere.c_bpartner_location (
            c_bpartner_location_id INTEGER PRIMARY KEY,
            c_bpartner_id INTEGER,
            c_salesregion_id INTEGER,
            c_location_id INTEGER,
            isactive CHAR(1) DEFAULT 'Y'
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS adempiere.c_location (
            c_location_id INTEGER PRIMARY KEY,
            c_city_id INTEGER,
            c_region_id INTEGER,
            address1 VARCHAR(255),
            city VARCHAR(120)
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS adempiere.c_region (
            c_region_id INTEGER PRIMARY KEY,
            name VARCHAR(120)
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS adempiere.c_city (
            c_city_id INTEGER PRIMARY KEY,
            name VARCHAR(120),
            c_region_id INTEGER
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS adempiere.c_doctype (
            c_doctype_id INTEGER PRIMARY KEY,
            name VARCHAR(120),
            docbasetype VARCHAR(10),
            isactive CHAR(1) DEFAULT 'Y',
            description VARCHAR(255)
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS adempiere.m_product (
            m_product_id INTEGER PRIMARY KEY,
            ad_org_id INTEGER,
            value VARCHAR(60),
            name VARCHAR(255),
            m_product_category_id INTEGER,
            isactive CHAR(1) DEFAULT 'Y',
            producttype CHAR(1),
            issold CHAR(1),
            ispurchased CHAR(1)
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS adempiere.m_product_category (
            m_product_category_id INTEGER PRIMARY KEY,
            name VARCHAR(120),
            value VARCHAR(60),
            isactive CHAR(1) DEFAULT 'Y'
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS adempiere.m_warehouse (
            m_warehouse_id INTEGER PRIMARY KEY,
            ad_org_id INTEGER,
            name VARCHAR(120),
            isactive CHAR(1) DEFAULT 'Y'
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS adempiere.m_locator (
            m_locator_id INTEGER PRIMARY KEY,
            m_warehouse_id INTEGER,
            value VARCHAR(60),
            isactive CHAR(1) DEFAULT 'Y'
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS adempiere.c_paymentterm (
            c_paymentterm_id INTEGER PRIMARY KEY,
            name VARCHAR(120),
            netdays INTEGER DEFAULT 30,
            isactive CHAR(1) DEFAULT 'Y'
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS adempiere.c_bank (
            c_bank_id INTEGER PRIMARY KEY,
            name VARCHAR(120),
            isactive CHAR(1) DEFAULT 'Y'
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS adempiere.c_bankaccount (
            c_bankaccount_id INTEGER PRIMARY KEY,
            c_bank_id INTEGER,
            ad_org_id INTEGER,
            accountno VARCHAR(60),
            c_currency_id INTEGER,
            currentbalance NUMERIC(20,2),
            bankaccounttype CHAR(1),
            isactive CHAR(1) DEFAULT 'Y'
        )
    """)

    # ── HR Reference Tables ─────────────────────────────────────────────

    op.execute("""
        CREATE TABLE IF NOT EXISTS adempiere.hr_department (
            hr_department_id INTEGER PRIMARY KEY,
            name VARCHAR(120),
            isactive CHAR(1) DEFAULT 'Y'
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS adempiere.hr_job (
            hr_job_id INTEGER PRIMARY KEY,
            name VARCHAR(120),
            isactive CHAR(1) DEFAULT 'Y'
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS adempiere.hr_concept (
            hr_concept_id INTEGER PRIMARY KEY,
            value VARCHAR(60),
            name VARCHAR(120),
            type CHAR(1),
            columntype CHAR(1),
            isactive CHAR(1) DEFAULT 'Y'
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS adempiere.hr_payroll (
            hr_payroll_id INTEGER PRIMARY KEY,
            name VARCHAR(120),
            isactive CHAR(1) DEFAULT 'Y'
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS adempiere.hr_employee (
            hr_employee_id INTEGER PRIMARY KEY,
            c_bpartner_id INTEGER,
            ad_org_id INTEGER,
            hr_department_id INTEGER,
            hr_job_id INTEGER,
            startdate DATE,
            enddate DATE,
            isactive CHAR(1) DEFAULT 'Y'
        )
    """)

    # ── Accounting Reference Tables ─────────────────────────────────────

    op.execute("""
        CREATE TABLE IF NOT EXISTS adempiere.c_elementvalue (
            c_elementvalue_id INTEGER PRIMARY KEY,
            value VARCHAR(60),
            name VARCHAR(120),
            accounttype CHAR(1),
            issummary CHAR(1) DEFAULT 'N',
            isactive CHAR(1) DEFAULT 'Y',
            c_element_id INTEGER
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS adempiere.c_element (
            c_element_id INTEGER PRIMARY KEY,
            name VARCHAR(120)
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS adempiere.c_acctschema (
            c_acctschema_id INTEGER PRIMARY KEY,
            name VARCHAR(120)
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS adempiere.c_period (
            c_period_id INTEGER PRIMARY KEY,
            name VARCHAR(120),
            startdate DATE,
            enddate DATE,
            periodno INTEGER
        )
    """)

    # ── Transaction Tables (populated with data < cutoff date) ──────────

    op.execute("""
        CREATE TABLE IF NOT EXISTS adempiere.c_invoice (
            c_invoice_id INTEGER PRIMARY KEY,
            ad_org_id INTEGER,
            c_bpartner_id INTEGER,
            c_currency_id INTEGER,
            c_doctypetarget_id INTEGER,
            c_paymentterm_id INTEGER,
            salesrep_id INTEGER,
            documentno VARCHAR(60),
            dateinvoiced DATE,
            grandtotal NUMERIC(20,2),
            totallines NUMERIC(20,2),
            withholdingamt NUMERIC(20,2),
            issotrx CHAR(1),
            ispaid CHAR(1),
            docstatus VARCHAR(2),
            isactive CHAR(1) DEFAULT 'Y',
            lve_controlnumber VARCHAR(60)
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS adempiere.c_invoiceline (
            c_invoiceline_id INTEGER PRIMARY KEY,
            c_invoice_id INTEGER,
            m_product_id INTEGER,
            qtyinvoiced NUMERIC(20,4),
            priceactual NUMERIC(20,6),
            linenetamt NUMERIC(20,2),
            line INTEGER
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS adempiere.c_payment (
            c_payment_id INTEGER PRIMARY KEY,
            ad_org_id INTEGER,
            c_bpartner_id INTEGER,
            c_currency_id INTEGER,
            c_bankaccount_id INTEGER,
            documentno VARCHAR(60),
            datetrx DATE,
            payamt NUMERIC(20,2),
            isreceipt CHAR(1),
            tendertype CHAR(1),
            docstatus VARCHAR(2),
            isactive CHAR(1) DEFAULT 'Y'
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS adempiere.c_allocationline (
            c_allocationline_id INTEGER PRIMARY KEY,
            c_allocationhdr_id INTEGER,
            c_invoice_id INTEGER,
            c_payment_id INTEGER,
            amount NUMERIC(20,2),
            discountamt NUMERIC(20,2),
            writeoffamt NUMERIC(20,2)
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS adempiere.c_order (
            c_order_id INTEGER PRIMARY KEY,
            ad_org_id INTEGER,
            c_bpartner_id INTEGER,
            c_currency_id INTEGER,
            c_doctype_id INTEGER,
            c_paymentterm_id INTEGER,
            documentno VARCHAR(60),
            dateordered DATE,
            grandtotal NUMERIC(20,2),
            issotrx CHAR(1),
            isdelivered CHAR(1),
            docstatus VARCHAR(2),
            isactive CHAR(1) DEFAULT 'Y',
            -- Agricultural fields for compras_productores
            driver VARCHAR(120),
            plateno VARCHAR(60),
            grossweight NUMERIC(20,4),
            tareweight NUMERIC(20,4),
            netweight NUMERIC(20,4),
            classification VARCHAR(60),
            tipofrijol VARCHAR(60),
            guidemac VARCHAR(60),
            guideproducer VARCHAR(60),
            guidesada VARCHAR(60)
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS adempiere.c_orderline (
            c_orderline_id INTEGER PRIMARY KEY,
            c_order_id INTEGER,
            m_product_id INTEGER,
            qtyordered NUMERIC(20,4),
            priceactual NUMERIC(20,6),
            linenetamt NUMERIC(20,2),
            line INTEGER
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS adempiere.m_inout (
            m_inout_id INTEGER PRIMARY KEY,
            ad_org_id INTEGER,
            c_bpartner_id INTEGER,
            c_doctype_id INTEGER,
            documentno VARCHAR(60),
            movementdate DATE,
            movementtype VARCHAR(2),
            docstatus VARCHAR(2),
            isactive CHAR(1) DEFAULT 'Y'
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS adempiere.m_inoutline (
            m_inoutline_id INTEGER PRIMARY KEY,
            m_inout_id INTEGER,
            m_product_id INTEGER,
            m_locator_id INTEGER,
            movementqty NUMERIC(20,4),
            line INTEGER
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS adempiere.fact_acct (
            fact_acct_id INTEGER PRIMARY KEY,
            ad_org_id INTEGER,
            account_id INTEGER,
            c_acctschema_id INTEGER,
            c_currency_id INTEGER,
            c_period_id INTEGER,
            dateacct DATE,
            amtsourcedr NUMERIC(20,2),
            amtsourcecr NUMERIC(20,2),
            amtacctdr NUMERIC(20,2),
            amtacctcr NUMERIC(20,2),
            postingtype CHAR(1),
            description VARCHAR(255)
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS adempiere.hr_process (
            hr_process_id INTEGER PRIMARY KEY,
            ad_org_id INTEGER,
            hr_payroll_id INTEGER,
            c_period_id INTEGER,
            dateacct DATE,
            documentno VARCHAR(60),
            docstatus VARCHAR(2),
            isactive CHAR(1) DEFAULT 'Y'
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS adempiere.hr_movement (
            hr_movement_id INTEGER PRIMARY KEY,
            hr_process_id INTEGER,
            c_bpartner_id INTEGER,
            hr_concept_id INTEGER,
            amount NUMERIC(20,4),
            qty NUMERIC(20,4)
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS adempiere.m_storageonhand (
            m_product_id INTEGER,
            m_locator_id INTEGER,
            m_attributesetinstance_id INTEGER DEFAULT 0,
            qtyonhand NUMERIC(20,4),
            datelastinventory DATE,
            PRIMARY KEY (m_product_id, m_locator_id, m_attributesetinstance_id)
        )
    """)

    # ── Indexes for performance ─────────────────────────────────────────

    op.execute("CREATE INDEX IF NOT EXISTS idx_hist_cinv_date ON adempiere.c_invoice(dateinvoiced)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_hist_cinv_sotrx ON adempiere.c_invoice(issotrx)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_hist_cinv_bp ON adempiere.c_invoice(c_bpartner_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_hist_cinv_org ON adempiere.c_invoice(ad_org_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_hist_cinvl_inv ON adempiere.c_invoiceline(c_invoice_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_hist_cpay_date ON adempiere.c_payment(datetrx)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_hist_cpay_bp ON adempiere.c_payment(c_bpartner_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_hist_cord_date ON adempiere.c_order(dateordered)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_hist_cord_sotrx ON adempiere.c_order(issotrx)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_hist_minout_date ON adempiere.m_inout(movementdate)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_hist_factacct_date ON adempiere.fact_acct(dateacct)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_hist_factacct_acct ON adempiere.fact_acct(account_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_hist_hrproc_date ON adempiere.hr_process(dateacct)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_hist_hrmov_proc ON adempiere.hr_movement(hr_process_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_hist_hrmov_bp ON adempiere.hr_movement(c_bpartner_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_hist_bpl_bp ON adempiere.c_bpartner_location(c_bpartner_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_hist_storage_prod ON adempiere.m_storageonhand(m_product_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_hist_storage_loc ON adempiere.m_storageonhand(m_locator_id)")

    # ── Metadata table to track extraction status ───────────────────────

    op.execute("""
        CREATE TABLE IF NOT EXISTS adempiere._extraction_metadata (
            id SERIAL PRIMARY KEY,
            extracted_at TIMESTAMP DEFAULT NOW(),
            cutoff_date DATE NOT NULL,
            tables_extracted TEXT[],
            total_rows BIGINT,
            duration_seconds INTEGER,
            notes TEXT
        )
    """)


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS adempiere CASCADE")
