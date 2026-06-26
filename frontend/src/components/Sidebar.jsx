import React, { useContext } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { LayoutDashboard, Receipt, Wallet, LogOut, User, X } from 'lucide-react';
import { AuthContext } from '../context/AuthContext';

const Sidebar = ({ isOpen, onClose }) => {
  const { user, logout } = useContext(AuthContext);
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <>
      {/* Mobile Backdrop Overlay */}
      {isOpen && (
        <div 
          className="md:hidden fixed inset-0 bg-black/60 backdrop-blur-sm z-40 transition-opacity"
          onClick={onClose}
        />
      )}

      {/* Sidebar Drawer */}
      <div className={`
        fixed inset-y-0 left-0 z-50 w-[260px] bg-[var(--bg-secondary)] border-r border-[var(--border)] p-6
        flex flex-col justify-between transform transition-transform duration-300 ease-in-out
        md:relative md:translate-x-0
        ${isOpen ? 'translate-x-0' : '-translate-x-full'}
      `}>
        <div className="flex flex-col gap-8">
          <div className="flex items-center justify-between">
            <div className="logo">
              <Wallet size={28} />
              <span>ExpenseAI</span>
            </div>
            {/* Mobile Close Button */}
            <button onClick={onClose} className="md:hidden text-[var(--text-secondary)] hover:text-white transition-colors">
              <X size={24} />
            </button>
          </div>
          
          <div className="nav-links">
            <NavLink 
              to="/" 
              onClick={onClose}
              className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            >
              <LayoutDashboard size={20} />
              Dashboard
            </NavLink>
            <NavLink 
              to="/transactions" 
              onClick={onClose}
              className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            >
              <Receipt size={20} />
              Transactions
            </NavLink>
          </div>
        </div>
        
        {user && (
          <div className="mt-auto pt-4 border-t border-[var(--border)]">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-full bg-indigo-500/20 flex items-center justify-center">
                <User size={20} className="text-[var(--accent-primary)]" />
              </div>
              <div className="overflow-hidden">
                <p className="font-semibold text-sm whitespace-nowrap overflow-hidden text-ellipsis text-white">{user.name}</p>
                <p className="text-xs text-[var(--text-secondary)] whitespace-nowrap overflow-hidden text-ellipsis">{user.email}</p>
              </div>
            </div>
            <button 
              onClick={handleLogout}
              className="w-full flex items-center justify-center gap-2 p-3 rounded-xl bg-red-500/10 text-[var(--danger)] border border-red-500/20 cursor-pointer font-medium hover:bg-red-500/20 transition-colors"
            >
              <LogOut size={18} />
              Sign Out
            </button>
          </div>
        )}
      </div>
    </>
  );
};

export default Sidebar;
