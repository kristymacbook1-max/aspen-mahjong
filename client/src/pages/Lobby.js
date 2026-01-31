import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useSocket } from '../context/SocketContext';
import './Lobby.css';

function Lobby() {
  const { user, isAuthenticated, guestLogin } = useAuth();
  const { startGameWithBots, joinGame, createGame, connected } = useSocket();
  const navigate = useNavigate();

  const [guestName, setGuestName] = useState('');
  const [joinCode, setJoinCode] = useState('');
  const [showJoinModal, setShowJoinModal] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [botDifficulty, setBotDifficulty] = useState('medium');
  const [humanPlayerCount, setHumanPlayerCount] = useState(1);
  const [includeBlanks, setIncludeBlanks] = useState(false);
  const [practiceMode, setPracticeMode] = useState(false);
  const [loading, setLoading] = useState(false);

  const handlePlayWithBots = async () => {
    if (!connected) {
      alert('Connecting to server... please try again in a moment.');
      return;
    }

    setLoading(true);

    // Use entered name, user name, or generate a guest name
    const playerName = guestName.trim() || user?.displayName || user?.username || `Guest_${Math.random().toString(36).substring(7)}`;

    console.log('Starting game with bots, player:', playerName, 'includeBlanks:', includeBlanks, 'practiceMode:', practiceMode);
    startGameWithBots(playerName, { includeBlanks, botDifficulty, practiceMode });
    navigate('/game');
  };

  const handleJoinGame = () => {
    if (!joinCode.trim()) return;
    if (!connected) {
      alert('Connecting to server... please try again in a moment.');
      return;
    }

    const playerName = user?.displayName || user?.username || 'Guest';
    joinGame(joinCode.trim(), playerName);
    setShowJoinModal(false);
    navigate(`/game/${joinCode.trim()}`);
  };

  const handleCreateGame = (waitForPlayers = 4) => {
    if (!connected) {
      alert('Connecting to server... please try again in a moment.');
      return;
    }

    const playerName = user?.displayName || user?.username || 'Guest';
    const withBots = waitForPlayers < 4; // Add bots if not waiting for 4 humans
    createGame(playerName, { private: true, waitForPlayers, includeBlanks, withBots });
    setShowCreateModal(false);
    navigate('/game');
  };

  return (
    <div className="lobby-page">
      <h1>Aspen Ladies Mahjong</h1>

      {/* Connection status */}
      <div className={`connection-status ${connected ? 'connected' : 'disconnected'}`}>
        {connected ? '🟢 Connected to server' : '🔴 Connecting to server...'}
      </div>

      {!isAuthenticated && (
        <div className="guest-name-input">
          <input
            type="text"
            placeholder="Enter your name (optional)"
            value={guestName}
            onChange={(e) => setGuestName(e.target.value)}
            maxLength={20}
          />
        </div>
      )}

      <div className="lobby-options">
        <div className="lobby-card main-card">
          <div className="card-icon">🀄</div>
          <h3>Start Playing</h3>
          <p>Play solo with bots or create a room for friends to join</p>

          <div className="game-settings">
            <div className="player-count-section">
              <label>Players:</label>
              <div className="player-count-selector">
                {[1, 2, 3, 4].map(count => (
                  <button
                    key={count}
                    className={`count-btn ${humanPlayerCount === count ? 'selected' : ''}`}
                    onClick={() => setHumanPlayerCount(count)}
                  >
                    {count}
                    <span className="bot-info">
                      {count < 4 ? `+${4 - count} Bots` : 'No Bots'}
                    </span>
                  </button>
                ))}
              </div>
            </div>

            <div className="difficulty-select">
              <label>Bot Difficulty:</label>
              <select
                value={botDifficulty}
                onChange={(e) => setBotDifficulty(e.target.value)}
              >
                <option value="easy">Easy</option>
                <option value="medium">Medium</option>
                <option value="hard">Hard</option>
              </select>
            </div>

            <div className="blanks-toggle">
              <label className="toggle-label">
                <input
                  type="checkbox"
                  checked={includeBlanks}
                  onChange={(e) => setIncludeBlanks(e.target.checked)}
                />
                <span className="toggle-text">Use Blank Tiles</span>
                <span className="toggle-hint">(Exchange for any discard)</span>
              </label>
            </div>

            <div className="practice-toggle">
              <label className="toggle-label practice">
                <input
                  type="checkbox"
                  checked={practiceMode}
                  onChange={(e) => setPracticeMode(e.target.checked)}
                />
                <span className="toggle-text">Practice Mode</span>
                <span className="toggle-hint">(Show best patterns for your hand)</span>
              </label>
            </div>
          </div>

          <div className="game-buttons">
            <button
              className="btn btn-primary btn-large"
              onClick={handlePlayWithBots}
              disabled={loading || !connected || humanPlayerCount > 1}
            >
              {loading ? 'Starting...' : 'Start Game Now'}
            </button>

            {humanPlayerCount > 1 && (
              <button
                className="btn btn-secondary btn-large"
                onClick={() => handleCreateGame(humanPlayerCount)}
                disabled={!connected}
              >
                Create Room (Share code with friends)
              </button>
            )}
          </div>

          <div className="join-section">
            <p className="join-text">Have a room code?</p>
            <button
              className="btn btn-link"
              onClick={() => setShowJoinModal(true)}
              disabled={!connected}
            >
              Join Existing Room
            </button>
          </div>
        </div>
      </div>

      {/* Join Game Modal */}
      {showJoinModal && (
        <div className="modal-overlay" onClick={() => setShowJoinModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Join Game</h2>
              <button
                className="modal-close"
                onClick={() => setShowJoinModal(false)}
              >
                ×
              </button>
            </div>

            <div className="input-group">
              <label>Game Code</label>
              <input
                type="text"
                placeholder="Enter game code"
                value={joinCode}
                onChange={(e) => setJoinCode(e.target.value.toUpperCase())}
                maxLength={8}
              />
            </div>

            <button
              className="btn btn-primary btn-full"
              onClick={handleJoinGame}
              disabled={!joinCode.trim()}
            >
              Join Game
            </button>
          </div>
        </div>
      )}

      {/* Create Game Modal */}
      {showCreateModal && (
        <div className="modal-overlay" onClick={() => setShowCreateModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Create Room</h2>
              <button
                className="modal-close"
                onClick={() => setShowCreateModal(false)}
              >
                ×
              </button>
            </div>

            <p className="modal-description">
              Create a room and choose how many human players to wait for.
              Remaining spots will be filled with bots.
            </p>

            <div className="input-group">
              <label>Number of Human Players</label>
              <div className="player-count-selector">
                {[1, 2, 3, 4].map(count => (
                  <button
                    key={count}
                    className={`count-btn ${humanPlayerCount === count ? 'selected' : ''}`}
                    onClick={() => setHumanPlayerCount(count)}
                  >
                    {count} {count === 1 ? 'Player' : 'Players'}
                    <span className="bot-info">
                      {count < 4 ? `+ ${4 - count} Bots` : 'No Bots'}
                    </span>
                  </button>
                ))}
              </div>
            </div>

            <button className="btn btn-primary btn-full" onClick={() => handleCreateGame(humanPlayerCount)}>
              Create Room {humanPlayerCount < 4 ? `(Wait for ${humanPlayerCount})` : '(Wait for 4)'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default Lobby;
