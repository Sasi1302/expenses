import React, { useState, useEffect } from 'react';
import { getTransactions, updateTransactionCategory } from '../api';
import UploadModal from '../components/UploadModal';
import { Receipt, Upload } from 'lucide-react';

const CATEGORIES = ['Food & Dining', 'Groceries', 'Transport', 'Utilities', 'Recharges', 'Shopping', 'Fuel', 'Entertainment', 'Medical Expenses', 'Education', 'Rent/Housing', 'Investments', 'Insurance', 'Personal Care', 'Transfers/Income', 'Bank Charges', 'Cash Withdrawal', 'Others'];

const Transactions = () => {
  const [transactions, setTransactions] = useState([]);
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [loading, setLoading] = useState(true);

  const fetchTransactions = async () => {
    setLoading(true);
    try {
      const { data } = await getTransactions();
      setTransactions(data);
    } catch (error) {
      console.error('Failed to fetch transactions', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTransactions();
  }, []);

  const handleCategoryChange = async (id, newCategory) => {
    try {
      await updateTransactionCategory(id, newCategory);
      setTransactions(transactions.map(t => 
        t._id === id ? { ...t, category: newCategory } : t
      ));
    } catch (error) {
      console.error('Failed to update category', error);
    }
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <h1>Transactions</h1>
        <button className="btn btn-primary" onClick={() => setIsUploadOpen(true)}>
          <Upload size={18} />
          Upload Statement
        </button>
      </div>

      <div className="glass-card">
        {loading ? (
          <p>Loading transactions...</p>
        ) : transactions.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '3rem 0', color: 'var(--text-secondary)' }}>
            <Receipt size={48} style={{ marginBottom: '1rem', opacity: 0.5 }} />
            <h3>No transactions found</h3>
            <p>Upload a bank statement to get started.</p>
          </div>
        ) : (
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Description</th>
                  <th>Amount</th>
                  <th>Category</th>
                  <th>Confidence</th>
                </tr>
              </thead>
              <tbody>
                {[...transactions].sort((a, b) => new Date(a.date) - new Date(b.date)).map((t) => (
                  <tr key={t._id}>
                    <td>{new Date(t.date).toLocaleDateString()}</td>
                    <td>{t.description}</td>
                    <td style={{ color: t.amount >= 0 ? 'var(--success)' : 'var(--text-primary)' }}>
                      ₹{Math.abs(t.amount).toFixed(2)}
                    </td>
                    <td>
                      <select 
                        value={t.category} 
                        onChange={(e) => handleCategoryChange(t._id, e.target.value)}
                        style={{ border: 'none', background: 'rgba(255,255,255,0.05)', cursor: 'pointer' }}
                      >
                        {CATEGORIES.map(c => (
                          <option key={c} value={c}>{c}</option>
                        ))}
                      </select>
                    </td>
                    <td>
                      <span className={`badge ${t.needsReview ? 'badge-warning' : 'badge-success'}`}>
                        {typeof t.confidence === 'number' ? `${t.confidence}%` : 'Review'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <UploadModal 
        isOpen={isUploadOpen} 
        onClose={() => setIsUploadOpen(false)} 
        onUploadSuccess={fetchTransactions}
      />
    </div>
  );
};

export default Transactions;
