# Expense Analyzer MVP

A full-stack web application to upload bank statement CSVs, automatically categorize transactions, and view a detailed dashboard with beautiful charts.

## Features
- **CSV Upload**: Upload standard bank statement CSVs (Date, Description, Amount).
- **Auto Categorization**: Keywords (e.g., SWIGGY, AMAZON) are automatically matched to categories (Food, Shopping).
- **Premium UI**: Built with React, Vite, and custom CSS for a beautiful glassmorphism dark-mode aesthetic.
- **Charts**: Interactive Recharts integration for Dashboard KPIs.
- **Editable Transactions**: Update categories inline from the Transactions page.

## Tech Stack
- **Frontend**: React, Vite, React Router, Recharts, Axios, Lucide Icons.
- **Backend**: Node.js, Express, Mongoose, Multer, csv-parser.
- **Database**: MongoDB

## Setup Instructions

### Prerequisites
- Node.js (v18+)
- MongoDB running locally or on a cloud cluster (e.g., MongoDB Atlas)

### 1. Start the Backend
1. Open a terminal and navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Ensure MongoDB is running (the default URI is `mongodb://localhost:27017/expense_analyzer`). You can modify this in `backend/.env`.
4. Start the server:
   ```bash
   node server.js
   ```

### 2. Start the Frontend
1. Open a new terminal and navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the Vite development server:
   ```bash
   npm run dev
   ```
4. Open the displayed local URL (usually `http://localhost:5173`) in your browser.

## Testing with Sample Data
A `sample_statement.csv` file is provided in the root of the project.
1. Go to the **Transactions** page.
2. Click **Upload CSV** and select `sample_statement.csv`.
3. Check the auto-categorized results in the table.
4. Go to the **Dashboard** to see the Recharts visual summaries.
