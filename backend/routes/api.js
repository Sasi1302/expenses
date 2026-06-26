import express from 'express';
import multer from 'multer';

// Import auth and middleware
import { registerUser, loginUser, getMe } from '../controllers/authController.js';
import { protect } from '../middleware/authMiddleware.js';

// Import our modular controllers
import { uploadStatement } from '../controllers/uploadController.js';
import { getTransactions, getDashboardData } from '../controllers/getController.js';
import { updateCategory } from '../controllers/updateController.js';

const router = express.Router();

// Setup Multer for file upload
const upload = multer({ dest: 'uploads/' });

// Auth Routes
router.post('/auth/register', registerUser);
router.post('/auth/login', loginUser);
router.get('/auth/me', protect, getMe);

// Protected POST Routes
router.post('/upload-statement', protect, upload.single('file'), uploadStatement);

// Protected GET Routes
router.get('/transactions', protect, getTransactions);
router.get('/dashboard', protect, getDashboardData);

// Protected PUT Routes
router.put('/transaction/:id/category', protect, updateCategory);

export default router;
