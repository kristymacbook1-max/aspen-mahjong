import React, { useEffect, useState, useCallback } from 'react';
import { useSocket } from '../context/SocketContext';
import './PatternSuggestions.css';

function PatternSuggestions({ enabled, onToggle }) {
  const {
    gameState,
    patternSuggestions,
    requestPatternSuggestions
  } = useSocket();

  const [isExpanded, setIsExpanded] = useState(true);
  const [isLoading, setIsLoading] = useState(false);

  // Get hand length safely
  const getHandLength = useCallback(() => {
    if (!gameState?.players || gameState.yourPlayerIndex === undefined) return 0;
    const player = gameState.players[gameState.yourPlayerIndex];
    return player?.hand?.length || 0;
  }, [gameState]);

  const handLength = getHandLength();
  const phase = gameState?.phase;

  // Request suggestions when enabled and hand/phase changes
  useEffect(() => {
    if (!enabled || !phase || !gameState) return;

    // Show during charleston, charleston_vote, and playing phases
    if (phase === 'playing' || phase === 'charleston' || phase === 'charleston_vote') {
      setIsLoading(true);
      const timer = setTimeout(() => {
        requestPatternSuggestions();
      }, 300);
      return () => clearTimeout(timer);
    }
  }, [enabled, phase, handLength, requestPatternSuggestions, gameState]);

  // Clear loading when suggestions arrive
  useEffect(() => {
    if (patternSuggestions) {
      setIsLoading(false);
    }
  }, [patternSuggestions]);

  // Request immediately when enabled changes to true
  useEffect(() => {
    if (enabled && gameState && handLength > 0) {
      setIsLoading(true);
      requestPatternSuggestions();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled]);

  // Show toggle button in bot games
  const isBotGame = gameState?.players?.some(p => p.isBot);

  // Debug logging
  console.log('PatternSuggestions render:', {
    hasGameState: !!gameState,
    isBotGame,
    enabled,
    players: gameState?.players?.map(p => ({ name: p.name, isBot: p.isBot }))
  });

  // Don't show anything if not a bot game (and we know gameState exists)
  if (gameState && !isBotGame) {
    console.log('PatternSuggestions: Not a bot game, returning null');
    return null;
  }

  // Don't show if game hasn't started yet
  if (!gameState) {
    return null;
  }

  // Show just the toggle button when not enabled
  if (!enabled) {
    return (
      <div className="pattern-suggestions-toggle">
        <button
          className="practice-mode-btn"
          onClick={onToggle}
          title="Show pattern suggestions"
        >
          📊 Practice Mode
        </button>
      </div>
    );
  }

  const handleRefresh = () => {
    setIsLoading(true);
    requestPatternSuggestions();
  };

  return (
    <div className={`pattern-suggestions ${isExpanded ? 'expanded' : 'collapsed'}`}>
      <div className="suggestions-header">
        <div
          className="header-content"
          onClick={() => setIsExpanded(!isExpanded)}
        >
          <span className="suggestions-title">
            📊 Practice Mode ({patternSuggestions?.cardYear || '2025'} Card)
          </span>
          <span className="toggle-icon">{isExpanded ? '▼' : '▶'}</span>
        </div>
        <button
          className="close-practice-btn"
          onClick={onToggle}
          title="Turn off practice mode"
        >
          ✕
        </button>
      </div>

      {isExpanded && (
        <div className="suggestions-content">
          {isLoading && !patternSuggestions?.suggestions ? (
            <p className="no-suggestions">Analyzing your hand...</p>
          ) : !patternSuggestions?.suggestions || patternSuggestions.suggestions.length === 0 ? (
            <p className="no-suggestions">No patterns found. Try refreshing.</p>
          ) : (
            <div className="suggestions-list">
              {patternSuggestions.suggestions.map((suggestion, index) => (
                <div
                  key={suggestion.pattern.id}
                  className={`suggestion-item rank-${index + 1}`}
                >
                  <div className="suggestion-rank">#{index + 1}</div>
                  <div className="suggestion-info">
                    <div className="suggestion-name">
                      {suggestion.pattern.name}
                      <span className="suggestion-category">
                        ({suggestion.pattern.category})
                      </span>
                    </div>
                    <div className="suggestion-description">
                      {suggestion.pattern.description}
                    </div>
                    <div className="suggestion-stats">
                      <span className="stat progress">
                        Progress: {suggestion.odds}%
                      </span>
                      <span className="stat needed">
                        Need {suggestion.tilesNeeded} tiles
                      </span>
                      <span className="stat value">
                        {suggestion.pattern.value} pts
                        {suggestion.pattern.concealed && ' (C)'}
                      </span>
                    </div>
                    <div className="progress-bar">
                      <div
                        className="progress-fill"
                        style={{ width: `${suggestion.odds}%` }}
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
          <button
            className="refresh-btn"
            onClick={handleRefresh}
            disabled={isLoading}
          >
            {isLoading ? 'Analyzing...' : 'Refresh Suggestions'}
          </button>
        </div>
      )}
    </div>
  );
}

export default PatternSuggestions;
