import bcrypt from 'bcryptjs';
import { getDb } from '../config/db.js';

export const User = {
  getCollection: () => getDb().collection('users'),
  
  matchPassword: async (enteredPassword, hashedPassword) => {
    return await bcrypt.compare(enteredPassword, hashedPassword);
  },

  hashPassword: async (password) => {
    const salt = await bcrypt.genSalt(10);
    return await bcrypt.hash(password, salt);
  }
};

export default User;
