import re
import os
import pdfplumber
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional

class BaseBankParser:
    def __init__(self, bank_name: str):
        self.bank_name = bank_name
        
        # Standard header mappings
        self.DATE_HEADERS = ["date", "transaction date", "txndate", "value date", "posting date", "transactiondate"]
        self.DESC_HEADERS = ["remarks", "narration", "description", "transaction details", "particulars", "details", "transaction remarks", "merchant", "payee", "beneficiary"]
        self.DEBIT_HEADERS = ["debit", "debits", "withdrawal", "withdrawals", "dr", "debit amount", "withdrawal amount", "debitamount"]
        self.CREDIT_HEADERS = ["credit", "credits", "deposit", "deposits", "cr", "credit amount", "deposit amount", "creditamount"]
        self.BALANCE_HEADERS = ["balance", "closing balance", "available balance", "running balance", "account balance", "closingbalance"]
        self.REF_HEADERS = ["reference", "reference number", "transaction id", "txn id", "upi reference", "utr", "rrn", "chequerefnumber"]
        self.CHEQUE_HEADERS = ["cheque number", "cheque no", "cheque", "chq no", "chq number"]
        self.MODE_HEADERS = ["transaction type", "mode", "channel", "payment mode"]

    def normalize_header(self, h: str) -> str:
        """
        Normalize a header string: lowercase, remove non-alphanumeric/spaces, strip.
        """
        if not h:
            return ""
        # Lowercase, replace slashes/dashes/newlines with spaces
        h_clean = str(h).lower().replace("\n", " ").replace("/", " ").replace("-", " ")
        # Remove parentheses and other special characters
        h_clean = re.sub(r'[^a-z0-9\s]', '', h_clean)
        # Collapse multiple spaces to one
        h_clean = re.sub(r'\s+', ' ', h_clean)
        return h_clean.strip()

    def clean_amount(self, val: Any) -> Optional[float]:
        """
        Clean amount strings (remove currency symbols, commas, handle negative signs, etc.)
        """
        if val is None:
            return None
        val_str = str(val).strip()
        if not val_str or val_str == "-" or val_str == "." or val_str.lower() == "nil":
            return None
            
        # Remove currency symbols (INR, Rs, ₹, $, etc.) and commas
        val_str = re.sub(r'[iI][nN][rR]|[rR][sS]|\u20b9|\u20B9|,', '', val_str).strip()
        
        # Handle formats like "120.00 Cr" or "120.00 Dr" or "120.00-"
        is_negative = False
        if val_str.endswith("-"):
            is_negative = True
            val_str = val_str[:-1]
        elif val_str.lower().endswith("dr"):
            is_negative = True
            val_str = val_str[:-2].strip()
        elif val_str.lower().endswith("cr"):
            val_str = val_str[:-2].strip()
            
        # Handle leading minus
        if val_str.startswith("-"):
            is_negative = True
            val_str = val_str[1:]
            
        try:
            num = float(val_str)
            return -num if is_negative else num
        except ValueError:
            return None

    def clean_text(self, val: Any) -> str:
        """
        Clean description/text values.
        """
        if val is None:
            return ""
        val_str = str(val).strip()
        # Collapse multiple whitespace/newlines
        val_str = re.sub(r'\s+', ' ', val_str)
        return val_str

    def parse_date(self, val: Any) -> Optional[str]:
        """
        Tries to parse different date formats and returns in YYYY-MM-DD.
        """
        if not val:
            return None
        val_str = str(val).strip()
        # Extract date-like pattern (ignore trailing details in cell)
        # e.g., "13 May 2026" or "18.06.2026" or "2026-05-13" or "18/06/26"
        # We can extract the first matching sequence of alphanumeric/spaces/punctuation
        val_str = re.sub(r'\n.*', '', val_str) # Keep first line
        
        # Try formats
        formats = [
            "%d.%m.%Y", "%d-%m-%Y", "%d/%m/%Y",
            "%d %b %Y", "%d-%b-%Y", "%d/%b/%Y",
            "%Y-%m-%d", "%d/%m/%y", "%d-%m-%y", "%d.%m.%y",
            "%b %d, %Y", "%d %B %Y", "%Y/%m/%d"
        ]
        
        # Clean string slightly
        date_cleaned = val_str.strip()
        # Remove extra spaces
        date_cleaned = re.sub(r'\s+', ' ', date_cleaned)
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_cleaned, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue
                
        # If the date has some extra words, try to regex find the date part
        # Pattern for "13 May 2026" or "13-May-2026"
        m1 = re.search(r'\b\d{1,2}\s+[A-Za-z]{3,9}\s+\d{2,4}\b', date_cleaned)
        if m1:
            # Try parsing with format
            for fmt in ["%d %b %Y", "%d-%b-%Y", "%d %B %Y"]:
                try:
                    dt = datetime.strptime(m1.group(0), fmt)
                    return dt.strftime("%Y-%m-%d")
                except ValueError:
                    continue
                    
        # Pattern for "18.06.2026" or "18/06/2026"
        m2 = re.search(r'\b\d{1,2}[\/\.\-]\d{1,2}[\/\.\-]\d{2,4}\b', date_cleaned)
        if m2:
            for fmt in ["%d/%m/%Y", "%d.%m.%Y", "%d-%m-%Y", "%d/%m/%y", "%d.%m.%y", "%d-%m-%y"]:
                try:
                    dt = datetime.strptime(m2.group(0), fmt)
                    return dt.strftime("%Y-%m-%d")
                except ValueError:
                    continue

        return None

    def match_column(self, header_normalized: str, header_list: List[str]) -> bool:
        """
        Check if the normalized header matches one of the known patterns.
        """
        return header_normalized in header_list

    def detect_columns(self, row: List[Any]) -> Dict[str, int]:
        """
        Detects standard columns from a table row.
        Returns a mapping of column_name -> index.
        """
        mapping = {}
        for idx, cell in enumerate(row):
            if cell is None:
                continue
            norm = self.normalize_header(str(cell))
            
            if self.match_column(norm, self.DATE_HEADERS) and "date" not in mapping:
                mapping["date"] = idx
            elif self.match_column(norm, self.DESC_HEADERS) and "description" not in mapping:
                mapping["description"] = idx
            elif self.match_column(norm, self.DEBIT_HEADERS) and "debit" not in mapping:
                mapping["debit"] = idx
            elif self.match_column(norm, self.CREDIT_HEADERS) and "credit" not in mapping:
                mapping["credit"] = idx
            elif self.match_column(norm, self.BALANCE_HEADERS) and "balance" not in mapping:
                mapping["balance"] = idx
            elif self.match_column(norm, self.REF_HEADERS) and "reference" not in mapping:
                mapping["reference"] = idx
            elif self.match_column(norm, self.CHEQUE_HEADERS) and "cheque" not in mapping:
                mapping["cheque"] = idx
            elif self.match_column(norm, self.MODE_HEADERS) and "mode" not in mapping:
                mapping["mode"] = idx
                
        return mapping

    def parse_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        Default table parser. Can be overridden in subclasses.
        """
        transactions = []
        col_mapping = {}
        
        # Keep track of parsing statistics
        total_rows_attempted = 0
        date_success = 0
        amount_success = 0
        balance_success = 0
        column_detection_success = False

        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                if not tables:
                    continue
                    
                for table in tables:
                    # Let's filter out completely empty rows
                    table_rows = [r for r in table if r and any(cell is not None and str(cell).strip() for cell in r)]
                    if not table_rows:
                        continue
                        
                    for row_idx, row in enumerate(table_rows):
                        # Detect headers if not already detected
                        # If a row has date, description, and balance, it's likely a header row
                        temp_mapping = self.detect_columns(row)
                        # We need at least date, description, balance, and either debit/credit or amount
                        has_core = "date" in temp_mapping and "description" in temp_mapping and "balance" in temp_mapping
                        
                        # Let's check if we detected columns
                        if has_core:
                            col_mapping = temp_mapping
                            column_detection_success = True
                            continue # Skip the header row itself
                            
                        # If we have column mapping, try parsing the transaction row
                        if col_mapping:
                            # Verify if this is actually a transaction row (starts with a date-like cell or description is not empty)
                            date_val = row[col_mapping["date"]] if col_mapping["date"] < len(row) else None
                            desc_val = row[col_mapping["description"]] if col_mapping["description"] < len(row) else None
                            
                            parsed_date = self.parse_date(date_val)
                            
                            # Handle multi-line: if parsed_date is None but desc_val exists and we have a previous transaction,
                            # append to the previous description.
                            if not parsed_date:
                                if desc_val and transactions:
                                    cleaned_desc = self.clean_text(desc_val)
                                    if cleaned_desc:
                                        transactions[-1]["description"] += " " + cleaned_desc
                                continue
                                
                            # Start parsing a new transaction row
                            total_rows_attempted += 1
                            date_success += 1
                            
                            # Parse Description
                            desc = self.clean_text(desc_val)
                            
                            # Parse Reference
                            ref = ""
                            if "reference" in col_mapping and col_mapping["reference"] < len(row):
                                ref = self.clean_text(row[col_mapping["reference"]])
                            elif "cheque" in col_mapping and col_mapping["cheque"] < len(row):
                                ref = self.clean_text(row[col_mapping["cheque"]])
                                
                            # Parse Debit & Credit
                            debit_val = self.clean_amount(row[col_mapping["debit"]]) if ("debit" in col_mapping and col_mapping["debit"] < len(row)) else None
                            credit_val = self.clean_amount(row[col_mapping["credit"]]) if ("credit" in col_mapping and col_mapping["credit"] < len(row)) else None
                            
                            # Determine type and amount
                            amount = 0.0
                            tx_type = "debit"
                            
                            # Standard debit/credit extraction
                            if debit_val is not None and debit_val != 0.0:
                                amount = -abs(debit_val)
                                tx_type = "debit"
                                amount_success += 1
                            elif credit_val is not None and credit_val != 0.0:
                                amount = abs(credit_val)
                                tx_type = "credit"
                                amount_success += 1
                            else:
                                # Sometimes it's a single column for amount
                                # Let's see if we missed it or it's 0
                                pass
                                
                            # Parse Balance
                            balance_val = row[col_mapping["balance"]] if col_mapping["balance"] < len(row) else None
                            balance = self.clean_amount(balance_val)
                            if balance is not None:
                                balance_success += 1
                            else:
                                balance = 0.0
                                
                            transactions.append({
                                "date": parsed_date,
                                "description": desc,
                                "amount": amount,
                                "type": tx_type,
                                "balance": balance,
                                "reference": ref,
                                "bank": self.bank_name
                            })

        # If table parsing didn't find anything, we can run text-based fallback
        if not transactions:
            # Let's delegate to a text-based extraction if subclass overrides it
            transactions = self.parse_text_fallback(pdf_path)
            # Recompute successes for text parsing if there are any transactions
            if transactions:
                total_rows_attempted = len(transactions)
                date_success = len(transactions)
                amount_success = len(transactions)
                balance_success = len([t for t in transactions if t.get("balance") is not None])
                column_detection_success = True
                
        # Validate transactions and calculate confidence score
        confidence_score, validation_passed = self.validate_and_score(
            transactions,
            column_detection_success,
            total_rows_attempted,
            date_success,
            amount_success,
            balance_success
        )
        
        return {
            "transactions": transactions,
            "confidence_score": confidence_score,
            "validation_passed": validation_passed,
            "parser_used": "regex_parser"
        }

    def parse_text_fallback(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Fallback parser to parse row text line by line using regex.
        Can be overridden in bank specific subclass.
        """
        return []

    def validate_and_score(self, 
                           transactions: List[Dict[str, Any]], 
                           col_detection: bool,
                           total_rows: int,
                           date_success: int,
                           amount_success: int,
                           balance_success: int) -> Tuple[float, bool]:
        """
        Validates the transactions and returns (confidence_score, validation_passed).
        """
        if not transactions:
            return 0.0, False
            
        # 1. Column Detection success (30%)
        col_score = 30.0 if col_detection else 0.0
        
        # 2. Date parsing success (20%)
        date_pct = (date_success / total_rows) if total_rows > 0 else 0
        date_score = date_pct * 20.0
        
        # 3. Amount parsing success (20%)
        amount_pct = (amount_success / total_rows) if total_rows > 0 else 0
        amount_score = amount_pct * 20.0
        
        # 4. Balance parsing success (20%)
        balance_pct = (balance_success / total_rows) if total_rows > 0 else 0
        balance_score = balance_pct * 20.0
        
        # 5. Transaction Validation / Balance Consistency (10%)
        # Check: Balance_{i-1} + Amount_i = Balance_i
        consistency_count = 0
        valid_transitions = 0
        
        # Sort transactions by date (but preserve original order if same date)
        # Note: Statements are typically in chronological or reverse-chronological order.
        # Let's check both orders to see if one matches the balance consistency.
        
        # Check normal chronological order:
        chrono_matches = 0
        for i in range(1, len(transactions)):
            prev_bal = transactions[i-1]["balance"]
            curr_amt = transactions[i]["amount"]
            curr_bal = transactions[i]["balance"]
            # Allow minor rounding differences (e.g. 0.05)
            if abs((prev_bal + curr_amt) - curr_bal) < 0.05:
                chrono_matches += 1
                
        # Check reverse-chronological order:
        rev_chrono_matches = 0
        for i in range(len(transactions) - 2, -1, -1):
            prev_bal = transactions[i+1]["balance"]
            curr_amt = transactions[i]["amount"]
            curr_bal = transactions[i]["balance"]
            if abs((prev_bal + curr_amt) - curr_bal) < 0.05:
                rev_chrono_matches += 1
                
        max_matches = max(chrono_matches, rev_chrono_matches)
        total_transitions = len(transactions) - 1
        
        if total_transitions > 0:
            consistency_pct = max_matches / total_transitions
        else:
            consistency_pct = 1.0 # 1 or 0 rows, vacuum pass
            
        validation_score = consistency_pct * 10.0
        
        total_confidence = col_score + date_score + amount_score + balance_score + validation_score
        
        # Set validation passed if:
        # - Row count > 0
        # - All columns detected
        # - High parsing success (>90% on date, amount, balance)
        # - Balance consistency matches for at least 80% of rows (if > 1 transaction)
        val_passed = (
            len(transactions) > 0 and 
            col_detection and 
            date_pct > 0.9 and 
            amount_pct > 0.9 and 
            balance_pct > 0.9 and 
            (total_transitions == 0 or consistency_pct > 0.8)
        )
        
        return round(total_confidence, 2), val_passed
