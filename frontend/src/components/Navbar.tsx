import React from 'react';
import { useAuth } from '../contexts/AuthContext';
import './Navbar.css';

interface NavbarProps {
  toggleSidebar: () => void;
}

const Navbar: React.FC<NavbarProps> = ({ toggleSidebar }) => {
  const { user, signOut } = useAuth();

  const handleSignOut = async () => {
    await signOut();
  };

  return (
    <nav className="navbar">
      <div className="navbar-left">
        <button className="menu-button" onClick={toggleSidebar}>
          ☰
        </button>
        <h1 className="navbar-title">ReconcileAI</h1>
      </div>
      <div className="navbar-right">
        <div className="user-info">
          <span className="user-email">{user?.email}</span>
          <span className="user-role">{user?.role}</span>
        </div>
        <button className="logout-button" onClick={handleSignOut}>
          Logout
        </button>
      </div>
    </nav>
  );
};

export default Navbar;
