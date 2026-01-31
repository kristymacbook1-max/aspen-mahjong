import React, { useState } from 'react';
import { useSocket } from '../context/SocketContext';
import Tile from './Tile';
import './JokerExchangeDialog.css';

function JokerExchangeDialog() {
  const {
    jokerExchangeRequest,
    jokerExchangePending,
    jokerExchangeResult,
    respondToJokerExchange,
    cancelJokerExchange,
    clearJokerExchangeResult
  } = useSocket();

  // Show incoming request dialog
  if (jokerExchangeRequest) {
    return (
      <div className="joker-exchange-overlay">
        <div className="joker-exchange-dialog">
          <div className="joker-exchange-header">
            <h3>Joker Exchange Request</h3>
          </div>
          <div className="joker-exchange-content">
            <p><strong>{jokerExchangeRequest.requesterName}</strong> wants to exchange:</p>
            <div className="exchange-tiles">
              <div className="exchange-tile-group">
                <span className="tile-label">Their tile:</span>
                <Tile tile={jokerExchangeRequest.offerTile} />
              </div>
              <span className="exchange-arrow">for your</span>
              <div className="exchange-tile-group">
                <span className="tile-label">Your Joker</span>
                <Tile tile={{ type: 'joker' }} />
              </div>
            </div>
            <p className="exchange-question">Do you accept this exchange?</p>
          </div>
          <div className="joker-exchange-actions">
            <button
              className="btn btn-primary"
              onClick={() => respondToJokerExchange(true)}
            >
              Accept
            </button>
            <button
              className="btn btn-secondary"
              onClick={() => respondToJokerExchange(false)}
            >
              Decline
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Show pending request indicator
  if (jokerExchangePending) {
    return (
      <div className="joker-exchange-pending">
        <div className="pending-content">
          <span className="pending-spinner"></span>
          <span>Waiting for response...</span>
          <button
            className="btn btn-small btn-secondary"
            onClick={cancelJokerExchange}
          >
            Cancel
          </button>
        </div>
      </div>
    );
  }

  // Show result notification
  if (jokerExchangeResult) {
    return (
      <div className={`joker-exchange-result ${jokerExchangeResult.success ? 'success' : 'failed'}`}>
        <span>{jokerExchangeResult.message}</span>
        <button className="btn-close" onClick={clearJokerExchangeResult}>OK</button>
      </div>
    );
  }

  return null;
}

export default JokerExchangeDialog;
