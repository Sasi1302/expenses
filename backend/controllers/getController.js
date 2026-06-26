import Transaction from '../models/Transaction.js';

export const getTransactions = async (req, res) => {
  try {
    const transactions = await Transaction.find({ user: req.user.id }).sort({ date: -1 });
    res.json(transactions);
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch transactions' });
  }
};

export const getDashboardData = async (req, res) => {
  try {
    const transactions = await Transaction.find({ user: req.user.id });
    
    let totalIncome = 0;
    let totalExpense = 0;
    const categoryDataMap = {};
    const monthlyDataMap = {};

    transactions.forEach(t => {
      const monthYear = `${t.date.toLocaleString('default', { month: 'short' })} ${t.date.getFullYear()}`;
      
      // Initialize maps
      if (!monthlyDataMap[monthYear]) monthlyDataMap[monthYear] = { income: 0, expense: 0 };

      // Determine if income based on sign AND description if sign is positive.
      if (t.amount > 0) {
        totalIncome += t.amount;
        monthlyDataMap[monthYear].income += t.amount;
      } else {
        const absAmount = Math.abs(t.amount);
        totalExpense += absAmount;
        if (!categoryDataMap[t.category]) categoryDataMap[t.category] = 0;
        categoryDataMap[t.category] += absAmount;
        monthlyDataMap[monthYear].expense += absAmount;
      }
    });

    const categoryData = Object.keys(categoryDataMap)
      .map(name => ({ name, value: categoryDataMap[name] }))
      .filter(item => item.value > 0);

    const monthlyData = Object.keys(monthlyDataMap)
      .map(name => ({
        name,
        income: monthlyDataMap[name].income,
        expense: monthlyDataMap[name].expense
      }));

    res.json({
      totalIncome,
      totalExpense,
      categoryData,
      monthlyData
    });
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Failed to load dashboard data' });
  }
};
