import React from 'react';
import { useAuth } from '../context/AuthContext';
import './Profile.css';

function Profile() {
  const { user } = useAuth();

  if (!user) {
    return (
      <div className="profile-page">
        <p>Please log in to view your profile.</p>
      </div>
    );
  }

  const stats = user.stats || {};

  const winRate = stats.games_played > 0
    ? ((stats.games_won / stats.games_played) * 100).toFixed(1)
    : 0;

  return (
    <div className="profile-page">
      <div className="profile-header">
        <div className="profile-avatar">
          {user.displayName?.charAt(0).toUpperCase() || user.username?.charAt(0).toUpperCase()}
        </div>
        <div className="profile-info">
          <h1>{user.displayName || user.username}</h1>
          <p className="profile-username">@{user.username}</p>
        </div>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-value">{stats.games_played || 0}</div>
          <div className="stat-label">Games Played</div>
        </div>

        <div className="stat-card">
          <div className="stat-value">{stats.games_won || 0}</div>
          <div className="stat-label">Wins</div>
        </div>

        <div className="stat-card">
          <div className="stat-value">{winRate}%</div>
          <div className="stat-label">Win Rate</div>
        </div>

        <div className="stat-card">
          <div className="stat-value">{stats.wall_games || 0}</div>
          <div className="stat-label">Wall Games</div>
        </div>

        <div className="stat-card">
          <div className="stat-value">{stats.rating || 1000}</div>
          <div className="stat-label">Rating</div>
        </div>

        <div className="stat-card">
          <div className="stat-value">{stats.total_points || 0}</div>
          <div className="stat-label">Total Points</div>
        </div>
      </div>

      <div className="profile-section">
        <h2>Recent Games</h2>
        <p className="empty-state">No games played yet. Start playing to see your history!</p>
      </div>
    </div>
  );
}

export default Profile;
