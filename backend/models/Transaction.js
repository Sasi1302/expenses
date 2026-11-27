import { getDb } from '../config/db.js';

const Transaction = {
  getCollection: () => getDb().collection('transactions')
};

export default Transaction;
