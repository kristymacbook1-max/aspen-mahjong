import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import './Navbar.css';

function Navbar() {
  const { user, isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  return (
    <nav className="navbar">
      <div className="navbar-brand">
        <Link to="/" className="navbar-logo">
          <span className="logo-icon">🀄</span>
          <span className="logo-text">Mahjong</span>
        </Link>
      </div>

      <div className="navbar-links">
        <Link to="/lobby" className="nav-link">Play</Link>
        <Link to="/resources" className="nav-link">Resources</Link>
        {isAuthenticated && !user?.isGuest && (
          <>
            <Link to="/groups" className="nav-link">Groups</Link>
            <Link to="/profile" className="nav-link">Stats</Link>
          </>
        )}
      </div>

      <div className="navbar-auth">
        {isAuthenticated ? (
          <div className="user-menu">
            <span className="user-name">
              {user?.displayName || user?.username}
              {user?.isGuest && ' (Guest)'}
            </span>
            <button onClick={handleLogout} className="btn btn-secondary btn-small">
              Logout
            </button>
          </div>
        ) : (
          <div className="auth-buttons">
            <Link to="/login" className="btn btn-secondary btn-small">Login</Link>
            <Link to="/register" className="btn btn-primary btn-small">Sign Up</Link>
          </div>
        )}
      </div>
    </nav>
  );
}

export default Navbar;
