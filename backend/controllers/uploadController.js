import fs from 'fs';
import { ObjectId } from 'mongodb';
import Transaction from '../models/Transaction.js';
import { categorizeTransactionDetails, categorizeTransactionsWithAi } from '../utils/categorizer.js';

export const uploadStatement = async (req, res) => {
  if (!req.file) {
    return res.status(400).json({ error: 'No file uploaded' });
  }

  const results = [];
  const fileExt = req.file.originalname.split('.').pop().toLowerCase();
  
  if (fileExt === 'pdf') {
    try {
      // Create built-in FormData and fetch the Python microservice
      const fileBuffer = fs.readFileSync(req.file.path);
      const fileBlob = new Blob([fileBuffer], { type: 'application/pdf' });
      const formData = new FormData();
      formData.append('file', fileBlob, req.file.originalname);

      // Delete local physical file immediately
      fs.unlinkSync(req.file.path);

      const response = await fetch('http://localhost:8000/parse', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorText = await response.text();
        return res.status(500).json({ error: 'FastAPI microservice failed to parse statement', details: errorText });
      }

      const parseResult = await response.json();
      const { bank, transactions, summary, insights } = parseResult;

      // Save transactions to database
      const finalResults = transactions.map(t => ({
        user: new ObjectId(req.user._id),
        date: new Date(t.date),
        description: t.description,
        amount: t.amount,
        category: t.category,
        confidence: t.confidence || 40,
        needsReview: t.needsReview ?? true,
        categorizationSource: t.categorizationSource || 'unknown',
        createdAt: new Date(),
        updatedAt: new Date()
      }));

      const transactionsCollection = Transaction.getCollection();
      await transactionsCollection.deleteMany({ user: new ObjectId(req.user._id) });
      if (finalResults.length > 0) {
        await transactionsCollection.insertMany(finalResults);
      }

      // Return confirmation message and the parsed data
      return res.status(200).json({ 
        message: `Successfully parsed ${finalResults.length} transactions from ${bank}.`,
        bank,
        transactions: finalResults,
        summary,
        insights
      });
    } catch (error) {
      console.error(error);
      return res.status(500).json({ error: 'Failed to parse PDF statement via microservice', details: error.message });
    }
  } else {
    try {
      const rows = parseCsvRows(fs.readFileSync(req.file.path, 'utf8'));
      fs.unlinkSync(req.file.path);

      const parsedTransactions = await categorizeTransactionsWithAi(
        parseTransactionsFromCsvRows(rows, req.user._id)
      );

      if (parsedTransactions.length > 0) {
        const transactionsCollection = Transaction.getCollection();
        await transactionsCollection.deleteMany({ user: new ObjectId(req.user._id) });
        await transactionsCollection.insertMany(parsedTransactions);
      }

      return res.status(200).json({
        message: `Successfully uploaded and categorized ${parsedTransactions.length} transactions.`
      });
    } catch (error) {
      console.error(error);
      return res.status(500).json({ error: 'Error parsing CSV file', details: error.message });
    }
  }
};

export const parseCsvRows = (text) => {
  const rows = [];
  let row = [];
  let value = '';
  let inQuotes = false;

  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];
    const next = text[i + 1];

    if (char === '"' && inQuotes && next === '"') {
      value += '"';
      i += 1;
    } else if (char === '"') {
      inQuotes = !inQuotes;
    } else if (char === ',' && !inQuotes) {
      row.push(value.trim());
      value = '';
    } else if ((char === '\n' || char === '\r') && !inQuotes) {
      if (char === '\r' && next === '\n') i += 1;
      row.push(value.trim());
      if (row.some(cell => cell !== '')) rows.push(row);
      row = [];
      value = '';
    } else {
      value += char;
    }
  }

  if (value || row.length) {
    row.push(value.trim());
    if (row.some(cell => cell !== '')) rows.push(row);
  }

  return rows;
};

const cleanNumber = (value) => {
  if (!value) return null;
  const cleaned = value
    .toString()
    .replace(/\b(cr|dr)\b/gi, '')
    .replace(/[^0-9.-]/g, '')
    .trim();
  if (!cleaned || cleaned === '.' || cleaned === '-' || cleaned === '#.#0.0') return null;
  const parsed = Number.parseFloat(cleaned);
  return Number.isFinite(parsed) ? parsed : null;
};

const parseStatementDate = (value) => {
  if (!value) return null;
  const trimmed = value.trim();
  const ddmmyyyy = trimmed.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
  if (ddmmyyyy) {
    const [, day, month, year] = ddmmyyyy;
    return new Date(Date.UTC(Number(year), Number(month) - 1, Number(day)));
  }

  const parsed = new Date(trimmed);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
};

export const parseTransactionsFromCsvRows = (rows, userId) => {
  const headerIndex = rows.findIndex(row =>
    row.some(cell => ['txn date', 'date', 'transaction date'].includes(cell.trim().toLowerCase())) &&
    row.some(cell => ['description', 'narration', 'remarks', 'particulars'].includes(cell.trim().toLowerCase()))
  );

  if (headerIndex === -1) {
    throw new Error('Transaction header not found in CSV.');
  }

  const headers = rows[headerIndex].map(cell => cell.trim().toLowerCase());
  const indexOfAny = (names) => headers.findIndex(header => names.includes(header));

  const dateIndex = indexOfAny(['txn date', 'date', 'transaction date', 'value date']);
  const descIndex = indexOfAny(['description', 'narration', 'remarks', 'particulars', 'details', 'transaction remarks']);
  const amountIndex = indexOfAny(['amount', 'transaction amount']);
  const debitIndex = indexOfAny(['debit amount', 'debit', 'withdrawal', 'withdrawals', 'dr']);
  const creditIndex = indexOfAny(['credit amount', 'credit', 'deposit', 'deposits', 'cr']);
  const balanceIndex = indexOfAny(['balance', 'closing balance']);

  const rawTransactions = [];
  for (const row of rows.slice(headerIndex + 1)) {
    const firstCell = (row[0] || '').trim().toLowerCase();
    if (!row.some(cell => cell.trim()) || firstCell === 'total') break;

    const date = parseStatementDate(row[dateIndex]);
    const description = (row[descIndex] || '').trim();
    if (!date || !description) continue;

    const debit = debitIndex >= 0 ? cleanNumber(row[debitIndex]) : null;
    const credit = creditIndex >= 0 ? cleanNumber(row[creditIndex]) : null;
    const directAmount = amountIndex >= 0 ? cleanNumber(row[amountIndex]) : null;
    const balance = balanceIndex >= 0 ? cleanNumber(row[balanceIndex]) : null;
    const hasDebitMarker = debitIndex >= 0 && Boolean((row[debitIndex] || '').trim());
    const hasCreditMarker = creditIndex >= 0 && Boolean((row[creditIndex] || '').trim());

    const extraFields = {};
    headers.forEach((h, idx) => {
      if (idx !== dateIndex && idx !== descIndex && idx !== amountIndex &&
          idx !== debitIndex && idx !== creditIndex && idx !== balanceIndex) {
        const val = (row[idx] || '').trim();
        if (val) {
          const cleanHeader = h.replace(/[^a-zA-Z0-9]/g, '_').toLowerCase();
          extraFields[cleanHeader] = val;
        }
      }
    });

    rawTransactions.push({
      date,
      description,
      debit,
      credit,
      directAmount,
      balance,
      hasDebitMarker,
      hasCreditMarker,
      ...extraFields
    });
  }

  return rawTransactions.map((tx, index) => {
    let amount = null;

    if (tx.directAmount !== null) amount = tx.directAmount;
    else if (tx.debit !== null) amount = -Math.abs(tx.debit);
    else if (tx.credit !== null) amount = Math.abs(tx.credit);

    if ((amount === null || amount === 0) && index > 0 && tx.balance !== null && rawTransactions[index - 1].balance !== null) {
      const delta = Number((tx.balance - rawTransactions[index - 1].balance).toFixed(2));
      if (delta !== 0) amount = delta;
    }

    if (amount === null || amount === 0) return null;

    const categoryDetails = categorizeTransactionDetails(tx, amount);
    
    // Construct the clean transaction object to save to DB
    return {
      user: new ObjectId(userId),
      date: tx.date,
      description: tx.description,
      amount,
      confidence: 40,
      needsReview: true,
      categorizationSource: 'unknown',
      createdAt: new Date(),
      updatedAt: new Date(),
      ...categoryDetails
    };
  }).filter(Boolean);
};
