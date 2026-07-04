import pandas as pd
import re

def clean_amount(val):
    if pd.isna(val): return 0.0
    val_str = str(val).strip().lower()
    val_str = re.sub(r'[inr\s,₹a-z]', '', val_str)
    try:
        return float(val_str)
    except:
        return 0.0

def parse_tabular_file(df):
    headers = [str(c).lower().strip() for c in df.columns]
    
    date_col = next((c for c in headers if 'date' in c), None)
    desc_col = next((c for c in headers if any(x in c for x in ['desc', 'narration', 'particular', 'remark'])), None)
    amount_col = next((c for c in headers if 'amount' in c and 'debit' not in c and 'credit' not in c), None)
    debit_col = next((c for c in headers if 'debit' in c or 'dr' in c or 'withdrawal' in c), None)
    credit_col = next((c for c in headers if 'credit' in c or 'cr' in c or 'deposit' in c), None)
    balance_col = next((c for c in headers if 'balance' in c), None)
    
    if not date_col or not desc_col:
        return []
        
    transactions = []
    for _, row in df.iterrows():
        date = str(row.iloc[headers.index(date_col)])
        desc = str(row.iloc[headers.index(desc_col)])
        if date == 'nan' or desc == 'nan': continue
        
        amount = 0.0
        if amount_col:
            amount = clean_amount(row.iloc[headers.index(amount_col)])
        elif debit_col and not pd.isna(row.iloc[headers.index(debit_col)]):
            amount = -abs(clean_amount(row.iloc[headers.index(debit_col)]))
        elif credit_col and not pd.isna(row.iloc[headers.index(credit_col)]):
            amount = abs(clean_amount(row.iloc[headers.index(credit_col)]))
            
        bal = 0.0
        if balance_col:
            bal = clean_amount(row.iloc[headers.index(balance_col)])
            
        transactions.append({
            "date": date,
            "description": desc,
            "amount": amount,
            "type": "debit" if amount < 0 else "credit",
            "balance": bal,
            "reference": "",
            "bank": "UNSUPPORTED"
        })
    return transactions

df = pd.DataFrame({"txn date": ["2026-05-13"], "narration": ["Amazon"], "debit amount": [120], "balance": [1000]})
print(parse_tabular_file(df))
