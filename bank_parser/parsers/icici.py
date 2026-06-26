from parsers.base import BaseBankParser

class ICICIBankParser(BaseBankParser):
    def __init__(self):
        super().__init__("ICICI")
        
        # ICICI specific header overrides if needed
        self.DATE_HEADERS.extend(["transaction date", "date"])
        self.DESC_HEADERS.extend(["transaction remarks", "remarks", "narration","Particulars","Description"])
        self.DEBIT_HEADERS.extend(["withdrawal amount", "withdrawal amount inr", "withdrawal","withdrawal inr"])
        self.CREDIT_HEADERS.extend(["deposit amount", "deposit amount inr", "deposit","deposit inr"])
        self.BALANCE_HEADERS.extend(["balance", "balance inr", "closing balance","closing balance inr"])
