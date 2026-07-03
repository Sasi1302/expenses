import axios from 'axios';

const API_URL = '/api';

// Configure axios to include cookies with requests
axios.defaults.withCredentials = true;

export const uploadStatement = (file) => {
  const formData = new FormData();
  formData.append('file', file);
  console.log(formData, "formData")
  return axios.post(`${API_URL}/upload-statement`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
};

export const getTransactions = () => {
  return axios.get(`${API_URL}/transactions`);
};

export const updateTransactionCategory = (id, category) => {
  return axios.put(`${API_URL}/transaction/${id}/category`, { category });
};

export const getDashboardData = () => {
  return axios.get(`${API_URL}/dashboard`);
};
