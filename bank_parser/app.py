import os
import tempfile
import json
import re
from typing import List, Dict, Any
# pyrefly: ignore [missing-import]
from fastapi import FastAPI, UploadFile, File, HTTPException
# pyrefly: ignore [missing-import]
from fastapi.middleware.cors import CORSMiddleware
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

# Import our components
from detector import detect_bank
from models import ParseResponse, Transaction
from categorizer import categorize_transaction_rules, categorize_transaction_ai, categorize_transactions_batch
from insights import generate_insights_summary

# Import parsers
from parsers.icici import ICICIBankParser
from parsers.indian_bank import IndianBankParser
from parsers.hdfc import HDFCBankParser
from parsers.sbi import SBIBankParser

# Load environment variables
load_dotenv(dotenv_path="/Users/cmi_10139/Desktop/sasi/expense-analyzer/backend/.env")

app = FastAPI(
    title="Bank Statement Analyzer API",
    description="Microservice to parse bank statement PDFs and generate insights",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Keys dictionary for LLM calls
API_KEYS = {
    "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
    "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"),
    "GROQ_API_KEY": os.getenv("GROQ_API_KEY"),
    "DEEPSEEK_API_KEY": os.getenv("DEEPSEEK_API_KEY")
}

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

def parse_pdf_via_ai(text: str, bank: str) -> List[Dict[str, Any]]:
    """
    Fallback method: Uses LLM to extract transaction objects from the PDF text.
    """
    prompt = f"""You are an expert financial data extractor. I will provide you with the raw text extracted from a bank statement PDF.
Your goal is to parse this text and extract all transactions into a structured JSON array.
Respond ONLY with the JSON array. Do not include markdown formatting like ```json or ```.

Each object in the array must have the exact following keys:
- "date": The date of the transaction in "YYYY-MM-DD" format.
- "description": The clean description or narration of the transaction.
- "amount": The transaction amount as a number. If it is an expense/debit/withdrawal, make it a negative number (e.g. -120.00). If it is income/credit/deposit, make it a positive number.
- "type": "debit" or "credit".
- "balance": The running balance after the transaction as a number.
- "reference": Cheque, reference, or UTR number if available, otherwise "".

Raw text from PDF:
{text}
"""
    
    # Try DeepSeek first
    if API_KEYS.get("DEEPSEEK_API_KEY"):
        try:
            from openai import OpenAI
            client = OpenAI(api_key=API_KEYS["DEEPSEEK_API_KEY"], base_url="https://api.deepseek.com")
            completion = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="deepseek-chat",
                temperature=0
            )
            res_text = completion.choices[0].message.content.strip()
            # Clean markdown block if present
            if res_text.startswith("```json"):
                res_text = res_text.replace("```json", "", 1).rstrip("`").strip()
            elif res_text.startswith("```"):
                res_text = res_text.replace("```", "", 1).rstrip("`").strip()
            parsed = json.loads(res_text)
            if isinstance(parsed, list):
                return parsed
        except Exception as e:
            print("DeepSeek AI parsing failed, falling back...", e)

    # Try Groq second
    if API_KEYS.get("GROQ_API_KEY"):
        try:
            from groq import Groq
            client = Groq(api_key=API_KEYS["GROQ_API_KEY"])
            completion = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile",
                temperature=0
            )
            res_text = completion.choices[0].message.content.strip()
            # Clean markdown block if present
            if res_text.startswith("```json"):
                res_text = res_text.replace("```json", "", 1).rstrip("`").strip()
            elif res_text.startswith("```"):
                res_text = res_text.replace("```", "", 1).rstrip("`").strip()
            parsed = json.loads(res_text)
            if isinstance(parsed, list):
                return parsed
        except Exception as e:
            print("Groq AI parsing failed, falling back...", e)

    # Try OpenAI second
    if API_KEYS.get("OPENAI_API_KEY"):
        try:
            from openai import OpenAI
            client = OpenAI(api_key=API_KEYS["OPENAI_API_KEY"])
            completion = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="gpt-4o-mini",
                temperature=0
            )
            res_text = completion.choices[0].message.content.strip()
            if res_text.startswith("```json"):
                res_text = res_text.replace("```json", "", 1).rstrip("`").strip()
            elif res_text.startswith("```"):
                res_text = res_text.replace("```", "", 1).rstrip("`").strip()
            parsed = json.loads(res_text)
            if isinstance(parsed, list):
                return parsed
        except Exception as e:
            print("OpenAI AI parsing failed, falling back...", e)

    # Try Gemini third
    if API_KEYS.get("GEMINI_API_KEY"):
        try:
            from google import genai
            client = genai.Client(api_key=API_KEYS["GEMINI_API_KEY"])
            result = client.models.generate_content(
                model='gemini-1.5-flash',
                contents=prompt,
            )
            res_text = result.text.strip()
            if res_text.startswith("```json"):
                res_text = res_text.replace("```json", "", 1).rstrip("`").strip()
            elif res_text.startswith("```"):
                res_text = res_text.replace("```", "", 1).rstrip("`").strip()
            parsed = json.loads(res_text)
            if isinstance(parsed, list):
                return parsed
        except Exception as e:
            print("Gemini AI parsing failed...", e)

    raise HTTPException(status_code=500, detail="All AI fallback endpoints failed to parse PDF.")

@app.post("/parse", response_model=ParseResponse)
async def parse_statement(file: UploadFile = File(...)):
    """
    Parses a bank statement PDF, CSV, or Excel file.
    Exposes POST /parse.
    """
    allowed_exts = (".pdf", ".csv", ".xls", ".xlsx")
    if not file.filename.lower().endswith(allowed_exts):
        raise HTTPException(status_code=400, detail="Only PDF, CSV, and Excel statements are supported.")

    import pdfplumber
    import pandas as pd
    
    ext = os.path.splitext(file.filename)[1].lower()
    
    # Write to a temporary file
    temp_fd, temp_path = tempfile.mkstemp(suffix=ext)
    try:
        with os.fdopen(temp_fd, 'wb') as tmp:
            tmp.write(await file.read())

        # Extract raw text to detect bank and for LLM fallback
        raw_text = ""
        
        if ext == ".pdf":
            with pdfplumber.open(temp_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        raw_text += text + "\n"
        else:
            raw_text = "Tabular Data"

        is_pdf = ext == ".pdf"
        
        if not raw_text.strip():
            raise HTTPException(status_code=400, detail="The uploaded file contains no readable text.")

        # Detect the Bank
        bank = detect_bank(raw_text) if is_pdf else "CSV/Excel Bank"
        print(f"Detected Bank: {bank}")

        transactions = []
        confidence_score = 0.0
        parser_used = "regex_parser"

        if not is_pdf:
            if ext == ".csv":
                try:
                    df = pd.read_csv(temp_path, header=None, names=range(30))
                    transactions = parse_tabular_file(df, bank)
                    confidence_score = 90.0
                    parser_used = "tabular_parser"
                except Exception as e:
                    print("Tabular parsing failed", e)
            elif ext in (".xls", ".xlsx"):
                try:
                    df = pd.read_excel(temp_path, header=None, names=range(30))
                    transactions = parse_tabular_file(df, bank)
                    confidence_score = 90.0
                    parser_used = "tabular_parser"
                except Exception as e:
                    print("Tabular parsing failed", e)

        # Choose the specific parser

        parser = None
        if bank == "ICICI":
            parser = ICICIBankParser()
        elif bank == "Indian Bank":
            parser = IndianBankParser()
        elif bank == "HDFC":
            parser = HDFCBankParser()
        elif bank == "SBI":
            parser = SBIBankParser()

        # If bank is supported and it is a PDF, try regex parser
        if parser is not None and is_pdf and not transactions:
            try:
                # 1. First Attempt: Run standard parser (table extraction)
                result = parser.parse_pdf(temp_path)
                transactions = result.get("transactions", [])
                confidence_score = result.get("confidence_score", 0.0)
                parser_used = result.get("parser_used", "regex_parser")
                
                # 2. Retry Attempt: If confidence score is below 80, try fallback parser modes (like text regex fallback)
                if confidence_score < 80:
                    print(f"Validation confidence low ({confidence_score}%). Retrying with text fallback...")
                    fallback_txs = parser.parse_text_fallback(temp_path)
                    if fallback_txs:
                        # Re-calculate confidence for text fallback
                        total_rows = len(fallback_txs)
                        date_success = len(fallback_txs)
                        amount_success = len(fallback_txs)
                        balance_success = len([t for t in fallback_txs if t.get("balance") is not None])
                        
                        fallback_conf, fallback_val = parser.validate_and_score(
                            fallback_txs,
                            col_detection=True,
                            total_rows=total_rows,
                            date_success=date_success,
                            amount_success=amount_success,
                            balance_success=balance_success
                        )
                        
                        # If fallback parser gave better confidence, use it
                        if fallback_conf > confidence_score:
                            transactions = fallback_txs
                            confidence_score = fallback_conf
                            parser_used = "regex_parser_text_fallback"
                            print(f"Fallback parser improved confidence to {confidence_score}%")

            except Exception as ex:
                print(f"Parser exception encountered: {ex}. Retrying via text fallback if possible...")
                # Try direct text fallback in case of exceptions
                try:
                    fallback_txs = parser.parse_text_fallback(temp_path)
                    if fallback_txs:
                        transactions = fallback_txs
                        confidence_score = 75.0  # assign default fallback confidence
                        parser_used = "regex_parser_text_fallback"
                except Exception:
                    pass

        # 3. AI Fallback: Use AI if bank is unsupported, or if confidence score is still below 80
        if (bank == "UNSUPPORTED" or confidence_score < 80) and is_pdf:
            print(f"Proceeding with AI Fallback. Reason: Bank={bank}, Confidence={confidence_score}%")
            ai_txs = parse_pdf_via_ai(raw_text, bank)
            
            # Format and normalize AI transactions
            transactions = []
            for tx in ai_txs:
                # Classify type
                amt = float(tx.get("amount", 0.0))
                tx_type = tx.get("type", "debit" if amt < 0 else "credit")
                
                transactions.append({
                    "date": tx.get("date", ""),
                    "description": tx.get("description", "Unknown"),
                    "amount": amt,
                    "type": tx_type,
                    "balance": float(tx.get("balance", 0.0)),
                    "reference": tx.get("reference", ""),
                    "bank": bank
                })
                
            confidence_score = 90.0  # High confidence assigned to parsed LLM structure
            parser_used = "ai_fallback"

        # Apply rule-based & AI-based categorization in batch
        final_transactions = []
        for tx in transactions:
            tx_obj = Transaction(
                date=tx["date"],
                description=tx["description"],
                amount=tx["amount"],
                type=tx["type"],
                balance=tx["balance"],
                reference=tx.get("reference", ""),
                bank=tx["bank"],
                category="Others"
            )
            final_transactions.append(tx_obj)

        categorize_transactions_batch(final_transactions, API_KEYS)

        # Generate summary and conversational insights
        insights_res = generate_insights_summary([t.model_dump() for t in final_transactions], API_KEYS)
        
        response = ParseResponse(
            bank=bank,
            transactions=final_transactions,
            summary=insights_res["summary"],
            insights=insights_res["insights"],
            confidence_score=confidence_score,
            parser_used=parser_used
        )
        return response

    finally:
        # Always clean up the temporary file
        if os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except Exception:
                pass

if __name__ == "__main__":
    # pyrefly: ignore [missing-import]
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
