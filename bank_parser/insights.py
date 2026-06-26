import pandas as pd
import re
from typing import List, Dict, Any
from openai import OpenAI
from groq import Groq
from google import genai

def extract_merchant(desc: str) -> str:
    """
    Cleans up description to find a simplified merchant/payee name.
    E.g. HDFC0MERUPI/Blinkit/XXXXX95663/blinkit. -> Blinkit
         YESB0MCHUPI/Tea Boy/XXXXX/paytm... -> Tea Boy
    """
    desc_clean = desc.strip()
    
    # Try splitting by '/' which is common in Indian UPI transaction descriptions
    parts = desc_clean.split('/')
    if len(parts) > 1:
        # Check if the first part looks like a bank code or transaction code (e.g. YESB0PTMUPI, SBIN0016209)
        first = parts[0]
        # Match alphanumeric code (e.g. 4-15 chars containing digits) or UPI prefix
        if (len(first) >= 4 and any(c.isdigit() for c in first)) or first.upper() == 'UPI':
            merchant = parts[1].strip()
            # If the merchant name has placeholder text like 'XXXXX', it might be in parts[2] or let's clean it
            merchant = re.sub(r'X{3,}', '', merchant).strip()
            if merchant:
                return merchant
                
    # If no slashes but has 'UPI TO' or similar
    upi_to_match = re.search(r'UPI TO\s+([^/]+)', desc_clean, re.IGNORECASE)
    if upi_to_match:
        return upi_to_match.group(1).strip()
        
    # Default to first 30 characters
    return desc_clean[:30]

def generate_insights_summary(transactions: List[Dict[str, Any]], api_keys: dict) -> Dict[str, Any]:
    """
    Generates structured statistics and natural language insights.
    """
    if not transactions:
        return {
            "summary": {
                "total_expenses": 0.0,
                "total_income": 0.0,
                "top_category": "None",
                "top_merchants": [],
                "monthly_trend": {},
                "food_spending": 0.0,
                "transport_spending": 0.0,
                "shopping_spending": 0.0,
                "transaction_count": 0
            },
            "insights": ["No transaction data available to generate insights."]
        }
        
    df = pd.DataFrame(transactions)
    df['date'] = pd.to_datetime(df['date'])
    df['month'] = df['date'].dt.strftime('%Y-%m')
    
    # Separate expenses (debit) and income (credit)
    expenses_df = df[df['amount'] < 0]
    income_df = df[df['amount'] > 0]
    
    total_expenses = float(abs(expenses_df['amount'].sum()))
    total_income = float(income_df['amount'].sum())
    
    # Top Expense Category
    top_cat = "None"
    if not expenses_df.empty:
        cat_sums = expenses_df.groupby('category')['amount'].sum().abs()
        if not cat_sums.empty:
            top_cat = cat_sums.idxmax()
            
    # Top Merchants (clean merchant names first)
    df['merchant'] = df['description'].apply(extract_merchant)
    expenses_df = df[df['amount'] < 0] # Refresh with merchant column
    
    top_merchants = []
    if not expenses_df.empty:
        merchant_sums = expenses_df.groupby('merchant')['amount'].sum().abs().reset_index()
        merchant_sums = merchant_sums.sort_values(by='amount', ascending=False).head(5)
        for _, row in merchant_sums.iterrows():
            top_merchants.append({
                "merchant": row['merchant'],
                "amount": float(row['amount'])
            })
            
    # Monthly spending trend (both expenses and income)
    monthly_trend = {}
    if not df.empty:
        for m in df['month'].unique():
            m_df = df[df['month'] == m]
            exp_sum = abs(m_df[m_df['amount'] < 0]['amount'].sum())
            inc_sum = m_df[m_df['amount'] > 0]['amount'].sum()
            monthly_trend[m] = {
                "expense": round(float(exp_sum), 2),
                "income": round(float(inc_sum), 2)
            }
            
    # Category specific spending
    food_spending = float(abs(df[(df['category'] == 'Food & Dining') & (df['amount'] < 0)]['amount'].sum()))
    transport_spending = float(abs(df[(df['category'] == 'Transport') & (df['amount'] < 0)]['amount'].sum()))
    shopping_spending = float(abs(df[(df['category'] == 'Shopping') & (df['amount'] < 0)]['amount'].sum()))
    
    summary = {
        "total_expenses": round(total_expenses, 2),
        "total_income": round(total_income, 2),
        "top_category": top_cat,
        "top_merchants": top_merchants,
        "monthly_trend": monthly_trend,
        "food_spending": round(food_spending, 2),
        "transport_spending": round(transport_spending, 2),
        "shopping_spending": round(shopping_spending, 2),
        "transaction_count": len(transactions)
    }
    
    # Generate conversational insights using LLM
    insights = []
    
    prompt = f"""You are a personal finance assistant. Analyze these expense statistics and generate 3-5 short, conversational, action-oriented insights in a bulleted list. 
Refer to amounts in Indian Rupees (e.g. ₹X,XXX).
Keep them brief and natural, like a personal banker talking to a client.

Data:
- Total Expenses: ₹{summary['total_expenses']}
- Total Income: ₹{summary['total_income']}
- Top Category: {summary['top_category']}
- Food Spending: ₹{summary['food_spending']}
- Transport Spending: ₹{summary['transport_spending']}
- Shopping Spending: ₹{summary['shopping_spending']}
- Top 3 Merchants: {', '.join([f"{m['merchant']} (₹{m['amount']})" for m in summary['top_merchants'][:3]])}
- Monthly Trend: {summary['monthly_trend']}

Return ONLY the bulleted list. Do not include introductory text, salutations, or markdown formatting blocks like ```json.
"""

    # LLM Fallback Chain
    used_ai = False
    
    # 1. Groq
    if api_keys.get("GROQ_API_KEY"):
        try:
            client = Groq(api_key=api_keys["GROQ_API_KEY"])
            completion = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile",
                temperature=0.7
            )
            response = completion.choices[0].message.content.strip()
            lines = [line.strip().lstrip('-* ').strip() for line in response.split('\n') if line.strip()]
            insights = [l for l in lines if l]
            used_ai = True
        except Exception as e:
            print("Groq insights generation failed:", e)
            
    # 2. OpenAI
    if not used_ai and api_keys.get("OPENAI_API_KEY"):
        try:
            client = OpenAI(api_key=api_keys["OPENAI_API_KEY"])
            completion = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="gpt-4o-mini",
                temperature=0.7
            )
            response = completion.choices[0].message.content.strip()
            lines = [line.strip().lstrip('-* ').strip() for line in response.split('\n') if line.strip()]
            insights = [l for l in lines if l]
            used_ai = True
        except Exception as e:
            print("OpenAI insights generation failed:", e)

    # 3. Gemini
    if not used_ai and api_keys.get("GEMINI_API_KEY"):
        try:
            client = genai.Client(api_key=api_keys["GEMINI_API_KEY"])
            result = client.models.generate_content(
                model='gemini-1.5-flash',
                contents=prompt,
            )
            response = result.text.strip()
            lines = [line.strip().lstrip('-* ').strip() for line in response.split('\n') if line.strip()]
            insights = [l for l in lines if l]
            used_ai = True
        except Exception as e:
            print("Gemini insights generation failed:", e)

    # Fallback to rule-based insights if all AI calls failed or no keys
    if not insights:
        insights.append(f"Your total expenses for this period are ₹{summary['total_expenses']:.2f}, while your total income is ₹{summary['total_income']:.2f}.")
        if summary['top_category'] != "None":
            insights.append(f"{summary['top_category']} is your top spending category.")
        if summary['food_spending'] > 0:
            insights.append(f"You spent ₹{summary['food_spending']:.2f} on food & dining.")
        if summary['top_merchants']:
            insights.append(f"Your highest merchant expense was with {summary['top_merchants'][0]['merchant']} totaling ₹{summary['top_merchants'][0]['amount']:.2f}.")
            
    return {
        "summary": summary,
        "insights": insights
    }
