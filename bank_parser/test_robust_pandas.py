import pandas as pd
from typing import List, Dict, Any

def parse_tabular_file(df: 'pd.DataFrame', bank: str) -> List[Dict[str, Any]]:
    import pandas as pd
    import re
    def clean_amount(val):
        if pd.isna(val) or val is None: return 0.0
        val_str = str(val).strip().lower()
        if not val_str or val_str == 'nan': return 0.0
        val_str = re.sub(r'[inr\s,₹a-z]', '', val_str)
        try:
            return float(val_str)
        except:
            return 0.0

    all_rows = [list(df.columns)] + df.values.tolist()
    
    header_idx = -1
    date_idx, desc_idx, amount_idx, debit_idx, credit_idx, balance_idx = -1, -1, -1, -1, -1, -1
    
    date_keywords = ['date', 'txn date', 'transaction date', 'value date']
    desc_keywords = ['desc', 'narration', 'particular', 'remark', 'detail', 'payee', 'merchant']
    amount_keywords = ['amount']
    debit_keywords = ['debit', 'dr', 'withdrawal']
    credit_keywords = ['credit', 'cr', 'deposit']
    balance_keywords = ['balance']
    
    for i, row in enumerate(all_rows):
        row_strs = [str(cell).lower().strip() for cell in row]
        
        d_idx = next((j for j, c in enumerate(row_strs) if any(k in c for k in date_keywords)), -1)
        ds_idx = next((j for j, c in enumerate(row_strs) if any(k in c for k in desc_keywords)), -1)
        
        if d_idx != -1 and ds_idx != -1:
            header_idx = i
            date_idx = d_idx
            desc_idx = ds_idx
            amount_idx = next((j for j, c in enumerate(row_strs) if any(k in c for k in amount_keywords) and not any(k in c for k in debit_keywords) and not any(k in c for k in credit_keywords)), -1)
            debit_idx = next((j for j, c in enumerate(row_strs) if any(k in c for k in debit_keywords)), -1)
            credit_idx = next((j for j, c in enumerate(row_strs) if any(k in c for k in credit_keywords)), -1)
            balance_idx = next((j for j, c in enumerate(row_strs) if any(k in c for k in balance_keywords)), -1)
            break
            
    if header_idx == -1:
        return []
        
    transactions = []
    for row in all_rows[header_idx+1:]:
        if len(row) <= max(date_idx, desc_idx):
            continue
            
        date = str(row[date_idx]).strip()
        desc = str(row[desc_idx]).strip()
        if date.lower() == 'nan' or not date or desc.lower() == 'nan' or not desc:
            continue
            
        if "opening balance" in desc.lower() or "total" in date.lower():
            continue
            
        amount = 0.0
        if amount_idx != -1 and amount_idx < len(row):
            amount = clean_amount(row[amount_idx])
        elif debit_idx != -1 and debit_idx < len(row) and str(row[debit_idx]).lower() != 'nan':
            amount = -abs(clean_amount(row[debit_idx]))
        elif credit_idx != -1 and credit_idx < len(row) and str(row[credit_idx]).lower() != 'nan':
            amount = abs(clean_amount(row[credit_idx]))
            
        bal = 0.0
        if balance_idx != -1 and balance_idx < len(row):
            bal = clean_amount(row[balance_idx])
            
        if amount == 0.0:
            continue
            
        transactions.append({
            "date": date,
            "description": desc,
            "amount": amount,
            "type": "debit" if amount < 0 else "credit",
            "balance": bal,
            "reference": "",
            "bank": bank
        })
    return transactions

df = pd.DataFrame([
    ["Statement for Account", "", "", ""],
    ["", "", "", ""],
    ["txn date", "narration", "debit amount", "balance"],
    ["2026-05-13", "Amazon", "120", "1000"],
    ["2026-05-14", "Salary", None, "2000"]  # Wait, Salary implies credit, but our test df has no credit col. I'll test basic debit logic
])
print(parse_tabular_file(df, "TEST"))
