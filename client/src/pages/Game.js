import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useSocket } from '../context/SocketContext';
import GameBoard from '../components/GameBoard';
import './Game.css';

function Game() {
  const { gameId: urlGameId } = useParams();
  const navigate = useNavigate();
  const { gameState, gameId, error, leaveGame, waitingRoom } = useSocket();
  const [copied, setCopied] = useState(false);

  // Join game if URL has gameId but we haven't joined yet
  useEffect(() => {
    if (urlGameId && !gameId) {
      // This would typically trigger a join flow
      // For now, redirect to lobby if no active game
    }
  }, [urlGameId, gameId]);

  const handleLeaveGame = () => {
    if (window.confirm('Are you sure you want to leave the game?')) {
      leaveGame();
      navigate('/lobby');
    }
  };

  // Show error state
  if (error) {
    return (
      <div className="game-page">
        <div className="game-error">
          <h2>Error</h2>
          <p>{error}</p>
          <button className="btn btn-primary" onClick={() => navigate('/lobby')}>
            Back to Lobby
          </button>
        </div>
      </div>
    );
  }

  // Copy game code to clipboard
  const copyGameCode = () => {
    navigator.clipboard.writeText(waitingRoom?.gameId || gameId);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Show waiting room if waiting for players
  if (waitingRoom) {
    return (
      <div className="game-page">
        <div className="waiting-room">
          <h2>Waiting for Players</h2>
          <div className="waiting-info">
            <p>Share this code with your friends:</p>
            <div className="game-code-display">
              <span className="code">{waitingRoom.gameId}</span>
              <button className="btn btn-small" onClick={copyGameCode}>
                {copied ? 'Copied!' : 'Copy'}
              </button>
            </div>
          </div>
          <div className="player-status">
            <div className="player-count">
              <span className="count">{waitingRoom.playersJoined}</span>
              <span className="separator">/</span>
              <span className="total">{waitingRoom.playersNeeded}</span>
            </div>
            <p>Players joined</p>
          </div>
          <div className="waiting-players">
            {waitingRoom.gameState?.players.map((player, index) => (
              <div key={index} className="waiting-player">
                <span className="player-avatar">{player.name?.charAt(0).toUpperCase()}</span>
                <span className="player-name">{player.name}</span>
              </div>
            ))}
          </div>
          <div className="loading-spinner"></div>
          <p className="waiting-hint">Game will start automatically when all players join</p>
          <button className="btn btn-secondary" onClick={handleLeaveGame}>
            Cancel
          </button>
        </div>
      </div>
    );
  }

  // Show loading if waiting for game
  if (!gameState) {
    return (
      <div className="game-page">
        <div className="game-loading">
          <div className="loading-spinner"></div>
          <p>Setting up game...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="game-page">
      <div className="game-header">
        <div className="game-info">
          <span className="game-code">Game: {gameId}</span>
          <span className="game-phase">Phase: {gameState.phase}</span>
        </div>
        <button className="btn btn-secondary btn-small" onClick={handleLeaveGame}>
          Leave Game
        </button>
      </div>

      <GameBoard />

      {/* Game finished actions */}
      {gameState.phase === 'finished' && (
        <div className="game-finished-actions">
          <button className="btn btn-primary" onClick={() => navigate('/lobby')}>
            Back to Lobby
          </button>
        </div>
      )}
    </div>
  );
}

export default Game;
