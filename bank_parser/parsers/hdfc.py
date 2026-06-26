from parsers.base import BaseBankParser

class HDFCBankParser(BaseBankParser):
    def __init__(self):
        super().__init__("HDFC")
        
        # HDFC specific mappings
        self.DATE_HEADERS.extend(["txn date", "value date"])
        self.DESC_HEADERS.extend(["narration"])
        self.DEBIT_HEADERS.extend(["withdrawal amt", "withdrawal"])
        self.CREDIT_HEADERS.extend(["deposit amt", "deposit"])
        self.BALANCE_HEADERS.extend(["closing balance", "balance"])
        self.REF_HEADERS.extend(["chqref no", "chq ref no", "reference"])
