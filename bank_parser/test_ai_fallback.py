import sys
import json
import pandas as pd
from app import parse_pdf_via_ai

df = pd.DataFrame({"date": ["2026-05-13"], "description": ["Amazon"], "amount": [-120]})
raw_text = df.to_string()

try:
    print(parse_pdf_via_ai(raw_text, "UNSUPPORTED"))
except Exception as e:
    print("FAILED:", repr(e))

