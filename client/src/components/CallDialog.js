import React, { useState, useEffect } from 'react';
import { useSocket } from '../context/SocketContext';
import Tile from './Tile';
import './CallDialog.css';

// All possible call types in American Mah Jongg
const ALL_CALLS = [
  { type: 'pung', name: 'Pung', description: '3 of a kind', tilesNeeded: 2 },
  { type: 'kong', name: 'Kong', description: '4 of a kind', tilesNeeded: 3 },
  { type: 'quint', name: 'Quint', description: '5 of a kind', tilesNeeded: 4 },
  { type: 'mahjong', name: 'Mah Jongg', description: 'Winning hand!', tilesNeeded: 0 }
];

function CallDialog() {
  const {
    callOpportunity,
    callError,
    selectedTiles,
    toggleTileSelection,
    callTile,
    passCall,
    clearSelection,
    getCurrentPlayer,
    exchangeBlankForDiscard
  } = useSocket();

  const [selectedCall, setSelectedCall] = useState(null);
  const [localError, setLocalError] = useState(null);
  const [selectedBlankId, setSelectedBlankId] = useState(null);
  const currentPlayer = getCurrentPlayer();

  // Find blank tiles in player's hand
  const blankTiles = currentPlayer?.hand.filter(tile => tile.type === 'blank') || [];

  // Combine local error and server error
  const error = localError || callError;

  // Reset state when call opportunity changes
  useEffect(() => {
    setSelectedCall(null);
    setLocalError(null);
    setSelectedBlankId(null);
    clearSelection();
  }, [callOpportunity, clearSelection]);

  const handleCallSelect = (callType) => {
    setSelectedCall(callType);
    setSelectedBlankId(null);
    setLocalError(null);
    clearSelection();
  };

  const handleBlankSelect = (blankId) => {
    setSelectedBlankId(blankId);
    setSelectedCall(null);
    setLocalError(null);
    clearSelection();
  };

  const handleUseBlank = () => {
    if (!selectedBlankId) {
      setLocalError('Please select a blank tile first');
      return;
    }
    exchangeBlankForDiscard(selectedBlankId);
  };

  const handleConfirmCall = () => {
    if (!selectedCall) {
      setLocalError('Please select a call type first');
      return;
    }

    const callInfo = ALL_CALLS.find(c => c.type === selectedCall);

    // For Mah Jongg, no tiles needed from hand (uses whole hand)
    if (selectedCall === 'mahjong') {
      callTile(selectedCall, []);
      return;
    }

    // Validate tile selection count
    if (selectedTiles.length !== callInfo.tilesNeeded) {
      setLocalError(`Please select exactly ${callInfo.tilesNeeded} tiles from your hand for a ${callInfo.name}`);
      return;
    }

    // Send to server - server will validate if it's actually a valid call
    callTile(selectedCall, selectedTiles);
  };

  if (!callOpportunity) return null;

  const discardTile = callOpportunity.tile;
  const selectedCallInfo = ALL_CALLS.find(c => c.type === selectedCall);

  return (
    <div className="call-dialog-overlay">
      <div className="call-dialog">
        <div className="call-dialog-header">
          <h3>Call Opportunity</h3>
          <button className="btn-cancel" onClick={passCall} title="Pass on this tile">
            ✕ Pass
          </button>
        </div>

        <div className="discarded-tile">
          <p>Discarded tile:</p>
          <Tile tile={discardTile} />
          <p className="discarded-by">
            by {callOpportunity.discardedByName || 'opponent'}
          </p>
        </div>

        {error && (
          <div className="call-error">
            {error}
          </div>
        )}

        <div className="call-options">
          {ALL_CALLS.map((call) => (
            <button
              key={call.type}
              className={`call-option ${selectedCall === call.type ? 'selected' : ''}`}
              onClick={() => handleCallSelect(call.type)}
            >
              <span className="call-name">{call.name}</span>
              <span className="call-desc">{call.description}</span>
            </button>
          ))}
        </div>

        {/* Blank tile exchange option */}
        {blankTiles.length > 0 && (
          <div className="blank-exchange-section">
            <div className="blank-divider">
              <span>OR</span>
            </div>
            <div className="blank-option">
              <p className="blank-label">Use a Blank Tile to take this discard:</p>
              <div className="blank-tiles">
                {blankTiles.map((tile) => (
                  <Tile
                    key={tile.id}
                    tile={tile}
                    selected={selectedBlankId === tile.id}
                    onClick={() => handleBlankSelect(tile.id)}
                  />
                ))}
              </div>
              {selectedBlankId && (
                <button
                  className="btn btn-success"
                  onClick={handleUseBlank}
                >
                  Use Blank for Discard
                </button>
              )}
            </div>
          </div>
        )}

        {selectedCall && selectedCall !== 'mahjong' && (
          <div className="call-selection">
            <p>Select {selectedCallInfo?.tilesNeeded} tiles from your hand to combine with the discarded tile:</p>
            <div className="hand-tiles-mini">
              {currentPlayer?.hand.map((tile) => (
                <Tile
                  key={tile.id}
                  tile={tile}
                  small
                  selected={selectedTiles.includes(tile.id)}
                  onClick={() => toggleTileSelection(tile.id)}
                />
              ))}
            </div>

            <p className="selection-count">
              Selected: {selectedTiles.length} / {selectedCallInfo?.tilesNeeded}
            </p>
          </div>
        )}

        {selectedCall === 'mahjong' && (
          <div className="call-selection">
            <p className="mahjong-info">
              Calling Mah Jongg will use the discarded tile to complete your winning hand.
              Make sure your hand is valid before calling!
            </p>
          </div>
        )}

        <div className="call-actions">
          <button
            className="btn btn-primary"
            onClick={handleConfirmCall}
            disabled={!selectedCall}
          >
            {selectedCall ? `Call ${selectedCallInfo?.name}` : 'Select a Call'}
          </button>
          <button className="btn btn-secondary" onClick={passCall}>
            Pass
          </button>
        </div>
      </div>
    </div>
  );
}

export default CallDialog;
