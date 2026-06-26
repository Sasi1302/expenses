import Transaction from '../models/Transaction.js';
import { saveCategoryCorrection } from '../utils/categorizer.js';

export const updateCategory = async (req, res) => {
  try {
    const { category } = req.body;
    const transaction = await Transaction.findOneAndUpdate(
      { _id: req.params.id, user: req.user.id },
      {
        category,
        confidence: 100,
        needsReview: false,
        categorizationSource: 'user_correction'
      },
      { new: true }
    );
    
    if (!transaction) {
      return res.status(404).json({ error: 'Transaction not found' });
    }

    saveCategoryCorrection(transaction.description, category);
    
    res.json(transaction);
  } catch (error) {
    res.status(500).json({ error: 'Failed to update category' });
  }
};
