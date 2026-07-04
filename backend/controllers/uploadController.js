import fs from 'fs';
import { ObjectId } from 'mongodb';
import Transaction from '../models/Transaction.js';


export const uploadStatement = async (req, res) => {
  if (!req.file) {
    return res.status(400).json({ error: 'No file uploaded' });
  }

  const results = [];
  const fileExt = req.file.originalname.split('.').pop().toLowerCase();
  const allowedExts = ['pdf', 'csv', 'xls', 'xlsx'];
  
  if (allowedExts.includes(fileExt)) {
    try {
      // Create built-in FormData and fetch the Python microservice
      const fileBuffer = fs.readFileSync(req.file.path);
      
      let mimeType = 'application/octet-stream';
      if (fileExt === 'pdf') mimeType = 'application/pdf';
      else if (fileExt === 'csv') mimeType = 'text/csv';
      else if (fileExt === 'xls') mimeType = 'application/vnd.ms-excel';
      else if (fileExt === 'xlsx') mimeType = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';

      const fileBlob = new Blob([fileBuffer], { type: mimeType });
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
      return res.status(500).json({ error: 'Failed to parse statement via microservice', details: error.message });
    }
  } else {
    // Unsupported file type
    fs.unlinkSync(req.file.path);
    return res.status(400).json({ error: 'Unsupported file type. Please upload a PDF, CSV, or Excel file.' });
  }
};


