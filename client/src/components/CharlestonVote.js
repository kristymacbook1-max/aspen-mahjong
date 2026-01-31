import React, { useState } from 'react';
import { useSocket } from '../context/SocketContext';
import './CharlestonVote.css';

function CharlestonVote() {
  const { gameState, submitCharlestonVote } = useSocket();
  const [voted, setVoted] = useState(false);

  if (gameState?.phase !== 'charleston_vote') {
    return null;
  }

  const handleVote = (stopCharleston) => {
    submitCharlestonVote(stopCharleston);
    setVoted(true);
  };

  return (
    <div className="charleston-vote-overlay">
      <div className="charleston-vote-dialog">
        <h2>First Charleston Complete!</h2>

        <p className="vote-description">
          The first Charleston (Right, Across, Left) is complete.
          Would you like to continue with a second Charleston?
        </p>

        {voted ? (
          <div className="vote-waiting">
            <div className="loading-spinner"></div>
            <p>Waiting for other players to vote...</p>
            <p className="vote-count">
              {gameState.charlestonVoteCount || 0} / 4 votes received
            </p>
          </div>
        ) : (
          <div className="vote-buttons">
            <button
              className="btn btn-primary btn-large"
              onClick={() => handleVote(false)}
            >
              Continue Charleston
            </button>
            <button
              className="btn btn-secondary btn-large"
              onClick={() => handleVote(true)}
            >
              Stop & Start Playing
            </button>
          </div>
        )}

        <p className="vote-note">
          Note: If any player votes to stop, the Charleston will end and the game will begin.
        </p>
      </div>
    </div>
  );
}

export default CharlestonVote;
