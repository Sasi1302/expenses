import re
import os
import json
from typing import Optional
from google import genai
from openai import OpenAI
from groq import Groq

CACHE_FILE_PATH = os.path.join(os.path.dirname(__file__), "category_cache.json")

def load_cache() -> dict:
    if os.path.exists(CACHE_FILE_PATH):
        try:
            with open(CACHE_FILE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print("Failed to load category cache:", e)
    return {}

def save_cache(cache: dict):
    try:
        with open(CACHE_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print("Failed to save category cache:", e)

def normalize_description(description: str) -> str:
    return " ".join(description.lower().split())

def category_result(category: str, confidence: int, source: str) -> dict:
    return {
        "category": category,
        "confidence": confidence,
        "needsReview": confidence < 70,
        "categorizationSource": source
    }

# Categories dictionary mapping category names to keywords
CATEGORIES = {
    'Food & Dining': [
        'tea', 'coffee', 'dinner', 'lunch', 'breakfast', 'snack', 'swiggy', 
        'zomato', 'restaurant', 'cafe', 'mcdonalds', 'kfc', 'pizza', 'bread omelette'
    ],
    'Groceries': [
        'milk', 'banana', 'blinkit', 'zepto', 'instamart', 'bigbasket', 
        'dmart', 'supermarket', 'grocery', 'vegetable', 'vegetables', 'fruit'
    ],
    'Transport': [
        'metro', 'rapido', 'uber', 'ola', 'auto', 'bus', 'train', 'flight', 
        'irctc', 'makemytrip', 'toll', 'namma yatri', 'redbus', 'transport',
        'railway', 'railways', 'indian railways'
    ],
    'Utilities': [
        'water', 'electricity', 'internet', 'broadband', 'bill', 'current bill', 'power', 'cable'
    ],
    'Recharges': [
        'recharge', 'jio', 'airtel', 'vi', 'vodafone', 'dth', 'tata sky', 'sun direct'
    ],
    'Gas': [
        'gas', 'lpg', 'indane', 'hp gas', 'bharat gas', 'pipeline'
    ],
    'Transfers/Income': [
        'phonepe', 'gpay', 'paytm', 'upi', 'credit', 'salary', 'freelance', 
        'deposit', 'refund', 'neft', 'imps', 'rtgs', 'upi to person'
    ],
    'Bank Charges': [
        'charge', 'charges', 'service charges', 'sms_chgs', 'uncoll chrg', 'fee', 'apy', 'gst', 'tax', 'penalty', 'emi'
    ],
    'Shopping': [
        'amazon', 'amazon pay', 'amazon pay later', 'flipkart', 'myntra', 'ajio', 'meesho', 'nykaa',
        'shopping', 'mall', 'clothes', 'apparel', 'shoes', 'delhivery', 'xerox'
    ],
    'Entertainment': [
        'pvr', 'inox', 'movie', 'bookmyshow', 'netflix', 'prime', 'spotify'
    ],
    'Fuel': [
        'indian oil', 'hp petrol', 'bharat petroleum', 'shell', 'petrol', 'diesel', 'fuel', 'fuels'
    ],
    'Medical Expenses': [
        'hospital', 'clinic', 'pharmacy', 'medicine', 'apollo', 'medical', 'doctor'
    ],
    'Education': [
        'school', 'college', 'tuition', 'fee', 'university', 'course', 'exam'
    ],
    'Rent/Housing': [
        'rent', 'maintenance', 'housing', 'tenant', 'brokerage'
    ],
    'Investments': [
        'mutual fund', 'angel mf', 'sip', 'stock', 'groww', 'zerodha', 'upstox', 'investment', 'fd'
    ],
    'Insurance': [
        'insurance', 'premium', 'lic', 'policy', 'health insurance', 'car insurance'
    ],
    'Personal Care': [
        'salon', 'spa', 'haircut', 'beauty', 'cosmetics', 'grooming'
    ],
    'Cash Withdrawal': [
        'nfs/cash', 'cash wdl', 'cash withdrawal', 'atm wdl', 'atm withdrawal'
    ],
}

TRANSACTION_TYPE_RULES = [
    (r'\b(nfs/cash|cash wdl|cash withdrawal|atm wdl|atm withdrawal)\b', 'Cash Withdrawal'),
    (r'\b(neft|imps|rtgs)\b', 'Transfers/Income'),
    (r'\b(charge|fee|gst|penalty)\b', 'Bank Charges'),
    (r'\b(pos|debit card|card purchase)\b', 'Shopping'),
]

def has_cash_withdrawal_signal(description: str) -> bool:
    return bool(re.search(r'\b(nfs/cash|cash wdl|cash withdrawal|atm wdl|atm withdrawal)\b', description.lower()))

def categorize_transaction_rules(description: str) -> str:
    """
    Keyword-based rule categorization.
    """
    return categorize_transaction_with_metadata(description)["category"]

def categorize_transaction_with_metadata(description: str, amount: Optional[float] = None, cache: Optional[dict] = None) -> dict:
    """
    Hybrid deterministic categorization with confidence metadata.
    """
    desc = description.lower()
    norm_desc = normalize_description(description)

    if amount is not None:
        try:
            if float(amount) > 0:
                return category_result('Transfers/Income', 100, 'amount_sign')
        except Exception:
            pass

    if cache and norm_desc in cache and cache[norm_desc] != 'Others':
        cached_category = cache[norm_desc]
        if not (cached_category == 'Cash Withdrawal' and not has_cash_withdrawal_signal(desc)):
            return category_result(cached_category, 100, 'cache')

    for pattern, category in TRANSACTION_TYPE_RULES:
        if re.search(pattern, desc):
            if category == 'Transfers/Income' and amount is not None:
                try:
                    if float(amount) < 0:
                        return category_result('Others', 45, 'transaction_type')
                except Exception:
                    pass
            return category_result(category, 95, 'transaction_type')

    for category, keywords in CATEGORIES.items():
        if category == 'Transfers/Income' and amount is not None:
            try:
                if float(amount) < 0:
                    continue
            except Exception:
                pass
        for keyword in keywords:
            pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
            if re.search(pattern, desc):
                return category_result(category, 90, 'merchant_rule')
    if cache and cache.get(norm_desc) == 'Others':
        return category_result('Others', 60, 'cache')

    return category_result('Others', 40, 'unknown')

def apply_category_metadata(tx, result: dict):
    if hasattr(tx, "category"):
        tx.category = result["category"]
        if hasattr(tx, "confidence"):
            tx.confidence = result["confidence"]
        if hasattr(tx, "needsReview"):
            tx.needsReview = result["needsReview"]
        if hasattr(tx, "categorizationSource"):
            tx.categorizationSource = result["categorizationSource"]
    elif isinstance(tx, dict):
        tx.update(result)

def categorize_transaction_ai(description: str, api_keys: dict) -> str:
    """
    Fallback method to categorize using AI if rules fail or categorize as 'Others'.
    """
    prompt = f"""You are a financial transaction categorizer.
Categorize the following transaction description into exactly one of these categories:
{list(CATEGORIES.keys())} or 'Others'.

Description: "{description}"

Respond with ONLY the exact category name. Do not include quotes, markdown formatting, or any extra text.
"""
    
    # Try Groq first
    if api_keys.get("GROQ_API_KEY"):
        try:
            client = Groq(api_key=api_keys["GROQ_API_KEY"])
            completion = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile",
                temperature=0,
                max_tokens=10
            )
            ans = completion.choices[0].message.content.strip()
            if ans in CATEGORIES or ans == 'Others':
                return ans
        except Exception as e:
            print("Groq categorizer fallback failed:", e)

    # Try OpenAI next
    if api_keys.get("OPENAI_API_KEY"):
        try:
            client = OpenAI(api_key=api_keys["OPENAI_API_KEY"])
            completion = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="gpt-4o-mini",
                temperature=0,
                max_tokens=10
            )
            ans = completion.choices[0].message.content.strip()
            if ans in CATEGORIES or ans == 'Others':
                return ans
        except Exception as e:
            print("OpenAI categorizer fallback failed:", e)

    # Try Gemini last
    if api_keys.get("GEMINI_API_KEY"):
        try:
            client = genai.Client(api_key=api_keys["GEMINI_API_KEY"])
            result = client.models.generate_content(
                model='gemini-1.5-flash',
                contents=prompt,
            )
            ans = result.text.strip()
            if ans in CATEGORIES or ans == 'Others':
                return ans
        except Exception as e:
            print("Gemini categorizer fallback failed:", e)

    return 'Others'

def categorize_transactions_batch(transactions: list, api_keys: dict) -> list:
    """
    Categorizes a list of transactions in batch using:
    1. Amount sign for credits
    2. Batch LLM calls for every debit/expense description
    3. Local deterministic rules as fallback if AI is unavailable
    """
    cache = load_cache()
    
    # Track debit descriptions for AI categorization.
    debit_descriptions = set()
    
    # Stage 1: Categorize via amount, user cache, transaction-type regexes, and merchant rules.
    for tx in transactions:
        # Check if transaction is a dict or an object with attributes (like Pydantic models)
        if hasattr(tx, "model_dump"):
            desc = tx.description
            amount = tx.amount
        elif isinstance(tx, dict):
            desc = tx.get("description", "")
            amount = tx.get("amount", 0.0)
        else:
            desc = getattr(tx, "description", "")
            amount = getattr(tx, "amount", 0.0)
            
        try:
            amt_val = float(amount)
        except Exception:
            amt_val = 0.0

        result = categorize_transaction_with_metadata(desc, amt_val, cache)
        apply_category_metadata(tx, result)

        if amt_val < 0:
            debit_descriptions.add(desc)

    # Stage 2: Batch AI call for every debit description.
    if debit_descriptions:
        uncategorized_list = list(debit_descriptions)
        expense_categories = [k for k in CATEGORIES.keys() if k != 'Transfers/Income']
        
        prompt = f"""You are a personal finance assistant.
Categorize the following transaction descriptions into exactly one of these expense categories:
{expense_categories} or 'Others'.

All of these transactions are debit/expense transactions. Do not categorize any of them as 'Transfers/Income'.

Important:
- Use the full description, merchant/person name, UPI handle, remarks, and purpose text.
- Do not classify a UPI row as Cash Withdrawal only because it contains "BRANCH : ATM SERVICE BRANCH".
- Cash Withdrawal only when the description has a real withdrawal signal like ATM WDL, CASH WDL, CASH WITHDRAWAL, or NFS/CASH.
- If it is only a person name or generic QR with no clear purpose, categorize it as 'Others'.

Transaction descriptions to categorize:
"""
        for i, desc in enumerate(uncategorized_list, start=1):
            prompt += f"{i}. \"{desc}\"\n"
            
        prompt += """
Respond with a JSON object mapping each exact transaction description to its category.
Format:
{
  "description 1": "CategoryName",
  "description 2": "CategoryName"
}
Respond ONLY with the JSON object. Do not include markdown formatting like ```json or ```.
"""
        
        ai_mappings = {}
        used_ai = False
        
        # 1. Try Groq
        if api_keys.get("GROQ_API_KEY"):
            try:
                client = Groq(api_key=api_keys["GROQ_API_KEY"])
                completion = client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model="llama-3.3-70b-versatile",
                    temperature=0
                )
                res_text = completion.choices[0].message.content.strip()
                if res_text.startswith("```json"):
                    res_text = res_text.replace("```json", "", 1).rstrip("`").strip()
                elif res_text.startswith("```"):
                    res_text = res_text.replace("```", "", 1).rstrip("`").strip()
                ai_mappings = json.loads(res_text)
                used_ai = True
            except Exception as e:
                print("Groq batch categorization failed:", e)

        # 2. Try OpenAI
        if not used_ai and api_keys.get("OPENAI_API_KEY"):
            try:
                client = OpenAI(api_key=api_keys["OPENAI_API_KEY"])
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
                ai_mappings = json.loads(res_text)
                used_ai = True
            except Exception as e:
                print("OpenAI batch categorization failed:", e)

        # 3. Try Gemini
        if not used_ai and api_keys.get("GEMINI_API_KEY"):
            try:
                client = genai.Client(api_key=api_keys["GEMINI_API_KEY"])
                result = client.models.generate_content(
                    model='gemini-1.5-flash',
                    contents=prompt,
                )
                res_text = result.text.strip()
                if res_text.startswith("```json"):
                    res_text = res_text.replace("```json", "", 1).rstrip("`").strip()
                elif res_text.startswith("```"):
                    res_text = res_text.replace("```", "", 1).rstrip("`").strip()
                ai_mappings = json.loads(res_text)
                used_ai = True
            except Exception as e:
                print("Gemini batch categorization failed:", e)

        # Update cache with results
        if used_ai and isinstance(ai_mappings, dict):
            cache_updated = False
            for raw_desc, cat in ai_mappings.items():
                if cat in CATEGORIES or cat == 'Others':
                    norm_desc = normalize_description(raw_desc)
                    cache[norm_desc] = cat
                    cache_updated = True
            
            if cache_updated:
                save_cache(cache)
                
            # Apply AI results to matching debit transactions.
            for tx in transactions:
                if hasattr(tx, "category"):
                    desc = tx.description
                    try:
                        amt_val = float(tx.amount)
                    except Exception:
                        amt_val = 0.0
                    norm_desc = normalize_description(desc)
                    if amt_val < 0 and norm_desc in cache:
                        category = cache[norm_desc]
                        result = category_result(category, 75 if category != 'Others' else 50, 'ai')
                        apply_category_metadata(tx, result)
                elif isinstance(tx, dict):
                    desc = tx.get("description", "")
                    try:
                        amt_val = float(tx.get("amount", 0.0))
                    except Exception:
                        amt_val = 0.0
                    norm_desc = normalize_description(desc)
                    if amt_val < 0 and norm_desc in cache:
                        category = cache[norm_desc]
                        result = category_result(category, 75 if category != 'Others' else 50, 'ai')
                        apply_category_metadata(tx, result)
                        
    return transactions
