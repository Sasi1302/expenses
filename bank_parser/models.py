from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class Transaction(BaseModel):
    date: str = Field(description="Transaction date in YYYY-MM-DD format")
    description: str = Field(description="Normalized description or narration")
    amount: float = Field(description="Amount (positive for credits, negative for debits)")
    type: str = Field(description="Transaction type: 'debit' or 'credit'")
    balance: float = Field(description="Running balance after transaction")
    reference: str = Field(default="", description="Cheque/Reference/UTR number if available")
    bank: str = Field(description="Name of the bank")
    category: str = Field(default="Others", description="Categorized transaction segment")
    confidence: int = Field(default=40, description="Category confidence score from 0 to 100")
    needsReview: bool = Field(default=True, description="Whether the category should be reviewed by the user")
    categorizationSource: str = Field(default="unknown", description="Source used to categorize the transaction")

class Summary(BaseModel):
    total_expenses: float
    total_income: float
    top_category: str
    transaction_count: int

class ParseResponse(BaseModel):
    bank: str
    transactions: List[Transaction]
    summary: Dict[str, Any]
    insights: List[str]
    confidence_score: float
    parser_used: str
