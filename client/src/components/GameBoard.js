import React, { useMemo, useState, useEffect } from 'react';
import { useSocket } from '../context/SocketContext';
import Tile from './Tile';
import PlayerArea from './PlayerArea';
import Charleston from './Charleston';
import CharlestonVote from './CharlestonVote';
import CallDialog from './CallDialog';
import ChatBox from './ChatBox';
import VideoChat from './VideoChat';
import JokerExchangeDialog from './JokerExchangeDialog';
import PatternSuggestions from './PatternSuggestions';
import './GameBoard.css';

function GameBoard() {
  const {
    gameState,
    selectedTiles,
    callOpportunity,
    drawnTile,
    toggleTileSelection,
    discardTile,
    drawTile,
    isMyTurn,
    getCurrentPlayer,
    reorderHand,
    clearDrawnTile,
    requestJokerExchange,
    jokerExchangePending,
    socketId
  } = useSocket();

  const [dragIndex, setDragIndex] = useState(null);
  const [jokerExchangeMode, setJokerExchangeMode] = useState(null); // { targetPlayerId, exposureIndex, jokerIndex }
  const [practiceMode, setPracticeMode] = useState(false);

  const currentPlayer = getCurrentPlayer();
  const myTurn = isMyTurn();

  // Sync practice mode with game options when game starts
  useEffect(() => {
    if (gameState?.options?.practiceMode) {
      setPracticeMode(true);
    }
  }, [gameState?.options?.practiceMode]);

  // Toggle practice mode on/off
  const togglePracticeMode = () => {
    setPracticeMode(prev => !prev);
  };

  // Get players in correct positions relative to current player
  const positionedPlayers = useMemo(() => {
    if (!gameState) return [];

    const myIndex = gameState.yourPlayerIndex;
    const positions = ['bottom', 'right', 'top', 'left'];

    return gameState.players.map((player, index) => {
      // Calculate relative position
      const relativeIndex = (index - myIndex + 4) % 4;
      return {
        ...player,
        position: positions[relativeIndex],
        isCurrentPlayer: index === gameState.currentPlayerIndex
      };
    });
  }, [gameState]);

  // Check if in Charleston phase
  const isCharleston = gameState?.phase === 'charleston';

  // Handle tile click
  const handleTileClick = (tile) => {
    toggleTileSelection(tile.id);
  };

  // Handle tile double-click (discard)
  const handleTileDoubleClick = (tile) => {
    if (myTurn && gameState?.phase === 'playing' && currentPlayer?.hand.length === 14) {
      discardTile(tile.id);
    }
  };

  // State for arrange mode - when on, clicking tiles swaps them instead of selecting
  const [arrangeMode, setArrangeMode] = useState(false);
  const [swapFromIndex, setSwapFromIndex] = useState(null);

  // Toggle arrange mode
  const toggleArrangeMode = () => {
    setArrangeMode(!arrangeMode);
    setSwapFromIndex(null);
  };

  // Handle tile click in arrange mode
  const handleArrangeModeClick = (index) => {
    if (swapFromIndex === null) {
      // First click - select tile to move
      setSwapFromIndex(index);
    } else if (swapFromIndex === index) {
      // Clicked same tile - cancel swap
      setSwapFromIndex(null);
    } else {
      // Second click - swap tiles
      reorderHand(swapFromIndex, index);
      setSwapFromIndex(null);
    }
  };

  // Handle draw
  const handleDraw = () => {
    if (myTurn && currentPlayer?.hand.length === 13) {
      drawTile();
    }
  };

  // Calculate total tiles in exposures
  const getTotalExposedTiles = () => {
    if (!currentPlayer?.exposures) return 0;
    return currentPlayer.exposures.reduce((total, exp) => total + exp.tiles.length, 0);
  };

  const totalExposed = getTotalExposedTiles();

  // A complete Mah Jongg hand has 14 tiles (hand + exposures)
  // At rest (waiting to draw), hand size = 14 - exposures - 1 = 13 - exposures
  // After drawing or calling, hand size = 14 - exposures, need to discard
  const restingHandSize = 13 - totalExposed;
  const activeHandSize = 14 - totalExposed; // Hand size when you need to discard

  // You can discard if it's your turn, playing phase, hand equals active size, and 1 tile selected
  const canDiscard = myTurn &&
    gameState?.phase === 'playing' &&
    currentPlayer?.hand.length === activeHandSize &&
    selectedTiles.length === 1;

  // You can draw if it's your turn, playing phase, and hand is at resting size
  const canDraw = myTurn &&
    gameState?.phase === 'playing' &&
    currentPlayer?.hand.length === restingHandSize;

  // Handle clicking on a joker in another player's exposure
  const handleJokerClick = (targetPlayerId, exposureIndex, jokerIndex) => {
    // Don't allow if there's already a pending exchange
    if (jokerExchangePending) return;

    // Store the joker info, will need to select a tile from hand to offer
    setJokerExchangeMode({ targetPlayerId, exposureIndex, jokerIndex });
  };

  // Handle selecting a tile to offer for joker exchange
  const handleOfferTileForJoker = (tileId) => {
    if (jokerExchangeMode) {
      requestJokerExchange(
        jokerExchangeMode.targetPlayerId,
        jokerExchangeMode.exposureIndex,
        jokerExchangeMode.jokerIndex,
        tileId
      );
      setJokerExchangeMode(null);
    }
  };

  // Cancel joker exchange mode
  const cancelJokerExchangeMode = () => {
    setJokerExchangeMode(null);
  };

  // Get the natural tile type of an exposure to know what tile can be exchanged
  const getExposureNaturalTile = (exposure) => {
    return exposure?.tiles?.find(t => t.type !== 'joker');
  };

  // Check if a tile matches the exposure for joker exchange
  const tileMatchesExposure = (tile, exposure) => {
    const naturalTile = getExposureNaturalTile(exposure);
    if (!naturalTile) return false;
    return tile.type === naturalTile.type && tile.value === naturalTile.value;
  };

  // Get matching tiles in hand for current joker exchange mode
  const getMatchingTilesForExchange = () => {
    if (!jokerExchangeMode || !currentPlayer?.hand) return [];

    // Find the target player and exposure
    const targetPlayer = gameState?.players.find(p => p.id === jokerExchangeMode.targetPlayerId);
    if (!targetPlayer) return [];

    const exposure = targetPlayer.exposures?.[jokerExchangeMode.exposureIndex];
    if (!exposure) return [];

    return currentPlayer.hand.filter(tile => tileMatchesExposure(tile, exposure));
  };

  if (!gameState) {
    return (
      <div className="game-board-loading">
        <div className="loading-spinner"></div>
        <p>Loading game...</p>
      </div>
    );
  }

  return (
    <div className="game-board">
      {/* Charleston overlay */}
      {isCharleston && (
        <Charleston />
      )}

      {/* Charleston vote overlay */}
      {gameState?.phase === 'charleston_vote' && (
        <CharlestonVote />
      )}

      {/* Call dialog */}
      {callOpportunity && (
        <CallDialog />
      )}

      {/* Joker exchange dialog */}
      <JokerExchangeDialog />

      {/* Practice mode pattern suggestions */}
      <PatternSuggestions enabled={practiceMode} onToggle={togglePracticeMode} />

      {/* Joker exchange mode overlay */}
      {jokerExchangeMode && (
        <div className="joker-exchange-mode-overlay">
          <div className="joker-exchange-mode-message">
            <h3>Select a tile from your hand to exchange</h3>
            {getMatchingTilesForExchange().length === 0 ? (
              <p className="no-matching">You don't have any matching tiles!</p>
            ) : (
              <p>Click a highlighted tile in your hand to offer it</p>
            )}
            <button className="btn btn-secondary" onClick={cancelJokerExchangeMode}>Cancel</button>
          </div>
        </div>
      )}

      {/* Top player */}
      <div className="board-top">
        <PlayerArea
          player={positionedPlayers.find(p => p.position === 'top')}
          position="top"
          onJokerClick={gameState?.phase === 'playing' ? handleJokerClick : undefined}
        />
      </div>

      {/* Middle section with left, center, right */}
      <div className="board-middle">
        {/* Left player */}
        <div className="board-left">
          <PlayerArea
            player={positionedPlayers.find(p => p.position === 'left')}
            position="left"
            onJokerClick={gameState?.phase === 'playing' ? handleJokerClick : undefined}
          />
        </div>

        {/* Center - discard pile and wall info */}
        <div className="board-center">
          <div className="wall-info">
            <span className="wall-count">{gameState.wallCount} tiles remaining</span>
            <span className="turn-info">
              Turn {gameState.turnNumber}
            </span>
          </div>

          {/* Clickable Wall */}
          <div
            className={`wall-stack ${canDraw ? 'wall-clickable' : ''}`}
            onClick={canDraw ? handleDraw : undefined}
            title={canDraw ? 'Click to draw a tile' : ''}
          >
            <div className="wall-tiles">
              <Tile tile={{ type: 'hidden' }} hidden small />
              <Tile tile={{ type: 'hidden' }} hidden small />
              <Tile tile={{ type: 'hidden' }} hidden small />
            </div>
            {canDraw && <span className="wall-draw-hint">Click to draw</span>}
          </div>

          {/* Drawn Tile Display */}
          {drawnTile && myTurn && (
            <div className="drawn-tile-display">
              <span className="drawn-tile-label">You drew:</span>
              <Tile tile={drawnTile} className="drawn-tile-highlight" />
              <button className="btn btn-small" onClick={clearDrawnTile}>
                OK
              </button>
            </div>
          )}

          <div className="discard-area">
            <h4>Discards</h4>
            <div className="discard-pile">
              {gameState.discardPile.slice(-12).map((tile, index) => (
                <Tile
                  key={`discard-${tile.id}-${index}`}
                  tile={tile}
                  small
                />
              ))}
              {gameState.currentDiscard && (
                <Tile
                  tile={gameState.currentDiscard.tile}
                  className="current-discard"
                />
              )}
            </div>
          </div>
        </div>

        {/* Right player */}
        <div className="board-right">
          <PlayerArea
            player={positionedPlayers.find(p => p.position === 'right')}
            position="right"
            onJokerClick={gameState?.phase === 'playing' ? handleJokerClick : undefined}
          />
        </div>
      </div>

      {/* Bottom - current player's hand */}
      <div className="board-bottom">
        <div className="my-area">
          {/* My exposures */}
          {currentPlayer?.exposures.length > 0 && (
            <div className="my-exposures">
              {currentPlayer.exposures.map((exposure, index) => (
                <div key={index} className="exposure-group">
                  {exposure.tiles.map((tile, tIndex) => (
                    <Tile
                      key={`exposure-${tile.id}-${tIndex}`}
                      tile={tile}
                      small
                    />
                  ))}
                </div>
              ))}
            </div>
          )}

          {/* My hand */}
          <div className="my-hand">
            {/* Arrange mode toggle button */}
            {gameState.phase !== 'finished' && (
              <div className="arrange-mode-toggle">
                <button
                  className={`btn btn-small ${arrangeMode ? 'btn-active' : 'btn-secondary'}`}
                  onClick={toggleArrangeMode}
                >
                  {arrangeMode ? '✓ Arrange Mode ON' : '↔ Arrange Tiles'}
                </button>
                {arrangeMode && swapFromIndex === null && (
                  <span className="arrange-hint">Click a tile to move it</span>
                )}
                {arrangeMode && swapFromIndex !== null && (
                  <span className="arrange-hint">Click where to place it (or same tile to cancel)</span>
                )}
              </div>
            )}
            <div className="hand-tiles">
              {currentPlayer?.hand.map((tile, index) => {
                const matchingTiles = getMatchingTilesForExchange();
                const isMatchForExchange = jokerExchangeMode && matchingTiles.some(t => t.id === tile.id);
                // Tiles are clickable during charleston, charleston_vote, playing, and calling phases
                const isInteractivePhase = ['charleston', 'charleston_vote', 'playing', 'calling'].includes(gameState.phase);
                // Highlight tile being moved in swap mode
                const isSwapSource = arrangeMode && swapFromIndex === index;

                // Determine click handler based on mode
                let tileClickHandler;
                if (arrangeMode) {
                  tileClickHandler = () => handleArrangeModeClick(index);
                } else if (jokerExchangeMode && isMatchForExchange) {
                  tileClickHandler = () => handleOfferTileForJoker(tile.id);
                } else if (!jokerExchangeMode) {
                  tileClickHandler = handleTileClick;
                }

                return (
                  <Tile
                    key={tile.id}
                    tile={tile}
                    index={index}
                    selected={arrangeMode ? isSwapSource : selectedTiles.includes(tile.id)}
                    onClick={tileClickHandler}
                    onDoubleClick={arrangeMode || jokerExchangeMode ? undefined : handleTileDoubleClick}
                    disabled={!arrangeMode && (jokerExchangeMode ? !isMatchForExchange : !isInteractivePhase)}
                    className={`${isMatchForExchange ? 'joker-exchange-match' : ''} ${isSwapSource ? 'swap-source' : ''}`}
                  />
                );
              })}
            </div>
          </div>

          {/* Action buttons */}
          <div className="action-buttons">
            {canDiscard && (
              <button
                className="btn btn-primary"
                onClick={() => discardTile(selectedTiles[0])}
              >
                Discard Selected
              </button>
            )}
            {canDraw && (
              <span className="turn-indicator">Your turn - Click the wall to draw!</span>
            )}
            {myTurn && gameState?.phase === 'playing' && currentPlayer?.hand.length === activeHandSize && selectedTiles.length === 0 && (
              <span className="turn-indicator">Select a tile to discard (or double-click)</span>
            )}
          </div>

          {/* Player info */}
          <div className="my-info">
            <span className="player-name">{currentPlayer?.name}</span>
            <span className="player-wind">{currentPlayer?.wind}</span>
          </div>
        </div>
      </div>

      {/* Game over overlay */}
      {gameState.phase === 'finished' && (
        <div className="game-over-overlay">
          <div className="game-over-content">
            <h2>
              {gameState.winner !== null
                ? `${gameState.players[gameState.winner].name} wins!`
                : 'Wall Game - No Winner'}
            </h2>
            {gameState.winningHand && (
              <div className="winning-hand">
                <h3>Winning Hand:</h3>
                {/* Show pattern info */}
                {gameState.winningHand.pattern && (
                  <div className="winning-pattern">
                    <span className="pattern-section">{gameState.winningHand.pattern.section}</span>
                    <span className="pattern-name">{gameState.winningHand.pattern.name}</span>
                    {gameState.winningHand.pattern.value && (
                      <span className="pattern-value">{gameState.winningHand.pattern.value} points</span>
                    )}
                  </div>
                )}
                {/* Show exposures */}
                {gameState.winningHand.exposures?.length > 0 && (
                  <div className="winning-exposures">
                    {gameState.winningHand.exposures.map((exposure, expIndex) => (
                      <div key={`win-exp-${expIndex}`} className="exposure-group">
                        {exposure.tiles.map((tile, tIndex) => (
                          <Tile key={`win-exp-${expIndex}-${tile.id}-${tIndex}`} tile={tile} small />
                        ))}
                      </div>
                    ))}
                  </div>
                )}
                {/* Show concealed hand tiles */}
                <div className="hand-tiles">
                  {gameState.winningHand.hand.map((tile, index) => (
                    <Tile key={`win-${tile.id}-${index}`} tile={tile} small />
                  ))}
                </div>
                {/* Show total tile count */}
                <p className="winning-tile-count">
                  Total: {(gameState.winningHand.hand?.length || 0) +
                    (gameState.winningHand.exposures?.reduce((sum, exp) => sum + exp.tiles.length, 0) || 0)} tiles
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Chat and Video Chat */}
      <ChatBox />
      <VideoChat />
    </div>
  );
}

export default GameBoard;
