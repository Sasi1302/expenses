import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import OpenAI from 'openai';
import Groq from 'groq-sdk';
import { GoogleGenerativeAI } from '@google/generative-ai';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const cachePath = path.join(__dirname, '../../bank_parser/category_cache.json');

const CATEGORIES = {
  'Food & Dining': [
    'tea', 'coffee', 'dinner', 'lunch', 'breakfast', 'snack',
    'swiggy', 'zomato', 'restaurant', 'cafe', 'mcdonalds',
    'kfc', 'pizza', 'bread omelette', 'biryani', 'hotel',
    'dominos', 'burger king', 'subway', 'eatclub', 'faasos'
  ],
  Groceries: [
    'milk', 'banana', 'blinkit', 'zepto', 'instamart',
    'bigbasket', 'dmart', 'supermarket', 'grocery',
    'vegetable', 'vegetables', 'fruit', 'fresh', 'mart',
    'reliance fresh', 'more'
  ],
  Transport: [
    'metro', 'rapido', 'uber', 'ola', 'auto', 'bus',
    'train', 'flight', 'irctc', 'makemytrip', 'toll',
    'namma yatri', 'redbus', 'transport', 'railway',
    'railways', 'indian railways', 'parking',
    'fastag', 'yatri'
  ],
  Fuel: [
    'indian oil', 'hp petrol', 'bharat petroleum',
    'shell', 'petrol', 'diesel', 'fuel', 'fuels',
    'iocl', 'bpcl', 'hpcl', 'petrol bunk'
  ],
  Utilities: [
    'water', 'electricity', 'internet', 'broadband',
    'bill', 'current bill', 'power', 'cable',
    'bescom', 'tneb', 'eb bill', 'bsnl'
  ],
  Recharges: [
    'recharge', 'jio', 'airtel', 'vi',
    'vodafone', 'dth', 'tata sky',
    'sun direct', 'mobile recharge'
  ],
  Gas: [
    'gas', 'lpg', 'indane', 'hp gas',
    'bharat gas', 'pipeline'
  ],
  'Transfers/Income': [
    'phonepe', 'gpay', 'google pay', 'paytm',
    'credit', 'salary', 'freelance',
    'deposit', 'refund', 'cashback',
    'reward', 'reward points',
    'neft', 'imps', 'rtgs',
    'upi to person', 'upi', 'received'
  ],
  'Bank Charges': [
    'charge', 'charges', 'service charges',
    'sms_chgs', 'uncoll chrg', 'fee',
    'apy', 'gst', 'tax', 'penalty',
    'emi', 'interest', 'processing fee'
  ],
  Shopping: [
    'amazon', 'amazon pay', 'amazon pay later',
    'flipkart', 'myntra', 'ajio',
    'meesho', 'nykaa', 'shopping',
    'mall', 'clothes', 'apparel',
    'shoes', 'delhivery', 'xerox',
    'jiomart', 'croma', 'vijay sales',
    'decathlon', 'ikea'
  ],
  Entertainment: [
    'pvr', 'inox', 'movie',
    'bookmyshow', 'netflix',
    'prime', 'spotify',
    'hotstar', 'sony liv',
    'zee5', 'youtube premium'
  ],
  'Medical Expenses': [
    'hospital', 'clinic', 'pharmacy',
    'medicine', 'apollo', 'medical',
    'doctor', 'medplus',
    '1mg', 'pharmeasy'
  ],
  Education: [
    'school', 'college', 'tuition',
    'fee', 'university',
    'course', 'exam',
    'udemy', 'coursera',
    'byjus', 'unacademy'
  ],
  'Rent/Housing': [
    'rent', 'maintenance',
    'housing', 'tenant',
    'brokerage', 'society'
  ],
  Investments: [
    'mutual fund', 'mf ',
    'angel mf', 'sip',
    'stock', 'groww',
    'zerodha', 'upstox',
    'investment', 'fd',
    'etmoney', 'coin'
  ],
  Insurance: [
    'insurance', 'premium',
    'lic', 'policy',
    'health insurance',
    'car insurance',
    'bike insurance'
  ],
  'Personal Care': [
    'salon', 'spa',
    'haircut', 'beauty',
    'cosmetics', 'grooming',
    'barber'
  ],
  'Cash Withdrawal': [
    'nfs/cash', 'cash wdl',
    'cash withdrawal',
    'atm wdl',
    'atm withdrawal'
  ],
  Donations: [
    'temple', 'church',
    'mosque', 'donation',
    'charity', 'ngo'
  ],
  Taxes: [
    'income tax',
    'property tax',
    'road tax',
    'challan',
    'gst payment'
  ],
  Loans: [
    'loan', 'emi',
    'bajaj finance',
    'home credit',
    'loan repayment'
  ],
  Travel: [
    'hotel', 'oyo',
    'booking.com',
    'airbnb',
    'goibibo',
    'makemytrip'
  ],
  Pets: [
    'pet', 'dog',
    'cat', 'veterinary',
    'pet food'
  ],
  Miscellaneous: []
};

const TRANSACTION_TYPE_RULES = [
  [/\b(nfs\/cash|cash wdl|cash withdrawal|atm wdl|atm withdrawal)\b/i, 'Cash Withdrawal'],
  [/\b(neft|imps|rtgs)\b/i, 'Transfers/Income'],
  [/\b(upi|upi\/dr|upi\/cr|phonepe|gpay|google pay|paytm)\b/i, 'Transfers/Income'],
  [/\b(salary|credit interest|refund|cashback|reward)\b/i, 'Transfers/Income'],
  [/\b(charge|charges|fee|gst|penalty|interest|processing fee)\b/i, 'Bank Charges'],
  [/\b(emi|loan)\b/i, 'Loans'],
  [/\b(pos|debit card|card purchase|visa|mastercard)\b/i, 'Shopping'],
  [/\b(petrol|diesel|fuel|iocl|hpcl|bpcl|shell)\b/i, 'Fuel'],
  [/\b(airtel|jio|vi|recharge)\b/i, 'Recharges']
];

const VALID_CATEGORIES = Object.keys(CATEGORIES);

const hasCashWithdrawalSignal = (desc) => /\b(nfs\/cash|cash wdl|cash withdrawal|atm wdl|atm withdrawal)\b/i.test(desc);

const normalizeDescription = (description = '') => description.toLowerCase().trim().replace(/\s+/g, ' ');

const result = (category, confidence, categorizationSource) => ({
  category,
  confidence,
  needsReview: confidence < 70,
  categorizationSource
});

const normalizeAiCategory = (category) => {
  if (!category || typeof category !== 'string') return 'Others';
  const exact = VALID_CATEGORIES.find(valid => valid.toLowerCase() === category.trim().toLowerCase());
  return exact || 'Others';
};

const parseAiResponse = (text) => {
  const cleaned = text
    .trim()
    .replace(/^```json/i, '')
    .replace(/^```/, '')
    .replace(/```$/, '')
    .trim();
  const parsed = JSON.parse(cleaned);
  return Array.isArray(parsed) ? parsed : parsed.results;
};

const loadCategoryCache = () => {
  let cache = {};
  try {
    if (fs.existsSync(cachePath)) {
      cache = JSON.parse(fs.readFileSync(cachePath, 'utf8'));
    }
  } catch (err) {
    console.error('Failed to load category cache in Node.js categorizer:', err);
  }
  return cache;
};

export const saveCategoryCorrection = (description, category) => {
  const normalizedDesc = normalizeDescription(description);
  if (!normalizedDesc || !category) return;

  const cache = loadCategoryCache();
  cache[normalizedDesc] = category;

  try {
    fs.writeFileSync(cachePath, JSON.stringify(cache, null, 2));
  } catch (err) {
    console.error('Failed to save category correction:', err);
  }
};

export const buildNormalizedSearchableString = (tx) => {
  if (!tx) return '';
  const textValues = [];

  const fields = [
    'description', 'narration', 'merchantName', 'merchant_name', 'merchant',
    'beneficiaryName', 'beneficiary_name', 'beneficiary', 'senderName', 'sender_name', 'sender',
    'receiverName', 'receiver_name', 'receiver', 'upiAppName', 'upi_app_name', 'upi_app',
    'upiId', 'upi_id', 'vpa', 'reference', 'referenceNumber', 'reference_number',
    'transactionRemarks', 'transaction_remarks', 'remarks', 'bankRemarks', 'bank_remarks',
    'paymentGateway', 'payment_gateway', 'type', 'transactionType', 'transaction_type',
    'additionalDetails', 'additional_details'
  ];

  // Try to extract known fields
  for (const field of fields) {
    let val = '';
    if (typeof tx.get === 'function') { // Mongoose document
      val = tx.get(field);
    } else {
      val = tx[field];
    }
    if (val !== undefined && val !== null && val !== '') {
      textValues.push(String(val));
    }
  }

  // Also grab any other string values to be comprehensive
  const keys = typeof tx.toObject === 'function' ? Object.keys(tx.toObject()) : Object.keys(tx);
  const metadataKeys = ['_id', 'user', 'date', 'amount', 'balance', 'confidence', 'needsReview', 'categorizationSource', 'category', 'createdAt', 'updatedAt', '__v'];
  for (const key of keys) {
    if (!fields.includes(key) && !metadataKeys.includes(key)) {
      let val = '';
      if (typeof tx.get === 'function') {
        val = tx.get(key);
      } else {
        val = tx[key];
      }
      if (typeof val === 'string' && val.trim() !== '') {
        textValues.push(val);
      }
    }
  }

  // Combine, lowercase
  let combined = textValues.join(' ').toLowerCase();

  // Remove punctuation and special characters (keep alphanumeric and spaces)
  combined = combined.replace(/[^a-z0-9\s]/g, ' ');

  // Replace multiple spaces with a single space, trim
  combined = combined.replace(/\s+/g, ' ').trim();

  // Remove duplicate words preserving order
  const words = combined.split(' ');
  const uniqueWords = [];
  const seen = new Set();
  for (const word of words) {
    if (word && !seen.has(word)) {
      seen.add(word);
      uniqueWords.push(word);
    }
  }

  return uniqueWords.join(' ');
};

export const categorizeTransactionDetails = (transactionOrDesc, amount) => {
  let searchStr = '';
  let description = '';

  if (transactionOrDesc && typeof transactionOrDesc === 'object') {
    description = transactionOrDesc.description || '';
    searchStr = buildNormalizedSearchableString(transactionOrDesc);
  } else {
    description = String(transactionOrDesc || '');
    searchStr = buildNormalizedSearchableString({ description });
  }

  const numericAmount = Number(amount || 0);

  if (numericAmount > 0) {
    return result('Transfers/Income', 100, 'amount_sign');
  }

  const cache = loadCategoryCache();
  const normalizedDesc = normalizeDescription(description);

  if (cache[normalizedDesc] && cache[normalizedDesc] !== 'Others') {
    const cachedCategory = cache[normalizedDesc];
    if (!(cachedCategory === 'Cash Withdrawal' && !hasCashWithdrawalSignal(searchStr))) {
      return result(cachedCategory, 100, 'cache');
    }
  }

  for (const [pattern, category] of TRANSACTION_TYPE_RULES) {
    if (pattern.test(searchStr)) {
      if (category === 'Transfers/Income' && numericAmount < 0) {
        return result('Others', 45, 'transaction_type');
      }
      return result(category, 95, 'transaction_type');
    }
  }

  for (const [category, keywords] of Object.entries(CATEGORIES)) {
    if (category === 'Transfers/Income' && numericAmount < 0) continue;

    for (const keyword of keywords) {
      const escaped = keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      const pattern = new RegExp(`\\b${escaped}\\b`, 'i');
      if (pattern.test(searchStr)) {
        return result(category, 90, 'merchant_rule');
      }
    }
  }

  if (cache[normalizedDesc] === 'Others') {
    return result('Others', 60, 'cache');
  }

  return result('Others', 40, 'unknown');
};

export const categorizeTransaction = (transactionOrDesc, amount) => {
  return categorizeTransactionDetails(transactionOrDesc, amount).category;
};

export const categorizeTransactionsWithAi = async (transactions) => {
  if (!transactions.length) return transactions;

  const prompt = `You are an Indian bank statement transaction categorizer.

Categorize every transaction into exactly one of these categories:
${VALID_CATEGORIES.join(', ')}

Rules:
- Use the full description, merchant/person name, UPI handle, remarks, and amount sign.
- Positive amounts are usually Transfers/Income unless the description clearly says reversal/refund of a spend.
- Do not classify a UPI row as Cash Withdrawal only because it contains "BRANCH : ATM SERVICE BRANCH".
- Cash Withdrawal only when the description has a real withdrawal signal like ATM WDL, CASH WDL, CASH WITHDRAWAL, or NFS/CASH.
- If it is only a person name or generic QR with no clear purpose, use Others with low confidence.
- Return only valid JSON. No markdown.

Transactions:
${JSON.stringify(transactions.map((tx, index) => ({
    id: index,
    date: tx.date instanceof Date ? tx.date.toISOString().slice(0, 10) : tx.date,
    amount: tx.amount,
    description: tx.description
  })), null, 2)}

Return a JSON object like:
{
  "results": [
    {"id":0,"category":"Food & Dining","confidence":90},
    {"id":1,"category":"Others","confidence":45}
  ]
}`;

  let aiResults = null;

  if (process.env.GROQ_API_KEY) {
    try {
      const client = new Groq({ apiKey: process.env.GROQ_API_KEY });
      const completion = await client.chat.completions.create({
        model: 'llama-3.3-70b-versatile',
        messages: [{ role: 'user', content: prompt }],
        temperature: 0
      });
      aiResults = parseAiResponse(completion.choices[0].message.content);
    } catch (error) {
      console.error('Groq batch categorization failed:', error.message);
    }
  }

  if (!aiResults && process.env.OPENAI_API_KEY) {
    try {
      const client = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
      const completion = await client.chat.completions.create({
        model: 'gpt-4o-mini',
        messages: [{ role: 'user', content: prompt }],
        temperature: 0,
        response_format: { type: 'json_object' }
      });
      aiResults = parseAiResponse(completion.choices[0].message.content);
    } catch (error) {
      console.error('OpenAI batch categorization failed:', error.message);
    }
  }

  if (!aiResults && process.env.GEMINI_API_KEY) {
    try {
      const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);
      const model = genAI.getGenerativeModel({ model: 'gemini-1.5-flash' });
      const response = await model.generateContent(prompt);
      aiResults = parseAiResponse(response.response.text());
    } catch (error) {
      console.error('Gemini batch categorization failed:', error.message);
    }
  }

  if (!Array.isArray(aiResults)) {
    return transactions;
  }

  const byId = new Map(aiResults.map(item => [Number(item.id), item]));

  return transactions.map((tx, index) => {
    const ai = byId.get(index);
    if (!ai) return tx;

    const category = normalizeAiCategory(ai.category);
    const confidence = Math.max(0, Math.min(100, Number(ai.confidence) || (category === 'Others' ? 45 : 80)));

    return {
      ...tx,
      category,
      confidence,
      needsReview: confidence < 70,
      categorizationSource: 'ai'
    };
  });
};
