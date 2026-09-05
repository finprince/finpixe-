"""
Controlled Business Data Tools for KIKI AI
==========================================
Deterministic, parameter-bound, multi-tenant database tools querying the MySQL System of Record.
All queries strictly enforce tenant isolation and read-only parameterized execution.
Reuses existing accounting logic and structures.
"""
from typing import Dict, Any, List, Optional
from django.db import connection
from ..logging import get_kiki_logger

logger = get_kiki_logger("business_tools")


def format_inr(amount: Optional[float]) -> str:
    """Format a numerical amount into Indian Rupee currency string (e.g. ₹1,25,000.00)."""
    if amount is None:
        return "₹0.00"
    try:
        val = float(amount)
        # Handle negative
        is_neg = val < 0
        val = abs(val)
        parts = f"{val:.2f}".split(".")
        int_part = parts[0]
        dec_part = parts[1]
        
        if len(int_part) <= 3:
            res = int_part
        else:
            last_3 = int_part[-3:]
            remaining = int_part[:-3]
            # Group by 2 digits from right
            grouped = []
            while remaining:
                grouped.insert(0, remaining[-2:])
                remaining = remaining[:-2]
            res = ",".join(grouped) + "," + last_3
            
        return f"-₹{res}.{dec_part}" if is_neg else f"₹{res}.{dec_part}"
    except Exception:
        return f"₹{amount}"


class BusinessToolsEngine:
    """Enterprise Business Tools Engine providing verified data for Kiki Agent."""

    # ── 1. SALES SUMMARY TOOL ─────────────────────────────────────────────────
    def get_sales_summary(
        self,
        tenant_id: str,
        date_range: Optional[Dict[str, Any]] = None,
        customer_name: Optional[str] = None,
        limit: int = 15
    ) -> Dict[str, Any]:
        """Queries sales vouchers and item details."""
        params: List[Any] = [tenant_id]
        where_clauses = ["tenant_id = %s", "LOWER(type) = 'sales'"]

        if date_range:
            where_clauses.append("date >= %s AND date <= %s")
            params.extend([date_range["start_date"], date_range["end_date"]])

        if customer_name:
            where_clauses.append("LOWER(party) LIKE %s")
            params.append(f"%{customer_name.lower().strip()}%")

        where_sql = " AND ".join(where_clauses)

        # Aggregate metrics
        agg_sql = f"""
            SELECT 
                COUNT(*) as invoice_count,
                COALESCE(SUM(total), 0) as total_sales,
                COALESCE(SUM(total_taxable_amount), 0) as total_taxable,
                COALESCE(SUM(total_cgst), 0) as total_cgst,
                COALESCE(SUM(total_sgst), 0) as total_sgst,
                COALESCE(SUM(total_igst), 0) as total_igst
            FROM vouchers
            WHERE {where_sql}
        """

        # Individual top records
        list_sql = f"""
            SELECT 
                id,
                date,
                voucher_number,
                COALESCE(invoice_no, voucher_number) as invoice_no,
                COALESCE(party, 'Unknown') as customer_name,
                COALESCE(total, 0) as amount,
                COALESCE(total_taxable_amount, 0) as taxable_amount,
                COALESCE(total_cgst + total_sgst + total_igst, 0) as tax_amount
            FROM vouchers
            WHERE {where_sql}
            ORDER BY date DESC, id DESC
            LIMIT {min(limit, 50)}
        """

        with connection.cursor() as cursor:
            cursor.execute(agg_sql, params)
            agg_row = cursor.fetchone()
            
            cursor.execute(list_sql, params)
            cols = [col[0] for col in cursor.description]
            records = [dict(zip(cols, row)) for row in cursor.fetchall()]

        count = agg_row[0] if agg_row else 0
        total_sales = float(agg_row[1]) if agg_row else 0.0
        total_taxable = float(agg_row[2]) if agg_row else 0.0
        total_cgst = float(agg_row[3]) if agg_row else 0.0
        total_sgst = float(agg_row[4]) if agg_row else 0.0
        total_igst = float(agg_row[5]) if agg_row else 0.0
        total_tax = total_cgst + total_sgst + total_igst

        # Format records for table display
        formatted_records = []
        for r in records:
            formatted_records.append({
                "Date": str(r["date"]),
                "Invoice No": r["invoice_no"],
                "Customer": r["customer_name"],
                "Amount": format_inr(r["amount"]),
                "Tax": format_inr(r["tax_amount"])
            })

        period_label = date_range.get("label", "All Time") if date_range else "All Time"

        return {
            "domain": "Sales",
            "count": count,
            "total_sales": total_sales,
            "total_sales_formatted": format_inr(total_sales),
            "total_taxable": total_taxable,
            "total_taxable_formatted": format_inr(total_taxable),
            "total_tax": total_tax,
            "total_tax_formatted": format_inr(total_tax),
            "total_cgst": total_cgst,
            "total_sgst": total_sgst,
            "total_igst": total_igst,
            "period": period_label,
            "records": records,
            "formatted_records": formatted_records
        }

    # ── 2. PURCHASE SUMMARY TOOL ──────────────────────────────────────────────
    def get_purchase_summary(
        self,
        tenant_id: str,
        date_range: Optional[Dict[str, Any]] = None,
        vendor_name: Optional[str] = None,
        limit: int = 15
    ) -> Dict[str, Any]:
        """Queries purchase vouchers and bill totals."""
        params: List[Any] = [tenant_id]
        where_clauses = ["tenant_id = %s", "LOWER(type) = 'purchase'"]

        if date_range:
            where_clauses.append("date >= %s AND date <= %s")
            params.extend([date_range["start_date"], date_range["end_date"]])

        if vendor_name:
            where_clauses.append("LOWER(party) LIKE %s")
            params.append(f"%{vendor_name.lower().strip()}%")

        where_sql = " AND ".join(where_clauses)

        agg_sql = f"""
            SELECT 
                COUNT(*) as bill_count,
                COALESCE(SUM(total), 0) as total_purchases,
                COALESCE(SUM(total_taxable_amount), 0) as total_taxable,
                COALESCE(SUM(total_cgst), 0) as total_cgst,
                COALESCE(SUM(total_sgst), 0) as total_sgst,
                COALESCE(SUM(total_igst), 0) as total_igst
            FROM vouchers
            WHERE {where_sql}
        """

        list_sql = f"""
            SELECT 
                id,
                date,
                voucher_number,
                COALESCE(invoice_no, voucher_number) as bill_no,
                COALESCE(party, 'Unknown') as vendor_name,
                COALESCE(total, 0) as amount,
                COALESCE(total_taxable_amount, 0) as taxable_amount,
                COALESCE(total_cgst + total_sgst + total_igst, 0) as tax_amount
            FROM vouchers
            WHERE {where_sql}
            ORDER BY date DESC, id DESC
            LIMIT {min(limit, 50)}
        """

        with connection.cursor() as cursor:
            cursor.execute(agg_sql, params)
            agg_row = cursor.fetchone()

            cursor.execute(list_sql, params)
            cols = [col[0] for col in cursor.description]
            records = [dict(zip(cols, row)) for row in cursor.fetchall()]

        count = agg_row[0] if agg_row else 0
        total_purchases = float(agg_row[1]) if agg_row else 0.0
        total_taxable = float(agg_row[2]) if agg_row else 0.0
        total_tax = (float(agg_row[3]) if agg_row else 0.0) + (float(agg_row[4]) if agg_row else 0.0) + (float(agg_row[5]) if agg_row else 0.0)

        formatted_records = []
        for r in records:
            formatted_records.append({
                "Date": str(r["date"]),
                "Bill No": r["bill_no"],
                "Supplier": r["vendor_name"],
                "Amount": format_inr(r["amount"]),
                "Tax": format_inr(r["tax_amount"])
            })

        period_label = date_range.get("label", "All Time") if date_range else "All Time"

        return {
            "domain": "Purchase",
            "count": count,
            "total_purchases": total_purchases,
            "total_purchases_formatted": format_inr(total_purchases),
            "total_taxable": total_taxable,
            "total_taxable_formatted": format_inr(total_taxable),
            "total_tax": total_tax,
            "total_tax_formatted": format_inr(total_tax),
            "period": period_label,
            "records": records,
            "formatted_records": formatted_records
        }

    # ── 3. RECEIVABLES & OUTSTANDING DUES TOOL ────────────────────────────────
    def get_receivables_summary(
        self,
        tenant_id: str,
        customer_name: Optional[str] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Calculates total outstanding receivables from customers.
        Uses advance_allocation, pending_transaction, and master_ledgers (Sundry Debtors).
        """
        params: List[Any] = [tenant_id]
        where_cust = ""
        if customer_name:
            where_cust = " AND LOWER(COALESCE(c.customer_name, '')) LIKE %s"
            params.append(f"%{customer_name.lower().strip()}%")

        # Query pending allocations
        sql = f"""
            SELECT 
                a.id,
                COALESCE(a.invoice_date, a.created_at) as invoice_date,
                COALESCE(a.reference_number, a.reference_id, 'INV') as invoice_no,
                COALESCE(c.customer_name, 'Customer') as customer_name,
                COALESCE(a.original_amount, 0) as invoice_amount,
                COALESCE(a.allocated_amount, 0) as paid_amount,
                (COALESCE(a.original_amount, 0) - COALESCE(a.allocated_amount, 0)) as pending_balance,
                a.due_date,
                COALESCE(a.due_status, 'Pending') as status
            FROM advance_allocation a
            LEFT JOIN customer_master_customer_basicdetails c ON a.party_customer_id = c.id
            WHERE a.tenant_id = %s 
              AND (COALESCE(a.original_amount, 0) - COALESCE(a.allocated_amount, 0)) > 0
              {where_cust}
            ORDER BY a.invoice_date DESC
            LIMIT {min(limit, 50)}
        """

        total_sql = f"""
            SELECT 
                COUNT(*) as pending_count,
                COALESCE(SUM(COALESCE(a.original_amount, 0) - COALESCE(a.allocated_amount, 0)), 0) as total_receivable
            FROM advance_allocation a
            LEFT JOIN customer_master_customer_basicdetails c ON a.party_customer_id = c.id
            WHERE a.tenant_id = %s 
              AND (COALESCE(a.original_amount, 0) - COALESCE(a.allocated_amount, 0)) > 0
              {where_cust}
        """

        with connection.cursor() as cursor:
            cursor.execute(total_sql, params)
            tot_row = cursor.fetchone()
            
            cursor.execute(sql, params)
            cols = [col[0] for col in cursor.description]
            records = [dict(zip(cols, row)) for row in cursor.fetchall()]

        count = tot_row[0] if tot_row else 0
        total_receivable = float(tot_row[1]) if tot_row else 0.0

        # Fallback to Sundry Debtors ledger balance if allocation table has no active records
        if total_receivable == 0.0:
            ledger_sql = """
                SELECT 
                    l.id,
                    COALESCE(l.ledger_type, l.ledger, 'Debtor') as customer_name,
                    COALESCE(SUM(e.debit) - SUM(e.credit), 0) + COALESCE(l.opening_balance, 0) as balance
                FROM master_ledgers l
                LEFT JOIN entries e ON e.ledger_id = l.id
                WHERE l.tenant_id = %s AND (LOWER(l.group) LIKE %s OR LOWER(l.category) = 'asset')
                GROUP BY l.id, l.ledger_type, l.ledger, l.opening_balance
                HAVING balance > 0
                LIMIT 20
            """
            with connection.cursor() as cursor:
                cursor.execute(ledger_sql, [tenant_id, "%debtor%"])
                l_cols = [col[0] for col in cursor.description]
                l_records = [dict(zip(l_cols, row)) for row in cursor.fetchall()]
                if l_records:
                    total_receivable = sum(float(r["balance"]) for r in l_records)
                    count = len(l_records)
                    records = [{
                        "id": r["id"],
                        "invoice_date": "-",
                        "invoice_no": "-",
                        "customer_name": r["customer_name"],
                        "invoice_amount": float(r["balance"]),
                        "paid_amount": 0.0,
                        "pending_balance": float(r["balance"]),
                        "due_date": "-",
                        "status": "Outstanding"
                    } for r in l_records]

        formatted_records = []
        for r in records:
            formatted_records.append({
                "Invoice": str(r["invoice_no"]),
                "Customer": str(r["customer_name"]),
                "Invoice Date": str(r["invoice_date"]),
                "Total Amount": format_inr(r["invoice_amount"]),
                "Balance Due": format_inr(r["pending_balance"]),
                "Status": str(r["status"])
            })

        return {
            "domain": "Receivables",
            "count": count,
            "total_receivable": total_receivable,
            "total_receivable_formatted": format_inr(total_receivable),
            "records": records,
            "formatted_records": formatted_records
        }

    # ── 4. PAYABLES & SUPPLIER DUES TOOL ──────────────────────────────────────
    def get_payables_summary(
        self,
        tenant_id: str,
        vendor_name: Optional[str] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Calculates total outstanding payables owed to suppliers/vendors.
        Uses advance_allocation and master_ledgers (Sundry Creditors).
        """
        params: List[Any] = [tenant_id]
        where_ven = ""
        if vendor_name:
            where_ven = " AND LOWER(COALESCE(v.vendor_name, '')) LIKE %s"
            params.append(f"%{vendor_name.lower().strip()}%")

        sql = f"""
            SELECT 
                a.id,
                COALESCE(a.invoice_date, a.created_at) as bill_date,
                COALESCE(a.reference_number, a.reference_id, 'BILL') as bill_no,
                COALESCE(v.vendor_name, 'Supplier') as vendor_name,
                COALESCE(a.original_amount, 0) as bill_amount,
                COALESCE(a.allocated_amount, 0) as paid_amount,
                (COALESCE(a.original_amount, 0) - COALESCE(a.allocated_amount, 0)) as pending_balance,
                a.due_date,
                COALESCE(a.due_status, 'Pending') as status
            FROM advance_allocation a
            LEFT JOIN vendor_master_vendorcreation_basicdetail v ON a.party_vendor_id = v.id
            WHERE a.tenant_id = %s 
              AND (COALESCE(a.original_amount, 0) - COALESCE(a.allocated_amount, 0)) > 0
              {where_ven}
            ORDER BY a.invoice_date DESC
            LIMIT {min(limit, 50)}
        """

        total_sql = f"""
            SELECT 
                COUNT(*) as pending_count,
                COALESCE(SUM(COALESCE(a.original_amount, 0) - COALESCE(a.allocated_amount, 0)), 0) as total_payable
            FROM advance_allocation a
            LEFT JOIN vendor_master_vendorcreation_basicdetail v ON a.party_vendor_id = v.id
            WHERE a.tenant_id = %s 
              AND (COALESCE(a.original_amount, 0) - COALESCE(a.allocated_amount, 0)) > 0
              {where_ven}
        """

        with connection.cursor() as cursor:
            cursor.execute(total_sql, params)
            tot_row = cursor.fetchone()

            cursor.execute(sql, params)
            cols = [col[0] for col in cursor.description]
            records = [dict(zip(cols, row)) for row in cursor.fetchall()]

        count = tot_row[0] if tot_row else 0
        total_payable = float(tot_row[1]) if tot_row else 0.0

        # Fallback to Sundry Creditors ledger balance if needed
        if total_payable == 0.0:
            ledger_sql = """
                SELECT 
                    l.id,
                    COALESCE(l.ledger_type, l.ledger, 'Supplier') as vendor_name,
                    COALESCE(SUM(e.credit) - SUM(e.debit), 0) + COALESCE(l.opening_balance, 0) as balance
                FROM master_ledgers l
                LEFT JOIN entries e ON e.ledger_id = l.id
                WHERE l.tenant_id = %s AND (LOWER(l.group) LIKE %s OR LOWER(l.category) = 'liability')
                GROUP BY l.id, l.ledger_type, l.ledger, l.opening_balance
                HAVING balance > 0
                LIMIT 20
            """
            with connection.cursor() as cursor:
                cursor.execute(ledger_sql, [tenant_id, "%creditor%"])
                l_cols = [col[0] for col in cursor.description]
                l_records = [dict(zip(l_cols, row)) for row in cursor.fetchall()]
                if l_records:
                    total_payable = sum(float(r["balance"]) for r in l_records)
                    count = len(l_records)
                    records = [{
                        "id": r["id"],
                        "bill_date": "-",
                        "bill_no": "-",
                        "vendor_name": r["vendor_name"],
                        "bill_amount": float(r["balance"]),
                        "paid_amount": 0.0,
                        "pending_balance": float(r["balance"]),
                        "due_date": "-",
                        "status": "Outstanding"
                    } for r in l_records]


        formatted_records = []
        for r in records:
            formatted_records.append({
                "Bill No": str(r["bill_no"]),
                "Supplier": str(r["vendor_name"]),
                "Bill Date": str(r["bill_date"]),
                "Total Amount": format_inr(r["bill_amount"]),
                "Balance Due": format_inr(r["pending_balance"]),
                "Status": str(r["status"])
            })

        return {
            "domain": "Payables",
            "count": count,
            "total_payable": total_payable,
            "total_payable_formatted": format_inr(total_payable),
            "records": records,
            "formatted_records": formatted_records
        }

    # ── 5. INVENTORY & STOCK SUMMARY TOOL ─────────────────────────────────────
    def get_inventory_summary(
        self,
        tenant_id: str,
        item_name: Optional[str] = None,
        low_stock_only: bool = False,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Queries inventory item catalog, live stock balances from inventory_stock_items,
        valuation rates, and low-stock reorder levels.
        """
        # 1. Fetch live stock items (primary source for quantity & valuation)
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    id,
                    TRIM(item_code) as item_code,
                    name,
                    COALESCE(`group`, 'General') as item_group,
                    COALESCE(unit, 'nos') as unit,
                    COALESCE(current_balance, 0) as current_balance,
                    COALESCE(rate, 0) as rate,
                    COALESCE(is_active, 1) as is_active
                FROM inventory_stock_items
                WHERE tenant_id = %s
            """, [tenant_id])
            s_cols = [col[0] for col in cursor.description]
            stock_rows = [dict(zip(s_cols, row)) for row in cursor.fetchall()]

            # 2. Fetch catalog items (source for categories, reorder levels, tax rates)
            cursor.execute("""
                SELECT 
                    id,
                    TRIM(item_code) as item_code,
                    item_name,
                    COALESCE(category_path, 'General') as category,
                    COALESCE(uom, 'nos') as uom,
                    COALESCE(rate, 0) as rate,
                    COALESCE(opening_stock, 0) as opening_stock,
                    COALESCE(reorder_level, 0) as reorder_level,
                    COALESCE(hsn_code, '') as hsn_code,
                    COALESCE(gst_rate, 0) as gst_rate,
                    COALESCE(is_active, 1) as is_active
                FROM inventory_master_inventoryitems
                WHERE tenant_id = %s AND is_active = 1
            """, [tenant_id])
            c_cols = [col[0] for col in cursor.description]
            catalog_rows = [dict(zip(c_cols, row)) for row in cursor.fetchall()]

        # Index live stock by normalized item_code
        stock_map: Dict[str, Dict[str, Any]] = {}
        for s in stock_rows:
            code_key = str(s["item_code"] or "").strip().lower()
            if code_key:
                stock_map[code_key] = s

        # Build unified inventory records
        merged_items: Dict[str, Dict[str, Any]] = {}

        # First populate from catalog
        for c in catalog_rows:
            code_key = str(c["item_code"] or "").strip().lower()
            s_match = stock_map.get(code_key)

            if s_match:
                current_qty = float(s_match["current_balance"] or 0.0)
                rate = float(s_match["rate"] or c["rate"] or 0.0)
                uom = s_match["unit"] or c["uom"] or "nos"
                name = c["item_name"] or s_match["name"] or code_key
            else:
                current_qty = float(c["opening_stock"] or 0.0)
                rate = float(c["rate"] or 0.0)
                uom = c["uom"] or "nos"
                name = c["item_name"] or code_key

            reorder = float(c["reorder_level"] or 0.0)
            valuation = current_qty * rate

            merged_items[code_key] = {
                "id": c["id"],
                "item_code": c["item_code"],
                "item_name": name,
                "category": c["category"],
                "uom": uom,
                "rate": rate,
                "current_stock": current_qty,
                "reorder_level": reorder,
                "valuation": valuation,
                "hsn_code": c["hsn_code"],
                "is_low": (current_qty <= reorder and reorder > 0)
            }

        # Include any stock items in inventory_stock_items not in catalog
        for code_key, s in stock_map.items():
            if code_key not in merged_items:
                current_qty = float(s["current_balance"] or 0.0)
                rate = float(s["rate"] or 0.0)
                valuation = current_qty * rate
                merged_items[code_key] = {
                    "id": s["id"],
                    "item_code": s["item_code"],
                    "item_name": s["name"] or s["item_code"],
                    "category": s["item_group"],
                    "uom": s["unit"] or "nos",
                    "rate": rate,
                    "current_stock": current_qty,
                    "reorder_level": 0.0,
                    "valuation": valuation,
                    "hsn_code": "",
                    "is_low": False
                }

        all_records = list(merged_items.values())

        # Calculate tenant-level aggregates
        total_items = len(all_records)
        total_quantity = sum(r["current_stock"] for r in all_records)
        total_valuation = sum(r["valuation"] for r in all_records)
        low_stock_count = sum(1 for r in all_records if r["is_low"])

        # Apply search and filtering
        filtered_records = all_records
        if item_name:
            query_str = item_name.lower().strip()
            filtered_records = [
                r for r in filtered_records
                if query_str in str(r["item_name"]).lower() or query_str in str(r["item_code"]).lower()
            ]

        if low_stock_only:
            filtered_records = [r for r in filtered_records if r["is_low"]]

        # Sort: low stock items first, then by item_name
        filtered_records.sort(key=lambda x: (not x["is_low"], x["item_name"].lower()))
        paged_records = filtered_records[:min(limit, 50)]

        formatted_records = []
        for r in paged_records:
            status_str = "⚠️ Low Stock" if r["is_low"] else "In Stock"
            formatted_records.append({
                "Item Code": r["item_code"],
                "Item Name": r["item_name"],
                "Category": r["category"],
                "Rate": format_inr(r["rate"]),
                "Stock": f"{r['current_stock']:g} {r['uom']}",
                "Reorder Level": f"{r['reorder_level']:g}",
                "Status": status_str
            })

        return {
            "domain": "Inventory",
            "total_items": total_items,
            "total_quantity": total_quantity,
            "total_valuation": total_valuation,
            "total_valuation_formatted": format_inr(total_valuation),
            "low_stock_count": low_stock_count,
            "low_stock_only": low_stock_only,
            "records": paged_records,
            "formatted_records": formatted_records
        }

    # ── 6. CUSTOMER DIRECTORY TOOL ────────────────────────────────────────────
    def get_customers_summary(
        self,
        tenant_id: str,
        customer_name: Optional[str] = None,
        limit: int = 15
    ) -> Dict[str, Any]:
        """Queries customer master directory and total billing."""
        params: List[Any] = [tenant_id]
        where_clauses = ["c.tenant_id = %s", "c.is_deleted = 0"]

        if customer_name:
            where_clauses.append("(LOWER(c.customer_name) LIKE %s OR LOWER(c.customer_code) LIKE %s)")
            params.extend([f"%{customer_name.lower().strip()}%", f"%{customer_name.lower().strip()}%"])

        where_sql = " AND ".join(where_clauses)

        sql = f"""
            SELECT 
                c.id,
                c.customer_code,
                c.customer_name,
                COALESCE(c.pan_number, '') as pan_number,
                COALESCE(c.contact_number, '') as phone,
                COALESCE(c.email_address, '') as email,
                COALESCE(c.billing_currency, 'INR') as currency
            FROM customer_master_customer_basicdetails c
            WHERE {where_sql}
            ORDER BY c.customer_name ASC
            LIMIT {min(limit, 50)}
        """

        # Fetch sales totals per party
        sales_by_party: Dict[str, float] = {}
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT LOWER(TRIM(party)), COALESCE(SUM(total), 0)
                FROM vouchers
                WHERE tenant_id = %s AND LOWER(type) = 'sales' AND party IS NOT NULL AND party != ''
                GROUP BY LOWER(TRIM(party))
            """, [tenant_id])
            for p_row in cursor.fetchall():
                if p_row[0]:
                    sales_by_party[p_row[0]] = float(p_row[1])

            cursor.execute(sql, params)
            cols = [col[0] for col in cursor.description]
            records = [dict(zip(cols, row)) for row in cursor.fetchall()]

        formatted_records = []
        for r in records:
            c_name = r["customer_name"].lower().strip()
            # Match directly or by substring
            tot_sales = sales_by_party.get(c_name, 0.0)
            if tot_sales == 0.0:
                for p_key, p_val in sales_by_party.items():
                    if c_name in p_key or p_key in c_name:
                        tot_sales += p_val
            r["total_purchased"] = tot_sales

            formatted_records.append({
                "Customer Code": r["customer_code"],
                "Customer Name": r["customer_name"],
                "Phone": r["phone"] or "-",
                "PAN": r["pan_number"] or "-",
                "Total Sales": format_inr(tot_sales)
            })

        # Sort by total_purchased descending
        records.sort(key=lambda x: x.get("total_purchased", 0.0), reverse=True)
        formatted_records.sort(key=lambda x: float(str(x.get("Total Sales", "0")).replace("₹", "").replace(",", "") or 0.0), reverse=True)

        return {
            "domain": "Customers",
            "count": len(records),
            "records": records,
            "formatted_records": formatted_records
        }

    # ── 7. SUPPLIER DIRECTORY TOOL ────────────────────────────────────
    def get_suppliers_summary(
        self,
        tenant_id: str,
        vendor_name: Optional[str] = None,
        limit: int = 15
    ) -> Dict[str, Any]:
        """Queries vendor/supplier master directory and procurement totals."""
        params: List[Any] = [tenant_id]
        where_clauses = ["v.tenant_id = %s", "v.is_deleted = 0"]

        if vendor_name:
            where_clauses.append("(LOWER(v.vendor_name) LIKE %s OR LOWER(v.vendor_code) LIKE %s)")
            params.extend([f"%{vendor_name.lower().strip()}%", f"%{vendor_name.lower().strip()}%"])

        where_sql = " AND ".join(where_clauses)

        sql = f"""
            SELECT 
                v.id,
                v.vendor_code,
                v.vendor_name,
                COALESCE(v.vendor_category, 'General') as category,
                COALESCE(v.pan_no, '') as pan_no,
                COALESCE(v.contact_no, '') as phone,
                COALESCE(v.email, '') as email
            FROM vendor_master_vendorcreation_basicdetail v
            WHERE {where_sql}
            ORDER BY v.vendor_name ASC
            LIMIT {min(limit, 50)}
        """

        # Fetch purchase totals per party
        purch_by_party: Dict[str, float] = {}
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT LOWER(TRIM(party)), COALESCE(SUM(total), 0)
                FROM vouchers
                WHERE tenant_id = %s AND LOWER(type) = 'purchase' AND party IS NOT NULL AND party != ''
                GROUP BY LOWER(TRIM(party))
            """, [tenant_id])
            for p_row in cursor.fetchall():
                if p_row[0]:
                    purch_by_party[p_row[0]] = float(p_row[1])

            cursor.execute(sql, params)
            cols = [col[0] for col in cursor.description]
            records = [dict(zip(cols, row)) for row in cursor.fetchall()]

        formatted_records = []
        for r in records:
            v_name = r["vendor_name"].lower().strip()
            tot_purch = purch_by_party.get(v_name, 0.0)
            if tot_purch == 0.0:
                for p_key, p_val in purch_by_party.items():
                    if v_name in p_key or p_key in v_name:
                        tot_purch += p_val
            r["total_procured"] = tot_purch

            formatted_records.append({
                "Vendor Code": r["vendor_code"],
                "Supplier Name": r["vendor_name"],
                "Category": r["category"],
                "Phone": r["phone"] or "-",
                "Total Purchases": format_inr(tot_purch)
            })

        records.sort(key=lambda x: x.get("total_procured", 0.0), reverse=True)
        formatted_records.sort(key=lambda x: float(str(x.get("Total Purchases", "0")).replace("₹", "").replace(",", "") or 0.0), reverse=True)

        return {
            "domain": "Suppliers",
            "count": len(records),
            "records": records,
            "formatted_records": formatted_records
        }


    # ── 8. GST SUMMARY TOOL ───────────────────────────────────────────────────
    def get_gst_summary(
        self,
        tenant_id: str,
        date_range: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Calculates Output GST, Input Tax Credit (ITC), and Net GST Liability."""
        params: List[Any] = [tenant_id]
        date_where = ""
        if date_range:
            date_where = " AND date >= %s AND date <= %s"
            params.extend([date_range["start_date"], date_range["end_date"]])

        # 1. Output GST from Sales Vouchers
        sales_sql = f"""
            SELECT 
                COALESCE(SUM(total_taxable_amount), 0) as taxable_sales,
                COALESCE(SUM(total_cgst), 0) as output_cgst,
                COALESCE(SUM(total_sgst), 0) as output_sgst,
                COALESCE(SUM(total_igst), 0) as output_igst
            FROM vouchers
            WHERE tenant_id = %s AND LOWER(type) = 'sales' {date_where}
        """

        # 2. Input GST from Purchase Vouchers
        purch_sql = f"""
            SELECT 
                COALESCE(SUM(total_taxable_amount), 0) as taxable_purchases,
                COALESCE(SUM(total_cgst), 0) as input_cgst,
                COALESCE(SUM(total_sgst), 0) as input_sgst,
                COALESCE(SUM(total_igst), 0) as input_igst
            FROM vouchers
            WHERE tenant_id = %s AND LOWER(type) = 'purchase' {date_where}
        """

        with connection.cursor() as cursor:
            cursor.execute(sales_sql, params)
            s_row = cursor.fetchone()

            cursor.execute(purch_sql, params)
            p_row = cursor.fetchone()

        output_cgst = float(s_row[1]) if s_row else 0.0
        output_sgst = float(s_row[2]) if s_row else 0.0
        output_igst = float(s_row[3]) if s_row else 0.0
        total_output_gst = output_cgst + output_sgst + output_igst

        input_cgst = float(p_row[1]) if p_row else 0.0
        input_sgst = float(p_row[2]) if p_row else 0.0
        input_igst = float(p_row[3]) if p_row else 0.0
        total_input_gst = input_cgst + input_sgst + input_igst

        net_cgst = output_cgst - input_cgst
        net_sgst = output_sgst - input_sgst
        net_igst = output_igst - input_igst
        net_liability = total_output_gst - total_input_gst

        period_label = date_range.get("label", "All Time") if date_range else "All Time"

        formatted_records = [
            {"Tax Component": "CGST", "Output GST (Sales)": format_inr(output_cgst), "Input GST (Purchase)": format_inr(input_cgst), "Net Payable": format_inr(net_cgst)},
            {"Tax Component": "SGST", "Output GST (Sales)": format_inr(output_sgst), "Input GST (Purchase)": format_inr(input_sgst), "Net Payable": format_inr(net_sgst)},
            {"Tax Component": "IGST", "Output GST (Sales)": format_inr(output_igst), "Input GST (Purchase)": format_inr(input_igst), "Net Payable": format_inr(net_igst)},
            {"Tax Component": "TOTAL GST", "Output GST (Sales)": format_inr(total_output_gst), "Input GST (Purchase)": format_inr(total_input_gst), "Net Payable": format_inr(net_liability)},
        ]

        return {
            "domain": "GST",
            "period": period_label,
            "total_output_gst": total_output_gst,
            "total_output_gst_formatted": format_inr(total_output_gst),
            "total_input_gst": total_input_gst,
            "total_input_gst_formatted": format_inr(total_input_gst),
            "net_liability": net_liability,
            "net_liability_formatted": format_inr(net_liability),
            "output_cgst": output_cgst,
            "output_sgst": output_sgst,
            "output_igst": output_igst,
            "input_cgst": input_cgst,
            "input_sgst": input_sgst,
            "input_igst": input_igst,
            "formatted_records": formatted_records
        }

    # ── 9. CASH & BANK & LEDGER BALANCE TOOL ──────────────────────────────────
    def get_ledger_balances(
        self,
        tenant_id: str,
        group_filter: Optional[str] = None,
        ledger_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Calculates closing ledger balances for Bank Accounts, Cash, and General Ledgers."""
        params: List[Any] = [tenant_id]
        where_clauses = ["l.tenant_id = %s"]

        if group_filter:
            if "bank" in group_filter.lower():
                where_clauses.append("(LOWER(l.group) LIKE %s OR LOWER(l.ledger_type) LIKE %s OR LOWER(l.category) LIKE %s)")
                params.extend(["%bank%", "%bank%", "%bank%"])
            elif "cash" in group_filter.lower():
                where_clauses.append("(LOWER(l.group) LIKE %s OR LOWER(l.ledger_type) LIKE %s OR LOWER(l.category) LIKE %s)")
                params.extend(["%cash%", "%cash%", "%cash%"])
            else:
                where_clauses.append("(LOWER(l.group) LIKE %s OR LOWER(l.category) LIKE %s)")
                params.extend([f"%{group_filter.lower().strip()}%", f"%{group_filter.lower().strip()}%"])

        if ledger_name:
            where_clauses.append("(LOWER(l.ledger_type) LIKE %s OR LOWER(l.ledger) LIKE %s)")
            params.extend([f"%{ledger_name.lower().strip()}%", f"%{ledger_name.lower().strip()}%"])

        where_sql = " AND ".join(where_clauses)

        sql = f"""
            SELECT 
                l.id,
                COALESCE(l.ledger_type, l.ledger, 'Account') as name,
                COALESCE(l.group, 'General') as ledger_group,
                COALESCE(l.category, 'Asset') as category,
                COALESCE(l.opening_balance, 0) as opening_balance,
                COALESCE(l.opening_balance_type, 'Dr') as opening_balance_type,
                COALESCE(SUM(e.debit), 0) as total_debit,
                COALESCE(SUM(e.credit), 0) as total_credit
            FROM master_ledgers l
            LEFT JOIN entries e ON e.ledger_id = l.id
            WHERE {where_sql}
            GROUP BY l.id, l.ledger_type, l.ledger, l.group, l.category, l.opening_balance, l.opening_balance_type
            ORDER BY l.group ASC, name ASC
            LIMIT 30
        """

        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            cols = [col[0] for col in cursor.description]
            records = [dict(zip(cols, row)) for row in cursor.fetchall()]

        total_balance = 0.0
        formatted_records = []

        for r in records:
            ob = float(r["opening_balance"])
            is_dr = str(r["opening_balance_type"]).lower() in ["dr", "debit"]
            dr = float(r["total_debit"])
            cr = float(r["total_credit"])
            cat_lower = str(r["category"]).lower()
            grp_lower = str(r["ledger_group"]).lower()
            is_debit_normal = any(k in cat_lower for k in ["asset", "cash", "bank", "expense", "expenditure", "debtor"]) or any(k in grp_lower for k in ["asset", "cash", "bank", "debtor"])

            if is_debit_normal:
                bal = (ob if is_dr else -ob) + dr - cr
            else:
                bal = (ob if not is_dr else -ob) + cr - dr

            total_balance += bal
            formatted_records.append({
                "Ledger Name": r["name"],
                "Group": r["ledger_group"],
                "Category": r["category"],
                "Total Debit": format_inr(dr),
                "Total Credit": format_inr(cr),
                "Closing Balance": format_inr(bal)
            })

        return {
            "domain": "Finance",
            "count": len(records),
            "total_balance": total_balance,
            "total_balance_formatted": format_inr(total_balance),
            "records": records,
            "formatted_records": formatted_records
        }

    # ── 10. PROFIT & LOSS OVERVIEW TOOL ───────────────────────────────────────
    def get_profit_loss_summary(
        self,
        tenant_id: str,
        date_range: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Calculates authoritative Financial Statements Profit & Loss by reusing
        the ERP's accounting flow layer (reports.flow.generate_profit_and_loss_data).
        Includes Income Accounts, Cost of Goods Sold with Closing Stock adjustment,
        Operating Expenses, and Net Profit / Net Loss.
        """
        start_date = date_range.get("start_date") if date_range else None
        end_date = date_range.get("end_date") if date_range else None
        period_label = date_range.get("label", "All Time") if date_range else "All Time"

        # Create lightweight authenticated context object for reports.flow
        class UserTenantProxy:
            def __init__(self, tid):
                self.tenant_id = str(tid)
                self.company_id = str(tid)
                self.is_authenticated = True
                self.id = "kiki_agent"

        user_proxy = UserTenantProxy(tenant_id)

        try:
            from reports.flow import generate_profit_and_loss_data
            pnl_data = generate_profit_and_loss_data(user_proxy, start_date=start_date, end_date=end_date)

            total_income = float(pnl_data.get("total_income", 0.0) or 0.0)
            total_expenses = float(pnl_data.get("total_expenses", 0.0) or 0.0)
            net_profit = float(pnl_data.get("net_profit", 0.0) or 0.0)

            # Extract granular accounting line items
            non_corp = pnl_data.get("non_corporate", {})
            rev_ops = float(non_corp.get("revenue_from_operations", {}).get("total", 0.0) or total_income)
            other_inc = float(non_corp.get("other_income", {}).get("total", 0.0) or 0.0)
            expenses_dict = non_corp.get("expenses", {})
            cogs = float(expenses_dict.get("cost_of_goods_sold", {}).get("total", 0.0) or 0.0)
            emp_exp = float(expenses_dict.get("employee_benefits_expense", {}).get("total", 0.0) or 0.0)
            fin_cost = float(expenses_dict.get("finance_costs", {}).get("total", 0.0) or 0.0)
            depr_exp = float(expenses_dict.get("depreciation_amortization", {}).get("total", 0.0) or 0.0)
            other_exp = float(expenses_dict.get("other_expenses", {}).get("total", 0.0) or 0.0)

        except Exception as e:
            logger.warning(f"[BUSINESS TOOLS] ERP P&L generation fallback due to: {e}")
            sales_data = self.get_sales_summary(tenant_id, date_range=date_range)
            purchase_data = self.get_purchase_summary(tenant_id, date_range=date_range)
            total_income = sales_data["total_sales"]
            cogs = purchase_data["total_purchases"]
            rev_ops = total_income
            other_inc = 0.0
            emp_exp = fin_cost = depr_exp = other_exp = 0.0
            total_expenses = cogs
            net_profit = total_income - total_expenses

        is_profit = net_profit >= 0

        formatted_records = [
            {"Accounting Metric": "Revenue from Operations", "Amount": format_inr(rev_ops)},
            {"Accounting Metric": "Other Income", "Amount": format_inr(other_inc)},
            {"Accounting Metric": "Total Income (A)", "Amount": format_inr(total_income)},
            {"Accounting Metric": "Cost of Goods Sold (incl. Closing Stock)", "Amount": format_inr(cogs)},
            {"Accounting Metric": "Operating & Other Expenses", "Amount": format_inr(emp_exp + other_exp + fin_cost + depr_exp)},
            {"Accounting Metric": "Total Expenses (B)", "Amount": format_inr(total_expenses)},
            {"Accounting Metric": "NET PROFIT (A - B)" if is_profit else "NET LOSS (A - B)", "Amount": format_inr(net_profit)}
        ]

        return {
            "domain": "Finance",
            "period": period_label,
            "total_income": total_income,
            "total_income_formatted": format_inr(total_income),
            "total_sales": rev_ops,
            "total_sales_formatted": format_inr(rev_ops),
            "total_purchases": cogs,
            "total_purchases_formatted": format_inr(cogs),
            "cost_of_goods_sold": cogs,
            "cost_of_goods_sold_formatted": format_inr(cogs),
            "other_expenses": total_expenses - cogs,
            "other_expenses_formatted": format_inr(total_expenses - cogs),
            "total_expenses": total_expenses,
            "total_expenses_formatted": format_inr(total_expenses),
            "net_profit": net_profit,
            "net_profit_formatted": format_inr(net_profit),
            "is_profit": is_profit,
            "formatted_records": formatted_records
        }


business_tools = BusinessToolsEngine()
