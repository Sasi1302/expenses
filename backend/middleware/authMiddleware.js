import jwt from 'jsonwebtoken';
import { ObjectId } from 'mongodb';
import User from '../models/User.js';

export const protect = async (req, res, next) => {
  let token;

  if (req.cookies && req.cookies.jwt) {
    try {
      // Get token from cookie
      token = req.cookies.jwt;

      // Verify token
      const decoded = jwt.verify(token, process.env.JWT_SECRET || 'fallback_secret');

      // Get user from the token and attach to request
      const usersCollection = User.getCollection();
      const user = await usersCollection.findOne({ _id: new ObjectId(decoded.id) });
      
      if (user) {
        delete user.password; // Manually remove password
        req.user = user;
        next();
      } else {
        res.status(401).json({ error: 'Not authorized, user not found' });
      }
    } catch (error) {
      res.status(401).json({ error: 'Not authorized, token failed' });
    }
  } else if (!token) {
    res.status(401).json({ error: 'Not authorized, no token' });
  }
};
