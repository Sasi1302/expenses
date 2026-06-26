import React, { useState } from 'react';
import { UploadCloud, X, Loader } from 'lucide-react';
import { uploadStatement } from '../api';

const UploadModal = ({ isOpen, onClose, onUploadSuccess }) => {
  const [file, setFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState('');

  if (!isOpen) return null;

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile && (selectedFile.type === 'text/csv' || selectedFile.type === 'application/pdf' || selectedFile.name.endsWith('.csv') || selectedFile.name.endsWith('.pdf'))) {
      console.log(selectedFile,"selectedFile")
      setFile(selectedFile);
      setError('');
    } else {
      setFile(null);
      setError('Please select a valid CSV or PDF file.');
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    setIsUploading(true);
    setError('');

    try {
      await uploadStatement(file);
      onUploadSuccess();
      onClose();
    } catch (err) {
      const apiError = err.response?.data?.details || err.response?.data?.error;
      setError(apiError ? `Error: ${apiError}` : 'Failed to upload file. Please try again.');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content glass-card" style={{ position: 'relative' }}>
        <button 
          onClick={onClose}
          style={{ position: 'absolute', top: '1.5rem', right: '1.5rem', background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer' }}
        >
          <X size={24} />
        </button>
        
        <h2 style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <UploadCloud className="text-accent" /> Upload Statement
        </h2>

        <div style={{ marginBottom: '1.5rem' }}>
          <input 
            type="file" 
            accept=".csv,.pdf" 
            onChange={handleFileChange} 
            style={{ display: 'none' }}
            id="file-upload"
          />
          <label htmlFor="file-upload" className="btn btn-secondary" style={{ display: 'inline-block', cursor: 'pointer' }}>
            Select CSV or PDF File
          </label>
          {error && <p style={{ color: 'var(--danger)', marginTop: '0.5rem', fontSize: '0.9rem' }}>{error}</p>}
          {file && !error && <p style={{ color: 'var(--success)', marginTop: '0.5rem', fontSize: '0.9rem' }}>Selected: {file.name}</p>}
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem' }}>
          <button className="btn btn-secondary" onClick={onClose} disabled={isUploading}>
            Cancel
          </button>
          <button className="btn btn-primary" onClick={handleUpload} disabled={!file || isUploading}>
            {isUploading ? <Loader size={18} className="spin" /> : 'Upload'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default UploadModal;
