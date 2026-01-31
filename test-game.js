const { io } = require('socket.io-client');

const socket = io('http://localhost:5000');
let gameId = null;
let myHand = [];
let myPlayerIndex = null;
let lastCharlestonPhase = null;

socket.on('connect', () => {
  console.log('Connected:', socket.id);
  console.log('Starting game with bots...');
  socket.emit('start-game', { playerName: 'TestPlayer', withBots: true });
});

socket.on('game-started', (state) => {
  console.log('=== GAME STARTED ===');
  console.log('Game ID:', state.id);
  console.log('Phase:', state.phase);
  console.log('Charleston phase:', state.charlestonPhase);
  console.log('Players:', state.players.map(p => p.name + (p.isBot ? ' (Bot)' : '')).join(', '));
  gameId = state.id;
  myPlayerIndex = state.yourPlayerIndex;
  myHand = state.players[myPlayerIndex].hand;
  console.log('Your hand:', myHand.length, 'tiles');

  // Auto-submit charleston
  if (state.phase === 'charleston') {
    submitCharleston(state.charlestonPhase);
  }
});

function submitCharleston(charlestonPhase) {
  if (charlestonPhase === lastCharlestonPhase) return;
  if (myHand.length < 3) return;

  lastCharlestonPhase = charlestonPhase;

  // Pick first 3 tiles to pass
  const tilesToPass = myHand.slice(0, 3).map(t => t.id);
  console.log('  Submitting charleston pass for phase:', charlestonPhase, '- Game ID:', gameId);
  socket.emit('charleston-pass', { gameId, tileIds: tilesToPass });
}

let lastPhase = null;
let hasVoted = false;

socket.on('game-state', (state) => {
  gameId = state.id; // Make sure we have the gameId
  myPlayerIndex = state.yourPlayerIndex;
  myHand = state.players[myPlayerIndex].hand;

  // Only log on phase changes
  const phaseChanged = state.phase !== lastPhase || state.charlestonPhase !== lastCharlestonPhase;
  if (phaseChanged) {
    console.log('Phase:', state.phase, '| Charleston:', state.charlestonPhase, '| Turn:', state.turnNumber, '| Wall:', state.wallCount);
  }

  if (state.phase === 'charleston') {
    submitCharleston(state.charlestonPhase);
    hasVoted = false; // Reset vote flag for new charleston round
  }

  if (state.phase === 'charleston_vote' && !hasVoted) {
    console.log('  Voting to stop charleston');
    socket.emit('charleston-vote', { gameId, stopCharleston: true });
    hasVoted = true;
  }

  lastPhase = state.phase;

  // Handle playing phase - auto-play for human
  if (state.phase === 'playing') {
    const isMyTurn = state.currentPlayerIndex === myPlayerIndex;
    if (isMyTurn) {
      // If we have 13 tiles, draw first
      if (myHand.length === 13) {
        console.log('  Drawing tile...');
        socket.emit('draw-tile', { gameId });
      }
      // If we have 14 tiles, discard one
      else if (myHand.length === 14) {
        const tileToDiscard = myHand[0]; // Discard first tile
        console.log('  Discarding tile:', tileToDiscard.type, tileToDiscard.value || '');
        socket.emit('discard-tile', { gameId, tileId: tileToDiscard.id });
      }
    }
  }

  if (state.phase === 'finished') {
    console.log('');
    console.log('=== GAME FINISHED ===');
    if (state.winner !== null) {
      console.log('Winner:', state.players[state.winner].name);
    } else {
      console.log('Wall game - no winner');
    }
    console.log('Total turns:', state.turnNumber);
    process.exit(0);
  }
});

socket.on('call-opportunity', (data) => {
  console.log('  Call opportunity for tile:', data.tile.type, data.tile.value || '');
  // Auto-pass for testing
  setTimeout(() => {
    socket.emit('pass-call', { gameId });
  }, 100);
});

socket.on('error', (err) => {
  console.error('ERROR:', err.message);
});

socket.on('disconnect', () => {
  console.log('Disconnected');
});

// Timeout after 5 minutes
setTimeout(() => {
  console.log('Timeout - game taking too long');
  process.exit(1);
}, 300000);

console.log('Connecting to server...');
