import re

def detect_bank(text: str) -> str:
    """
    Detects the bank from the raw text extracted from the bank statement PDF.
    Uses IFSC prefixes and specific bank name phrases to avoid false positives.
    Returns: 'ICICI', 'Indian Bank', 'HDFC', 'SBI', or 'UNSUPPORTED'
    """
    text_lower = text.lower()
    
    # 1. Detect Indian Bank
    if "indian bank" in text_lower or "idib0" in text_lower:
        return "Indian Bank"
        
    # 2. Detect SBI (State Bank of India)
    if "state bank of india" in text_lower or "sbin0" in text_lower:
        return "SBI"
        
    # 3. Detect HDFC Bank
    if "hdfc bank" in text_lower or "hdfc0" in text_lower:
        return "HDFC"
        
    # 4. Detect ICICI Bank
    # Match "icici bank" or IFSC code pattern (icic0...)
    # We avoid matching standalone "icici" to prevent false positives from @icici UPI handles
    if "icici bank" in text_lower or "icic0" in text_lower:
        return "ICICI"
        
    return "UNSUPPORTED"
