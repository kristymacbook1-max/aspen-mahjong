import React from 'react';
import Tile from './Tile';
import './PlayerArea.css';

function PlayerArea({ player, position, onJokerClick }) {
  if (!player) return null;

  const isHorizontal = position === 'left' || position === 'right';

  // Check if a tile in an exposure is a joker
  const isJoker = (tile) => tile.type === 'joker';

  // Handle click on a joker in an exposure
  const handleJokerClick = (exposureIndex, jokerIndex) => {
    if (onJokerClick) {
      onJokerClick(player.id, exposureIndex, jokerIndex);
    }
  };

  return (
    <div className={`player-area player-${position} ${player.isCurrentPlayer ? 'current-turn' : ''}`}>
      <div className="player-info-bar">
        <span className="player-name">{player.name}</span>
        <span className="player-wind">{player.wind}</span>
        {player.isBot && <span className="bot-badge">BOT</span>}
      </div>

      {/* Exposures */}
      {player.exposures && player.exposures.length > 0 && (
        <div className={`player-exposures ${isHorizontal ? 'horizontal' : ''}`}>
          {player.exposures.map((exposure, expIndex) => (
            <div key={expIndex} className="exposure-group">
              {exposure.tiles.map((tile, tileIndex) => (
                <div
                  key={`exp-${tile.id || tileIndex}`}
                  className={`exposure-tile-wrapper ${isJoker(tile) ? 'has-joker' : ''}`}
                  onClick={isJoker(tile) ? () => handleJokerClick(expIndex, tileIndex) : undefined}
                  title={isJoker(tile) ? 'Click to request joker exchange' : ''}
                >
                  <Tile
                    tile={tile}
                    small
                  />
                  {isJoker(tile) && onJokerClick && (
                    <span className="joker-exchange-hint">Exchange</span>
                  )}
                </div>
              ))}
            </div>
          ))}
        </div>
      )}

      {/* Hand (always hidden for opponents - this is PlayerArea which is for other players) */}
      <div className={`player-hand ${isHorizontal ? 'horizontal' : ''}`}>
        {player.hand && player.hand.map((tile, index) => (
          <Tile
            key={tile.id || `hidden-${index}`}
            tile={tile}
            hidden={true}
            small
          />
        ))}
      </div>

      {/* Turn indicator */}
      {player.isCurrentPlayer && (
        <div className="turn-indicator-dot"></div>
      )}
    </div>
  );
}

export default PlayerArea;
