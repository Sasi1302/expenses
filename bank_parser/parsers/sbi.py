from parsers.base import BaseBankParser

class SBIBankParser(BaseBankParser):
    def __init__(self):
        super().__init__("SBI")
        
        # SBI specific mappings
        self.DATE_HEADERS.extend(["txn date", "date"])
        self.DESC_HEADERS.extend(["description", "narration"])
        self.DEBIT_HEADERS.extend(["debit", "withdrawal"])
        self.CREDIT_HEADERS.extend(["credit", "deposit"])
        self.BALANCE_HEADERS.extend(["balance", "closing balance"])
