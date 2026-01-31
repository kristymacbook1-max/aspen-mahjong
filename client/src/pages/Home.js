import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import './Home.css';

function Home() {
  const { isAuthenticated } = useAuth();

  return (
    <div className="home-page">
      <section className="hero">
        <div className="hero-content">
          <h1>Play American Mah Jongg Online</h1>
          <p className="hero-subtitle">
            Challenge yourself against intelligent bots or play with friends from anywhere
          </p>

          <div className="hero-actions">
            <Link to="/lobby" className="btn btn-primary btn-large">
              Play Now
            </Link>
            {!isAuthenticated && (
              <Link to="/register" className="btn btn-secondary btn-large">
                Create Account
              </Link>
            )}
          </div>
        </div>

        <div className="hero-tiles">
          <span className="floating-tile">🀄</span>
          <span className="floating-tile">🀅</span>
          <span className="floating-tile">🀆</span>
          <span className="floating-tile">🀙</span>
        </div>
      </section>

      <section className="features">
        <div className="feature-card">
          <div className="feature-icon">🎮</div>
          <h3>Play Online</h3>
          <ul>
            <li>Multi-level intelligent bots</li>
            <li>Practice mode to improve</li>
            <li>Play with friends remotely</li>
            <li>Video chat built-in</li>
          </ul>
        </div>

        <div className="feature-card">
          <div className="feature-icon">📊</div>
          <h3>Track Progress</h3>
          <ul>
            <li>Wins, losses, and wall games</li>
            <li>Average game duration</li>
            <li>Rating history</li>
            <li>Detailed statistics</li>
          </ul>
        </div>

        <div className="feature-card">
          <div className="feature-icon">👥</div>
          <h3>Play with Groups</h3>
          <ul>
            <li>Create or join groups</li>
            <li>Schedule recurring games</li>
            <li>Invite friends easily</li>
            <li>Organize tournaments</li>
          </ul>
        </div>
      </section>

      <section className="how-to-play">
        <h2>How It Works</h2>
        <div className="steps">
          <div className="step">
            <div className="step-number">1</div>
            <h4>Choose Your Game</h4>
            <p>Play solo with bots or create a room for friends</p>
          </div>
          <div className="step">
            <div className="step-number">2</div>
            <h4>Charleston</h4>
            <p>Pass tiles to start - 3 right, 3 across, 3 left</p>
          </div>
          <div className="step">
            <div className="step-number">3</div>
            <h4>Build Your Hand</h4>
            <p>Draw, discard, and call tiles to complete patterns</p>
          </div>
          <div className="step">
            <div className="step-number">4</div>
            <h4>Mah Jongg!</h4>
            <p>Complete your hand to win the game</p>
          </div>
        </div>
      </section>
    </div>
  );
}

export default Home;
