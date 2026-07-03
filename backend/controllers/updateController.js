import { ObjectId } from 'mongodb';
import Transaction from '../models/Transaction.js';
import { saveCategoryCorrection } from '../utils/categorizer.js';

export const updateCategory = async (req, res) => {
  try {
    const { category } = req.body;
    const transactionsCollection = Transaction.getCollection();
    
    const result = await transactionsCollection.findOneAndUpdate(
      { _id: new ObjectId(req.params.id), user: new ObjectId(req.user._id) },
      {
        $set: {
          category,
          confidence: 100,
          needsReview: false,
          categorizationSource: 'user_correction'
        }
      },
      { returnDocument: 'after' } // native driver equivalent of { new: true }
    );
    
    // In native driver, the updated document is in result.value (or just result in newer versions)
    const transaction = result.value || result;

    if (!transaction) {
      return res.status(404).json({ error: 'Transaction not found' });
    }

    saveCategoryCorrection(transaction.description, category);
    
    res.json(transaction);
  } catch (error) {
    res.status(500).json({ error: 'Failed to update category' });
  }
};
