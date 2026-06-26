import re
import pdfplumber
from typing import List, Dict, Any
from parsers.base import BaseBankParser

class IndianBankParser(BaseBankParser):
    def __init__(self):
        super().__init__("Indian Bank")
        self.DATE_HEADERS.extend(["date"])
        self.DESC_HEADERS.extend(["transaction details", "details"])
        self.DEBIT_HEADERS.extend(["debits", "debit"])
        self.CREDIT_HEADERS.extend(["credits", "credit"])
        self.BALANCE_HEADERS.extend(["balance"])

    def parse_text_fallback(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Regex-based text fallback parsing specifically designed for Indian Bank statements.
        This handles statements where columns are collapsed in PDF text extraction.
        """
        transactions = []
        
        # Load PDF text page-by-page
        full_text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"
                    
        lines = [line.strip() for line in full_text.split("\n") if line.strip()]
        
        # Date regex: e.g. "11 May 2026" or "13 May 2026" at start of line
        date_regex = re.compile(r'^(\d{1,2}\s+[A-Za-z]{3}\s+\d{4})')
        
        # Amount lines patterns (searched anywhere in the line):
        # 1. Debit: "INR 12.00 - INR 3,087.21"
        debit_pattern = re.compile(r'INR\s+([\d,]+\.\d{2})\s+-\s*INR\s+([\d,]+\.\d{2})', re.IGNORECASE)
        # 2. Credit: "- INR 500.00 INR 1,546.21" or "- INR 100.00 INR 1,607.21"
        credit_pattern = re.compile(r'-\s*INR\s+([\d,]+\.\d{2})\s+INR\s+([\d,]+\.\d{2})', re.IGNORECASE)
        
        # Noise patterns to ignore and reset description collection
        noise_patterns = [
            r'^account statement',
            r'^last \d+ transactions',
            r'^account details',
            r'^account summary',
            r'^account holder name',
            r'^opening balance',
            r'^account type',
            r'^total credits',
            r'^account number',
            r'^customer\'s address',
            r'^total debits',
            r'^street',
            r'^ending balance',
            r'^branch name',
            r'^ifsc',
            r'^account currency',
            r'^account activity',
            r'^date transaction details',
            r'^total inr',
            r'^indian bank \|'
        ]
        
        def is_noise(line_str: str) -> bool:
            line_lower = line_str.lower()
            return any(re.search(pat, line_lower) for pat in noise_patterns)
            
        has_active_txn = False
        
        for line in lines:
            if is_noise(line):
                has_active_txn = False
                continue
                
            date_match = date_regex.match(line)
            if date_match:
                date_str = date_match.group(1)
                parsed_date = self.parse_date(date_str)
                
                # Check for debit or credit amounts on the same line
                deb_match = debit_pattern.search(line)
                cred_match = credit_pattern.search(line)
                
                if parsed_date and (deb_match or cred_match):
                    # We have a valid start of transaction
                    amount = 0.0
                    tx_type = "debit"
                    balance = 0.0
                    pat_start = len(line)
                    
                    if deb_match:
                        amount_val = self.clean_amount(deb_match.group(1))
                        balance_val = self.clean_amount(deb_match.group(2))
                        amount = -abs(amount_val) if amount_val else 0.0
                        tx_type = "debit"
                        balance = balance_val or 0.0
                        pat_start = deb_match.start(0)
                    elif cred_match:
                        amount_val = self.clean_amount(cred_match.group(1))
                        balance_val = self.clean_amount(cred_match.group(2))
                        amount = abs(amount_val) if amount_val else 0.0
                        tx_type = "credit"
                        balance = balance_val or 0.0
                        pat_start = cred_match.start(0)
                        
                    # Extract the description part between the date and the pattern start
                    date_end = date_match.end(1)
                    desc_start = line[date_end:pat_start].strip()
                    
                    transactions.append({
                        "date": parsed_date,
                        "description": desc_start,
                        "amount": amount,
                        "type": tx_type,
                        "balance": balance,
                        "reference": "",
                        "bank": self.bank_name
                    })
                    has_active_txn = True
            elif has_active_txn and transactions:
                # Append subsequent lines to the description of the active transaction
                cleaned_line = line.strip()
                if cleaned_line:
                    transactions[-1]["description"] = (transactions[-1]["description"] + " " + cleaned_line).strip()
                    
        return transactions
