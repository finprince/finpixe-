from django.db import connection

sql_statements = [
    """
    CREATE TABLE IF NOT EXISTS `accounting_cache_table` (
      `cache_key` varchar(255) NOT NULL,
      `value` longtext NOT NULL,
      `expires` datetime(6) NOT NULL,
      PRIMARY KEY (`cache_key`),
      KEY `accounting_cache_table_expires` (`expires`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
    """,
    """
    CREATE TABLE IF NOT EXISTS `advance_allocation` (
      `id` bigint NOT NULL AUTO_INCREMENT,
      `tenant_id` varchar(36) DEFAULT NULL,
      `created_at` datetime(6) DEFAULT NULL,
      `updated_at` datetime(6) DEFAULT NULL,
      `type` varchar(50) DEFAULT NULL,
      `reference_id` varchar(150) DEFAULT NULL,
      `reference_number` varchar(150) DEFAULT NULL,
      `reference_type` varchar(20) NOT NULL,
      `invoice_date` date DEFAULT NULL,
      `pending_before` decimal(25,2) NOT NULL,
      `balance_after` decimal(25,2) NOT NULL,
      `party_vendor_id` bigint DEFAULT NULL,
      `pay_from_ledger_id` bigint DEFAULT NULL,
      `pay_to_ledger_id` bigint DEFAULT NULL,
      `transaction_id` bigint NOT NULL,
      `advance_ref_no` varchar(150) DEFAULT NULL,
      `is_advance` tinyint(1) NOT NULL,
      `ledger_id_val` bigint DEFAULT NULL,
      `party_customer_id` bigint DEFAULT NULL,
      `pay_from_customer_id_val` bigint DEFAULT NULL,
      `pay_from_ledger_id_val` bigint DEFAULT NULL,
      `pay_from_vendor_id_val` bigint DEFAULT NULL,
      `pay_to_customer_id_val` bigint DEFAULT NULL,
      `pay_to_ledger_id_val` bigint DEFAULT NULL,
      `pay_to_vendor_id_val` bigint DEFAULT NULL,
      `receive_from_customer_id_val` bigint DEFAULT NULL,
      `receive_from_ledger_id_val` bigint DEFAULT NULL,
      `receive_from_vendor_id_val` bigint DEFAULT NULL,
      `receive_in_customer_id_val` bigint DEFAULT NULL,
      `receive_in_ledger_id_val` bigint DEFAULT NULL,
      `receive_in_vendor_id_val` bigint DEFAULT NULL,
      `due_date` date DEFAULT NULL,
      `due_status` varchar(50) DEFAULT NULL,
      `original_amount` decimal(25,2) NOT NULL,
      `allocated_amount` decimal(25,2) DEFAULT NULL,
      `advance_source_id` bigint DEFAULT NULL,
      `advance_source_type` varchar(20) DEFAULT NULL,
      `amount` decimal(25,2) DEFAULT NULL,
      `posting_note` longtext,
      `vouch_amount` decimal(25,2) NOT NULL,
      `ref_no` varchar(150) DEFAULT NULL,
      `narration` longtext,
      `gst_rate` decimal(5,2) DEFAULT NULL,
      `gst_registered` varchar(3) NOT NULL,
      `amendment_date` date DEFAULT NULL,
      `original_voucher_snapshot` json DEFAULT NULL,
      `amendment_filed` tinyint(1) NOT NULL,
      PRIMARY KEY (`id`),
      KEY `advance_allocation_pay_from_ledger_id_0eaeca7e_fk_master_le` (`pay_from_ledger_id`),
      KEY `advance_allocation_pay_to_ledger_id_336922ab_fk_master_le` (`pay_to_ledger_id`),
      KEY `advance_allocation_transaction_id_7b578e38_fk_transactions_id` (`transaction_id`),
      KEY `advance_allocation_tenant_id_6b213cf4` (`tenant_id`),
      KEY `advance_allocation_reference_id_f39d041b` (`reference_id`),
      KEY `advance_allocation_reference_number_ed664d75` (`reference_number`),
      KEY `advance_allocation_adv_src_idx` (`advance_source_id`),
      CONSTRAINT `advance_allocation_pay_from_ledger_id_0eaeca7e_fk_master_le` FOREIGN KEY (`pay_from_ledger_id`) REFERENCES `master_ledgers` (`id`),
      CONSTRAINT `advance_allocation_pay_to_ledger_id_336922ab_fk_master_le` FOREIGN KEY (`pay_to_ledger_id`) REFERENCES `master_ledgers` (`id`),
      CONSTRAINT `advance_allocation_transaction_id_7b578e38_fk_transactions_id` FOREIGN KEY (`transaction_id`) REFERENCES `transactions` (`id`)
    ) ENGINE=InnoDB AUTO_INCREMENT=159 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
    """
]

with connection.cursor() as cursor:
    for idx, stmt in enumerate(sql_statements, 1):
        cursor.execute(stmt)
        print(f"Statement {idx} executed successfully.")

    cursor.execute("SHOW TABLES LIKE 'accounting_cache_table';")
    print("accounting_cache_table:", cursor.fetchall())
    cursor.execute("SHOW TABLES LIKE 'advance_allocation';")
    print("advance_allocation:", cursor.fetchall())
