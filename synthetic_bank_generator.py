import os
import random
import datetime

# --- PROCEDURAL DATA GENERATOR ---

MERCHANTS = [
    "AMAZON IN", "UPI/Zomato", "NACH-HDFC ERGO", "POS/STARBUCKS", 
    "ATM WITHDRAWAL", "NEFT-SALARY", "IMPS/John Doe", "NETFLIX", 
    "UBER RIDES", "UPI/Swiggy", "CASH DEPOSIT", "CHEQUE CLEARING"
]

def generate_transactions(num_txns=15):
    transactions = []
    balance = random.uniform(20000, 250000)
    current_date = datetime.date.today() - datetime.timedelta(days=30)
    
    total_debits = 0
    total_credits = 0
    
    for i in range(num_txns):
        txn_date = current_date + datetime.timedelta(days=random.randint(1, 2))
        current_date = txn_date
        
        desc = random.choice(MERCHANTS)
        
        is_credit = "SALARY" in desc or "DEPOSIT" in desc or random.random() > 0.7
        
        if is_credit:
            amt = round(random.uniform(1000, 50000), 2)
            balance += amt
            total_credits += amt
            transactions.append({
                "date": txn_date.strftime("%d %b %Y"),
                "val_date": (txn_date + datetime.timedelta(days=1)).strftime("%d %b %Y"),
                "desc": desc,
                "ref_no": f"REF{random.randint(10000000, 99999999)}",
                "type": "CR",
                "debit": 0,
                "credit": amt,
                "amount": amt,
                "balance": balance
            })
        else:
            amt = round(random.uniform(100, 10000), 2)
            balance -= amt
            total_debits += amt
            transactions.append({
                "date": txn_date.strftime("%d %b %Y"),
                "val_date": (txn_date + datetime.timedelta(days=1)).strftime("%d %b %Y"),
                "desc": desc,
                "ref_no": f"TXN{random.randint(10000000, 99999999)}",
                "type": "DR",
                "debit": amt,
                "credit": 0,
                "amount": -amt,
                "balance": balance
            })
            
    return transactions, total_debits, total_credits, balance


# --- VISUAL THEMES ---
THEMES = [
    {"font": "Arial, sans-serif", "primary": "#004d99", "bg": "#ffffff", "th_bg": "#f0f8ff", "text": "#333", "border": "1px solid #ddd", "name": "Corporate Blue"},
    {"font": "Georgia, serif", "primary": "#800000", "bg": "#fdfdfd", "th_bg": "#e6e6e6", "text": "#000", "border": "2px solid #800000", "name": "Classic Maroon"},
    {"font": "Verdana, sans-serif", "primary": "#008000", "bg": "#ffffff", "th_bg": "#e6ffe6", "text": "#222", "border": "1px dashed #ccc", "name": "Retail Green"},
    {"font": "'Courier New', monospace", "primary": "#000000", "bg": "#ffffff", "th_bg": "#000000", "th_color": "#ffffff", "text": "#000", "border": "1px solid #000", "name": "Terminal Mono"},
    {"font": "Tahoma, sans-serif", "primary": "#e62e00", "bg": "#fffaf0", "th_bg": "#ffcccc", "text": "#444", "border": "1px solid #e62e00", "name": "Modern Red"}
]

# --- COMBINATORIAL HTML ENGINE ---

def build_header(header_style, bank_name, total_debits, total_credits, opening_bal, closing_bal, theme):
    primary = theme['primary']
    if header_style == "split":
        return f"""
        <div style="display: flex; justify-content: space-between; border-bottom: 3px solid {primary}; padding-bottom: 20px; margin-bottom: 20px;">
            <div>
                <h2 style="color: {primary}; margin: 0; font-size: 28px;">{bank_name}</h2>
                <p style="margin: 5px 0;">123 Banking Street, Financial District</p>
            </div>
            <div style="text-align: right;">
                <h3 style="margin: 0; color: #555;">Account Statement</h3>
                <p style="margin: 5px 0;"><b>Name:</b> JOHN CITIZEN<br><b>A/C No:</b> 4445935743<br><b>Date:</b> {datetime.date.today().strftime('%d %b %Y')}</p>
            </div>
        </div>
        """
    elif header_style == "summary_box":
        return f"""
        <div style="text-align: center; margin-bottom: 20px;">
            <h1 style="color: {primary};">{bank_name}</h1>
            <h3 style="color: #666;">STATEMENT OF ACCOUNT</h3>
        </div>
        <div style="border: {theme['border']}; padding: 15px; margin-bottom: 30px; display: flex; justify-content: space-around; background-color: {theme['th_bg']};">
            <div style="text-align: center;"><b>Opening Balance:</b><br>{opening_bal:,.2f}</div>
            <div style="text-align: center; color: #cc0000;"><b>Total Debits:</b><br>{total_debits:,.2f}</div>
            <div style="text-align: center; color: #008000;"><b>Total Credits:</b><br>{total_credits:,.2f}</div>
            <div style="text-align: center;"><b>Closing Balance:</b><br>{closing_bal:,.2f}</div>
        </div>
        """
    else: # Basic
        return f"""
        <div style="margin-bottom: 30px; background-color: {primary}; color: white; padding: 20px; border-radius: 5px;">
            <h1 style="margin: 0;">{bank_name}</h1>
            <h2 style="margin: 5px 0;">Account Statement</h2>
            <p style="margin: 0;">Customer: JOHN CITIZEN | Account: 4445935743</p>
        </div>
        """

def build_unified_table(txns, column_layout, theme):
    th_color = theme.get('th_color', '#000')
    html = f"<table style='width: 100%; border-collapse: collapse; font-size: 12px; border: {theme['border']};'>"
    html += f"<tr style='background-color: {theme['th_bg']}; color: {th_color}; text-align: left;'>"
    
    if column_layout == "expanded":
        html += f"<th style='padding:10px; border:{theme['border']};'>Date</th>"
        html += f"<th style='padding:10px; border:{theme['border']};'>Ref No</th>"
        html += f"<th style='padding:10px; border:{theme['border']};'>Particulars</th>"
        html += f"<th style='padding:10px; border:{theme['border']};'>Debit</th>"
        html += f"<th style='padding:10px; border:{theme['border']};'>Credit</th>"
        html += f"<th style='padding:10px; border:{theme['border']};'>Balance</th>"
        html += "</tr>"
        for t in txns:
            debit_str = f"{t['debit']:,.2f}" if t['debit'] > 0 else ""
            credit_str = f"{t['credit']:,.2f}" if t['credit'] > 0 else ""
            html += f"<tr>"
            html += f"<td style='padding:10px; border-bottom:1px solid #eee;'>{t['date']}</td>"
            html += f"<td style='padding:10px; border-bottom:1px solid #eee;'>{t['ref_no']}</td>"
            html += f"<td style='padding:10px; border-bottom:1px solid #eee;'>{t['desc']}</td>"
            html += f"<td style='padding:10px; border-bottom:1px solid #eee;'>{debit_str}</td>"
            html += f"<td style='padding:10px; border-bottom:1px solid #eee;'>{credit_str}</td>"
            html += f"<td style='padding:10px; border-bottom:1px solid #eee;'><b>{t['balance']:,.2f}</b></td>"
            html += "</tr>"
            
    elif column_layout == "consolidated":
        html += f"<th style='padding:12px; border-bottom:{theme['border']};'>Transaction Date</th>"
        html += f"<th style='padding:12px; border-bottom:{theme['border']};'>Description</th>"
        html += f"<th style='padding:12px; border-bottom:{theme['border']};'>Amount</th>"
        html += f"<th style='padding:12px; border-bottom:{theme['border']};'>Balance</th>"
        html += "</tr>"
        for t in txns:
            amt_str = f"+{t['credit']:,.2f}" if t['credit'] > 0 else f"-{t['debit']:,.2f}"
            color = "#008000" if t['credit'] > 0 else "#cc0000"
            html += f"<tr>"
            html += f"<td style='padding:10px; border-bottom:1px solid #eee;'>{t['date']}</td>"
            html += f"<td style='padding:10px; border-bottom:1px solid #eee;'>{t['desc']}</td>"
            html += f"<td style='padding:10px; border-bottom:1px solid #eee; color: {color};'>{amt_str}</td>"
            html += f"<td style='padding:10px; border-bottom:1px solid #eee;'><b>{t['balance']:,.2f}</b></td>"
            html += "</tr>"
            
    html += "</table>"
    return html

def build_split_tables(txns, theme):
    debits = [t for t in txns if t['type'] == 'DR']
    credits = [t for t in txns if t['type'] == 'CR']
    th_color = theme.get('th_color', '#000')
    
    html = "<div style='display: flex; gap: 30px; font-size: 11px;'>"
    
    # Debits Table
    html += "<div style='flex: 1;'>"
    html += f"<h3 style='color: {theme['primary']}; border-bottom: 2px solid {theme['primary']}; padding-bottom: 5px;'>Withdrawals (Debits)</h3>"
    html += f"<table style='width: 100%; border-collapse: collapse; border: {theme['border']};'>"
    html += f"<tr style='background-color: {theme['th_bg']}; color: {th_color};'><th style='padding:8px; text-align: left;'>Date</th><th style='padding:8px; text-align: left;'>Particulars</th><th style='padding:8px; text-align: right;'>Amount</th></tr>"
    for t in debits:
        html += f"<tr><td style='padding:8px; border-bottom:1px solid #ddd;'>{t['date']}</td><td style='padding:8px; border-bottom:1px solid #ddd;'>{t['desc']}</td><td style='padding:8px; border-bottom:1px solid #ddd; text-align: right; color: #cc0000;'>{t['debit']:,.2f}</td></tr>"
    html += "</table></div>"
    
    # Credits Table
    html += "<div style='flex: 1;'>"
    html += f"<h3 style='color: {theme['primary']}; border-bottom: 2px solid {theme['primary']}; padding-bottom: 5px;'>Deposits (Credits)</h3>"
    html += f"<table style='width: 100%; border-collapse: collapse; border: {theme['border']};'>"
    html += f"<tr style='background-color: {theme['th_bg']}; color: {th_color};'><th style='padding:8px; text-align: left;'>Date</th><th style='padding:8px; text-align: left;'>Particulars</th><th style='padding:8px; text-align: right;'>Amount</th></tr>"
    for t in credits:
        html += f"<tr><td style='padding:8px; border-bottom:1px solid #ddd;'>{t['date']}</td><td style='padding:8px; border-bottom:1px solid #ddd;'>{t['desc']}</td><td style='padding:8px; border-bottom:1px solid #ddd; text-align: right; color: #008000;'>{t['credit']:,.2f}</td></tr>"
    html += "</table></div>"
    
    html += "</div>"
    return html

def build_multiline_blocks(txns, theme):
    html = f"<div style='max-width: 800px; margin: 0 auto;'>"
    for t in txns:
        amt_str = f"+ {t['credit']:,.2f}" if t['credit'] > 0 else f"- {t['debit']:,.2f}"
        color = "#008000" if t['credit'] > 0 else "#cc0000"
        html += f"""
        <div style="border: {theme['border']}; padding: 15px; margin-bottom: 10px; background-color: {theme['bg']}; border-radius: 5px; box-shadow: 1px 1px 3px rgba(0,0,0,0.1);">
            <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                <span style="font-size: 14px;"><b>{t['date']}</b> | Ref: {t['ref_no']}</span>
                <span style="font-size: 16px; font-weight: bold; color: {color};">{amt_str}</span>
            </div>
            <div style="display: flex; justify-content: space-between; color: #555;">
                <span>{t['desc']}</span>
                <span style="background-color: {theme['th_bg']}; padding: 3px 8px; border-radius: 3px; font-weight: bold;">Bal: {t['balance']:,.2f}</span>
            </div>
        </div>
        """
    html += "</div>"
    return html

def generate_procedural_statement(idx):
    bank_names = ["Global Trust Bank", "First National Bank", "Apex Financial", "Metro Union Bank", "Pinnacle Bank"]
    bank_name = random.choice(bank_names)
    
    txns, tot_dr, tot_cr, final_bal = generate_transactions(15)
    opening_bal = final_bal + tot_dr - tot_cr
    
    # 1. Randomly select structural components and Visual Theme
    theme = random.choice(THEMES)
    header_style = random.choice(["split", "summary_box", "basic"])
    table_architecture = random.choice(["unified", "split", "multiline"])
    
    html = f"""
    <html>
    <head>
        <title>Statement {idx}</title>
    </head>
    <body style="margin: 40px; font-family: {theme['font']}; background-color: #f4f6f9; color: {theme['text']};">
        <div style="background-color: {theme['bg']}; padding: 40px; border: 1px solid #ccc; box-shadow: 0px 0px 10px rgba(0,0,0,0.05); max-width: 1000px; margin: 0 auto;">
    """
    
    html += build_header(header_style, bank_name, tot_dr, tot_cr, opening_bal, final_bal, theme)
    
    if table_architecture == "unified":
        column_layout = random.choice(["expanded", "consolidated"])
        html += build_unified_table(txns, column_layout, theme)
    elif table_architecture == "split":
        html += build_split_tables(txns, theme)
    elif table_architecture == "multiline":
        html += build_multiline_blocks(txns, theme)
        
    html += """
        </div>
    </body>
    </html>
    """
    return html

def main():
    output_dir = "bank_statements"
    os.makedirs(output_dir, exist_ok=True)
    
    total_templates = 25
    print(f"Combinatorial Engine: Generating {total_templates} distinct structural & visual formats...")
    
    for idx in range(1, total_templates + 1):
        html_content = generate_procedural_statement(idx)
        
        filepath = os.path.join(output_dir, f"procedural_format_{idx}.html")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html_content)
            
        print(f"[*] Generated unique variant: {filepath}")
        
    print(f"\n[SUCCESS] {total_templates} deeply unique formats generated successfully.")

if __name__ == "__main__":
    main()
