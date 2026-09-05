import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
import django
django.setup()

from django.db import connection

def fix_schema():
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        all_tables = set(row[0] for row in cursor.fetchall())

        # 1. CustomerMasterLongTermContractBasicDetail
        if 'customer_master_longtermcontracts_basicdetails' in all_tables:
            cursor.execute("DESCRIBE customer_master_longtermcontracts_basicdetails;")
            cols = set(r[0] for r in cursor.fetchall())
            if 'is_paused' not in cols:
                print("Adding is_paused to customer_master_longtermcontracts_basicdetails")
                cursor.execute("ALTER TABLE customer_master_longtermcontracts_basicdetails ADD COLUMN is_paused tinyint(1) NOT NULL DEFAULT 0;")

        # 2. GSTR3BReport
        if 'gst_reconciliation_gstr3b_reports' in all_tables:
            cursor.execute("DESCRIBE gst_reconciliation_gstr3b_reports;")
            cols = set(r[0] for r in cursor.fetchall())
            if 'status' not in cols:
                print("Adding status to gst_reconciliation_gstr3b_reports")
                cursor.execute("ALTER TABLE gst_reconciliation_gstr3b_reports ADD COLUMN status varchar(50) NOT NULL DEFAULT 'DRAFT';")
            if 'arn_number' not in cols:
                print("Adding arn_number to gst_reconciliation_gstr3b_reports")
                cursor.execute("ALTER TABLE gst_reconciliation_gstr3b_reports ADD COLUMN arn_number varchar(100) NULL;")
            if 'filed_date' not in cols:
                print("Adding filed_date to gst_reconciliation_gstr3b_reports")
                cursor.execute("ALTER TABLE gst_reconciliation_gstr3b_reports ADD COLUMN filed_date datetime(6) NULL;")

        # 3. PendingPurchase
        if 'pending_purchase_queue' in all_tables:
            cursor.execute("DESCRIBE pending_purchase_queue;")
            cols = set(r[0] for r in cursor.fetchall())
            if 'company_match_detected' not in cols:
                print("Adding company_match_detected to pending_purchase_queue")
                cursor.execute("ALTER TABLE pending_purchase_queue ADD COLUMN company_match_detected tinyint(1) NOT NULL DEFAULT 0;")
            if 'company_match_decision' not in cols:
                print("Adding company_match_decision to pending_purchase_queue")
                cursor.execute("ALTER TABLE pending_purchase_queue ADD COLUMN company_match_decision varchar(50) NULL;")

        # 4. Missing Tables
        if 'gst_electronic_ledgers' not in all_tables:
            print("Creating gst_electronic_ledgers")
            cursor.execute("""
            CREATE TABLE `gst_electronic_ledgers` (
              `id` bigint NOT NULL AUTO_INCREMENT,
              `tenant_id` char(36) NOT NULL,
              `ledger_type` varchar(20) NOT NULL,
              `return_period` varchar(10) NOT NULL,
              `financial_year` varchar(10) NOT NULL,
              `igst_amount` decimal(15,2) NOT NULL DEFAULT '0.00',
              `cgst_amount` decimal(15,2) NOT NULL DEFAULT '0.00',
              `sgst_amount` decimal(15,2) NOT NULL DEFAULT '0.00',
              `cess_amount` decimal(15,2) NOT NULL DEFAULT '0.00',
              `total_amount` decimal(15,2) NOT NULL DEFAULT '0.00',
              `balance_as_on` datetime(6) NULL,
              `created_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
              `updated_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
              PRIMARY KEY (`id`),
              KEY `idx_gst_el_tenant` (`tenant_id`),
              KEY `idx_gst_el_type_period` (`tenant_id`, `ledger_type`, `return_period`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """)

        if 'gst_late_fees' not in all_tables:
            print("Creating gst_late_fees")
            cursor.execute("""
            CREATE TABLE `gst_late_fees` (
              `id` bigint NOT NULL AUTO_INCREMENT,
              `tenant_id` char(36) NOT NULL,
              `return_type` varchar(20) NOT NULL,
              `return_period` varchar(10) NOT NULL,
              `financial_year` varchar(10) NOT NULL,
              `cgst_fee` decimal(15,2) NOT NULL DEFAULT '0.00',
              `sgst_fee` decimal(15,2) NOT NULL DEFAULT '0.00',
              `total_fee` decimal(15,2) NOT NULL DEFAULT '0.00',
              `cgst_interest` decimal(15,2) NOT NULL DEFAULT '0.00',
              `sgst_interest` decimal(15,2) NOT NULL DEFAULT '0.00',
              `total_interest` decimal(15,2) NOT NULL DEFAULT '0.00',
              `calculated_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
              `created_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
              `updated_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
              PRIMARY KEY (`id`),
              KEY `idx_gst_lf_tenant` (`tenant_id`),
              KEY `idx_gst_lf_period` (`tenant_id`, `return_type`, `return_period`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """)

        if 'rag_active_index' not in all_tables:
            print("Creating rag_active_index")
            cursor.execute("""
            CREATE TABLE `rag_active_index` (
              `id` bigint NOT NULL AUTO_INCREMENT,
              `index_name` varchar(255) NOT NULL,
              `active_version` varchar(100) NOT NULL,
              `updated_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
              PRIMARY KEY (`id`),
              UNIQUE KEY `idx_rag_active_name` (`index_name`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """)

        if 'rag_reindex_jobs' not in all_tables:
            print("Creating rag_reindex_jobs")
            cursor.execute("""
            CREATE TABLE `rag_reindex_jobs` (
              `id` bigint NOT NULL AUTO_INCREMENT,
              `job_id` varchar(100) NOT NULL,
              `status` varchar(50) NOT NULL,
              `details` text NULL,
              `created_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
              `updated_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
              PRIMARY KEY (`id`),
              UNIQUE KEY `idx_rag_job_id` (`job_id`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """)

    print("Schema alignment complete!")

if __name__ == "__main__":
    fix_schema()
