import React, { useState, useEffect } from 'react';
import { useSocket } from '../context/SocketContext';
import Tile from './Tile';
import './Charleston.css';

const CHARLESTON_NAMES = {
  first_right: 'First Right',
  first_across: 'First Across',
  first_left: 'First Left',
  second_left: 'Second Left',
  second_across: 'Second Across',
  second_right: 'Second Right',
  courtesy: 'Courtesy Pass'
};

const PASS_DIRECTIONS = {
  first_right: '→',
  first_across: '↑',
  first_left: '←',
  second_left: '←',
  second_across: '↑',
  second_right: '→',
  courtesy: '↔'
};

function Charleston() {
  const {
    gameState,
    selectedTiles,
    toggleTileSelection,
    submitCharlestonPass,
    getCurrentPlayer,
    reorderHand
  } = useSocket();

  const [submitted, setSubmitted] = useState(false);
  const [arrangeMode, setArrangeMode] = useState(false); // Default OFF - select tiles for passing
  const [swapFromIndex, setSwapFromIndex] = useState(null);

  const currentPlayer = getCurrentPlayer();

  // Toggle arrange mode
  const toggleArrangeMode = () => {
    setArrangeMode(!arrangeMode);
    setSwapFromIndex(null);
  };

  // Handle tile click in arrange mode
  const handleArrangeModeClick = (index) => {
    if (swapFromIndex === null) {
      setSwapFromIndex(index);
    } else if (swapFromIndex === index) {
      setSwapFromIndex(null);
    } else {
      reorderHand(swapFromIndex, index);
      setSwapFromIndex(null);
    }
  };
  const charlestonPhase = gameState?.charlestonPhase;

  // Reset submitted state when phase changes
  useEffect(() => {
    setSubmitted(false);
  }, [charlestonPhase]);

  const handleTileClick = (tile) => {
    if (submitted) return;
    // Don't allow selecting more than 3 tiles (unless deselecting)
    if (selectedTiles.length >= 3 && !selectedTiles.includes(tile.id)) {
      return;
    }
    toggleTileSelection(tile.id);
  };

  const handleSubmit = () => {
    if (selectedTiles.length !== 3) {
      alert('Please select exactly 3 tiles to pass');
      return;
    }
    submitCharlestonPass(selectedTiles);
    setSubmitted(true);
  };

  if (!charlestonPhase || charlestonPhase === 'done') {
    return null;
  }

  return (
    <div className="charleston-overlay">
      <div className="charleston-dialog">
        <h2>Charleston - {CHARLESTON_NAMES[charlestonPhase]}</h2>

        <div className="charleston-info">
          <span className="pass-direction">
            Pass {PASS_DIRECTIONS[charlestonPhase]}
          </span>
          <p>Select 3 tiles to pass</p>
        </div>

        {submitted ? (
          <div className="charleston-waiting">
            <div className="loading-spinner"></div>
            <p>Waiting for other players...</p>
          </div>
        ) : (
          <>
            <div className="charleston-hand">
              <div className="charleston-hand-header">
                <p className="hand-label">
                  {arrangeMode ? 'Click tiles to rearrange:' : 'Your hand (click tiles to select):'}
                </p>
                <button
                  className={`btn btn-small ${arrangeMode ? 'btn-active' : 'btn-secondary'}`}
                  onClick={toggleArrangeMode}
                >
                  {arrangeMode ? '✓ Arrange ON' : '↔ Arrange'}
                </button>
              </div>
              {arrangeMode && (
                <p className="arrange-hint-charleston">
                  {swapFromIndex === null ? 'Click a tile to move it' : 'Click where to place it'}
                </p>
              )}
              <div className="hand-tiles">
                {currentPlayer?.hand.map((tile, index) => {
                  const isSwapSource = arrangeMode && swapFromIndex === index;
                  return (
                    <Tile
                      key={tile.id}
                      tile={tile}
                      selected={arrangeMode ? isSwapSource : selectedTiles.includes(tile.id)}
                      onClick={arrangeMode ? () => handleArrangeModeClick(index) : () => handleTileClick(tile)}
                      className={isSwapSource ? 'swap-source' : ''}
                    />
                  );
                })}
              </div>
            </div>

            <div className="charleston-selection">
              <p className="selection-label">
                Selected ({Math.min(selectedTiles.length, 3)}/3):
              </p>
              <div className="selected-tiles">
                {selectedTiles.slice(0, 3).map((tileId) => {
                  const tile = currentPlayer?.hand.find(t => t.id === tileId);
                  return tile ? (
                    <Tile
                      key={tile.id}
                      tile={tile}
                      onClick={() => handleTileClick(tile)}
                    />
                  ) : null;
                })}
                {/* Empty slots */}
                {[...Array(Math.max(0, 3 - selectedTiles.length))].map((_, i) => (
                  <div key={`empty-${i}`} className="tile-slot"></div>
                ))}
              </div>
            </div>

            <button
              className="btn btn-primary btn-large"
              onClick={handleSubmit}
              disabled={selectedTiles.length !== 3}
            >
              Pass Tiles
            </button>
          </>
        )}
      </div>
    </div>
  );
}

export default Charleston;
