import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { io } from 'socket.io-client';

const SocketContext = createContext(null);

// Use same origin for socket connection (works on any port)
const socket = io({
  autoConnect: true,
  reconnection: true,
  reconnectionAttempts: 5,
  reconnectionDelay: 1000
});

export function SocketProvider({ children }) {
  const [connected, setConnected] = useState(socket.connected);
  const [gameState, setGameState] = useState(null);
  const [gameId, setGameId] = useState(null);
  const [error, setError] = useState(null);
  const [callError, setCallError] = useState(null);
  const [callOpportunity, setCallOpportunity] = useState(null);
  const [selectedTiles, setSelectedTiles] = useState([]);
  const [drawnTile, setDrawnTile] = useState(null);
  const [chatMessages, setChatMessages] = useState([]);
  const [remotePeers, setRemotePeers] = useState([]);
  const [waitingRoom, setWaitingRoom] = useState(null);
  const [jokerExchangeRequest, setJokerExchangeRequest] = useState(null);
  const [jokerExchangePending, setJokerExchangePending] = useState(null);
  const [jokerExchangeResult, setJokerExchangeResult] = useState(null);
  const [blankExchangeResult, setBlankExchangeResult] = useState(null);
  const [patternSuggestions, setPatternSuggestions] = useState(null);

  useEffect(() => {
    console.log('Setting up socket listeners');

    // Connection events
    socket.on('connect', () => {
      console.log('Socket connected:', socket.id);
      setConnected(true);
    });

    socket.on('disconnect', () => {
      console.log('Socket disconnected');
      setConnected(false);
    });

    socket.on('connect_error', (err) => {
      console.error('Socket connection error:', err);
    });

    // Game events
    socket.on('game-started', (state) => {
      console.log('Game started event received:', state);
      setGameState(state);
      setGameId(state.id);
      setError(null);
      setSelectedTiles([]);
      setWaitingRoom(null); // Clear waiting room when game starts
    });

    socket.on('game-waiting', (data) => {
      console.log('Game waiting for players:', data);
      setWaitingRoom(data);
      setGameId(data.gameId);
    });

    socket.on('game-state', (state) => {
      console.log('Game state update:', state);
      // Preserve local hand order when receiving server updates
      setGameState(prevState => {
        if (!prevState || !prevState.players || state.yourPlayerIndex === undefined) {
          return state;
        }

        const prevPlayer = prevState.players[prevState.yourPlayerIndex];
        const newPlayer = state.players[state.yourPlayerIndex];

        // If the hand has the same tiles (just potentially reordered by server),
        // preserve the client's order
        if (prevPlayer?.hand && newPlayer?.hand &&
            prevPlayer.hand.length === newPlayer.hand.length) {
          const prevTileIds = new Set(prevPlayer.hand.map(t => t.id));
          const newTileIds = new Set(newPlayer.hand.map(t => t.id));

          // Check if it's the same set of tiles
          const sameSet = prevPlayer.hand.length === newPlayer.hand.length &&
            [...prevTileIds].every(id => newTileIds.has(id));

          if (sameSet) {
            // Preserve the client's hand order
            const newPlayers = [...state.players];
            newPlayers[state.yourPlayerIndex] = {
              ...newPlayer,
              hand: prevPlayer.hand
            };
            return {
              ...state,
              players: newPlayers
            };
          }
        }

        return state;
      });
      // Clear call opportunity if game moved past calling phase
      if (state.phase !== 'calling') {
        setCallOpportunity(null);
        setCallError(null);
      }
    });

    socket.on('call-opportunity', (data) => {
      console.log('Call opportunity:', data);
      setCallOpportunity(data);
      setCallError(null); // Clear any previous call errors
    });

    socket.on('player-joined', (data) => {
      console.log('Player joined:', data);
      setGameState(data.gameState);
    });

    socket.on('player-left', (data) => {
      console.log('Player left:', data);
      setGameState(data.gameState);
    });

    socket.on('game-over', (data) => {
      console.log('Game over:', data);
      setGameState(data.gameState);
    });

    socket.on('error', (data) => {
      console.error('Game error:', data);
      // Only set main error for critical errors (game not found, etc.)
      // For gameplay errors (invalid call, etc.), only set callError
      const isCriticalError = data.message?.includes('Game not found') ||
                              data.message?.includes('not connected') ||
                              data.message?.includes('disconnected');
      if (isCriticalError) {
        setError(data.message);
      }
      // If we're in a call opportunity, show the error there
      setCallError(data.message);
    });

    socket.on('tile-drawn', (data) => {
      console.log('Tile drawn:', data);
      setDrawnTile(data.tile);
    });

    // Chat messages
    socket.on('chat-message', (data) => {
      console.log('Chat message received:', data);
      setChatMessages(prev => [...prev, data]);
    });

    // WebRTC signaling for video/audio
    socket.on('signal', (data) => {
      console.log('Signal received from:', data.fromId);
      // Handle WebRTC signaling - will be used by VideoChat component
      setRemotePeers(prev => {
        const existing = prev.find(p => p.id === data.fromId);
        if (existing) {
          return prev.map(p => p.id === data.fromId ? { ...p, signal: data.signal } : p);
        }
        return [...prev, { id: data.fromId, signal: data.signal }];
      });
    });

    // Joker exchange events
    socket.on('joker-exchange-request', (data) => {
      console.log('Joker exchange request received:', data);
      setJokerExchangeRequest(data);
    });

    socket.on('joker-exchange-pending', (data) => {
      console.log('Joker exchange pending:', data);
      setJokerExchangePending(data);
    });

    socket.on('joker-exchange-complete', (data) => {
      console.log('Joker exchange complete:', data);
      setJokerExchangeResult(data);
      setJokerExchangeRequest(null);
      setJokerExchangePending(null);
      // Clear result after a few seconds
      setTimeout(() => setJokerExchangeResult(null), 3000);
    });

    socket.on('joker-exchange-cancelled', (data) => {
      console.log('Joker exchange cancelled:', data);
      setJokerExchangeRequest(null);
      setJokerExchangePending(null);
    });

    // Blank exchange events
    socket.on('blank-exchange', (data) => {
      console.log('Blank exchange completed:', data);
      setBlankExchangeResult(data);
      // Clear result after a few seconds
      setTimeout(() => setBlankExchangeResult(null), 3000);
    });

    // Pattern suggestions (practice mode)
    socket.on('pattern-suggestions', (data) => {
      console.log('Pattern suggestions received:', data);
      setPatternSuggestions(data);
    });

    // Initial connection check
    if (socket.connected) {
      setConnected(true);
    }

    return () => {
      socket.off('connect');
      socket.off('disconnect');
      socket.off('connect_error');
      socket.off('game-started');
      socket.off('game-state');
      socket.off('call-opportunity');
      socket.off('player-joined');
      socket.off('player-left');
      socket.off('game-over');
      socket.off('error');
      socket.off('tile-drawn');
      socket.off('chat-message');
      socket.off('signal');
      socket.off('game-waiting');
      socket.off('joker-exchange-request');
      socket.off('joker-exchange-pending');
      socket.off('joker-exchange-complete');
      socket.off('joker-exchange-cancelled');
      socket.off('blank-exchange');
      socket.off('pattern-suggestions');
    };
  }, []);

  // Game actions
  const startGameWithBots = useCallback((playerName, options = {}) => {
    console.log('startGameWithBots called, connected:', socket.connected, 'playerName:', playerName, 'options:', options);
    if (!socket.connected) {
      console.error('Socket not connected!');
      return false;
    }
    console.log('Emitting start-game event');
    socket.emit('start-game', { playerName, withBots: true, ...options });
    return true;
  }, []);

  const joinGame = useCallback((gId, playerName) => {
    if (!socket.connected) return false;
    socket.emit('join-game', { gameId: gId, playerName });
    setGameId(gId);
    return true;
  }, []);

  const createGame = useCallback((playerName, options = {}) => {
    if (!socket.connected) return false;
    socket.emit('start-game', { playerName, ...options });
    return true;
  }, []);

  const drawTile = useCallback(() => {
    if (!socket.connected || !gameId) return;
    socket.emit('draw-tile', { gameId });
  }, [gameId]);

  const discardTile = useCallback((tileId) => {
    if (!socket.connected || !gameId) return;
    socket.emit('discard-tile', { gameId, tileId });
    setDrawnTile(null); // Clear the drawn tile indicator after discarding
  }, [gameId]);

  const clearDrawnTile = useCallback(() => {
    setDrawnTile(null);
  }, []);

  const callTile = useCallback((callType, meldTileIds) => {
    if (!socket.connected || !gameId) return;
    socket.emit('call-tile', { gameId, callType, meldTileIds });
    setCallOpportunity(null);
  }, [gameId]);

  const passCall = useCallback(() => {
    if (!socket.connected || !gameId) return;
    socket.emit('pass-call', { gameId });
    setCallOpportunity(null);
  }, [gameId]);

  const submitCharlestonPass = useCallback((tileIds) => {
    if (!socket.connected || !gameId) return;
    console.log('Submitting Charleston pass:', tileIds, 'for game:', gameId);
    socket.emit('charleston-pass', { gameId, tileIds });
    setSelectedTiles([]); // Clear selection after submitting
  }, [gameId]);

  const submitCharlestonVote = useCallback((stopCharleston) => {
    if (!socket.connected || !gameId) return;
    console.log('Submitting Charleston vote, stop:', stopCharleston, 'for game:', gameId);
    socket.emit('charleston-vote', { gameId, stopCharleston });
  }, [gameId]);

  const declareMahjong = useCallback(() => {
    if (!socket.connected || !gameId) return;
    socket.emit('declare-mahjong', { gameId });
  }, [gameId]);

  const leaveGame = useCallback(() => {
    setGameState(null);
    setGameId(null);
    setCallOpportunity(null);
    setError(null);
    setSelectedTiles([]);
    setChatMessages([]);
    setRemotePeers([]);
    setJokerExchangeRequest(null);
    setJokerExchangePending(null);
    setJokerExchangeResult(null);
  }, []);

  // Joker exchange functions
  const requestJokerExchange = useCallback((targetPlayerId, exposureIndex, jokerIndex, offerTileId) => {
    if (!socket.connected || !gameId) return;
    console.log('Requesting joker exchange:', { targetPlayerId, exposureIndex, jokerIndex, offerTileId });
    socket.emit('joker-exchange-request', { gameId, targetPlayerId, exposureIndex, jokerIndex, offerTileId });
  }, [gameId]);

  const respondToJokerExchange = useCallback((accept) => {
    if (!socket.connected || !gameId) return;
    console.log('Responding to joker exchange:', accept);
    socket.emit('joker-exchange-response', { gameId, accept });
    setJokerExchangeRequest(null);
  }, [gameId]);

  const cancelJokerExchange = useCallback(() => {
    if (!socket.connected || !gameId) return;
    console.log('Cancelling joker exchange');
    socket.emit('joker-exchange-cancel', { gameId });
    setJokerExchangePending(null);
  }, [gameId]);

  const clearJokerExchangeResult = useCallback(() => {
    setJokerExchangeResult(null);
  }, []);

  // Blank exchange - use a blank tile to take the current discard
  const exchangeBlankForDiscard = useCallback((blankTileId) => {
    if (!socket.connected || !gameId) return;
    console.log('Using blank tile for discard:', blankTileId);
    socket.emit('blank-exchange', { gameId, blankTileId });
  }, [gameId]);

  const clearBlankExchangeResult = useCallback(() => {
    setBlankExchangeResult(null);
  }, []);

  // Pattern suggestions (practice mode)
  const requestPatternSuggestions = useCallback(() => {
    if (!socket.connected || !gameId) return;
    console.log('Requesting pattern suggestions');
    socket.emit('get-pattern-suggestions', { gameId });
  }, [gameId]);

  const clearPatternSuggestions = useCallback(() => {
    setPatternSuggestions(null);
  }, []);

  // Chat functions
  const sendChatMessage = useCallback((message) => {
    if (!socket.connected || !gameId) return;
    socket.emit('chat-message', { gameId, message });
  }, [gameId]);

  // WebRTC signaling
  const sendSignal = useCallback((targetId, signal) => {
    if (!socket.connected) return;
    socket.emit('signal', { targetId, signal });
  }, []);

  // Tile selection for UI
  const toggleTileSelection = useCallback((tileId) => {
    setSelectedTiles(prev =>
      prev.includes(tileId)
        ? prev.filter(id => id !== tileId)
        : [...prev, tileId]
    );
  }, []);

  const clearSelection = useCallback(() => {
    setSelectedTiles([]);
  }, []);

  // Reorder hand tiles (client-side only - for player convenience)
  const reorderHand = useCallback((fromIndex, toIndex) => {
    setGameState(prevState => {
      if (!prevState) return prevState;
      const player = prevState.players[prevState.yourPlayerIndex];
      if (!player || !player.hand) return prevState;

      const newHand = [...player.hand];
      const [movedTile] = newHand.splice(fromIndex, 1);
      newHand.splice(toIndex, 0, movedTile);

      const newPlayers = [...prevState.players];
      newPlayers[prevState.yourPlayerIndex] = {
        ...player,
        hand: newHand
      };

      return {
        ...prevState,
        players: newPlayers
      };
    });
  }, []);

  // Helper functions for game state
  const isMyTurn = useCallback(() => {
    if (!gameState) return false;
    return gameState.yourPlayerIndex === gameState.currentPlayerIndex;
  }, [gameState]);

  const getCurrentPlayer = useCallback(() => {
    if (!gameState) return null;
    return gameState.players[gameState.yourPlayerIndex];
  }, [gameState]);

  const value = {
    socket,
    connected,
    socketId: socket.id,
    gameState,
    gameId,
    error,
    callError,
    callOpportunity,
    selectedTiles,
    drawnTile,
    chatMessages,
    remotePeers,
    waitingRoom,
    jokerExchangeRequest,
    jokerExchangePending,
    jokerExchangeResult,
    blankExchangeResult,
    patternSuggestions,
    startGameWithBots,
    joinGame,
    createGame,
    drawTile,
    discardTile,
    callTile,
    passCall,
    submitCharlestonPass,
    submitCharlestonVote,
    declareMahjong,
    leaveGame,
    toggleTileSelection,
    clearSelection,
    clearDrawnTile,
    reorderHand,
    isMyTurn,
    getCurrentPlayer,
    sendChatMessage,
    sendSignal,
    requestJokerExchange,
    respondToJokerExchange,
    cancelJokerExchange,
    clearJokerExchangeResult,
    exchangeBlankForDiscard,
    clearBlankExchangeResult,
    requestPatternSuggestions,
    clearPatternSuggestions
  };

  return (
    <SocketContext.Provider value={value}>
      {children}
    </SocketContext.Provider>
  );
}

export function useSocket() {
  const context = useContext(SocketContext);
  if (!context) {
    throw new Error('useSocket must be used within a SocketProvider');
  }
  return context;
}
