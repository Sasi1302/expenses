import { MongoClient } from 'mongodb';

let db;

const connectDB = async () => {
  try {
    const client = new MongoClient(process.env.MONGODB_URI || 'mongodb://localhost:27017');
    await client.connect();
    
    // Set the specific database
    db = client.db('expense_analyzer');
    console.log('Connected to raw MongoDB database');

    // Create indexes (like unique email)
    await db.collection('users').createIndex({ email: 1 }, { unique: true });

  } catch (error) {
    console.error(`Error connecting to MongoDB: ${error.message}`);
    process.exit(1);
  }
};

export const getDb = () => {
  if (!db) {
    throw new Error('Database not initialized');
  }
  return db;
};

export default connectDB;
