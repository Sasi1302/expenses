import express from 'express';
import cors from 'cors';
import cookieParser from 'cookie-parser';
import dotenv from 'dotenv';
import apiRoutes from './routes/api.js';
import connectDB from './config/db.js';

dotenv.config();

const app = express();
const PORT = process.env.PORT || 5000;

app.use(cors({
  origin: 'http://localhost:5173', // Allow your frontend to connect
  credentials: true, // This allows cookies to be sent back and forth!
}));
app.use(express.json());
app.use(cookieParser());

// Set up routes
app.use('/api', apiRoutes);

// Connect to MongoDB
await connectDB();

app.listen(PORT, () => {
  console.log(`Server is running on port ${PORT}`);
});
