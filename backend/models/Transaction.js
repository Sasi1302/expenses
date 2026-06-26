import mongoose from 'mongoose';

const transactionSchema = new mongoose.Schema({
  user: {
    type: mongoose.Schema.Types.ObjectId,
    required: true,
    ref: 'User'
  },
  date: { 
    type: Date, 
    required: true 
  },
  description: { 
    type: String, 
    required: true 
  },
  amount: { 
    type: Number, 
    required: true 
  },
  category: { 
    type: String, 
    required: true 
  },
  confidence: {
    type: Number,
    default: 40
  },
  needsReview: {
    type: Boolean,
    default: true
  },
  categorizationSource: {
    type: String,
    default: 'unknown'
  }
}, {
  timestamps: true
});

const Transaction = mongoose.model('Transaction', transactionSchema);
export default Transaction;
