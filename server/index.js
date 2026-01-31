const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const cors = require('cors');
const path = require('path');

// Import routes
const authRoutes = require('./routes/auth');
const gameRoutes = require('./routes/game');
const groupRoutes = require('./routes/groups');

// Import game manager
const GameManager = require('./game/GameManager');

const app = express();
const server = http.createServer(app);
const io = new Server(server, {
  cors: {
    origin: process.env.NODE_ENV === 'production'
      ? true  // Allow all origins in production (served from same domain)
      : "http://localhost:3000",
    methods: ["GET", "POST"]
  }
});

// Middleware
app.use(cors());
app.use(express.json());

// Routes
app.use('/api/auth', authRoutes);
app.use('/api/game', gameRoutes);
app.use('/api/groups', groupRoutes);

// Initialize game manager with socket.io
const gameManager = new GameManager(io);

// Socket.io connection handling
io.on('connection', (socket) => {
  console.log('User connected:', socket.id);

  // Join a game room
  socket.on('join-game', (data) => {
    gameManager.handleJoinGame(socket, data);
  });

  // Start a game (with bots or waiting for players)
  socket.on('start-game', (data) => {
    console.log('Start game request from:', socket.id, 'data:', data);
    gameManager.handleStartGame(socket, data);
  });

  // Player draws a tile
  socket.on('draw-tile', (data) => {
    gameManager.handleDrawTile(socket, data);
  });

  // Player discards a tile
  socket.on('discard-tile', (data) => {
    gameManager.handleDiscardTile(socket, data);
  });

  // Player calls a tile (pung, kong, chow, mah jongg)
  socket.on('call-tile', (data) => {
    gameManager.handleCallTile(socket, data);
  });

  // Player passes on calling a tile
  socket.on('pass-call', (data) => {
    gameManager.handlePassCall(socket, data);
  });

  // Charleston - pass tiles
  socket.on('charleston-pass', (data) => {
    gameManager.handleCharlestonPass(socket, data);
  });

  // Charleston - vote to stop or continue
  socket.on('charleston-vote', (data) => {
    gameManager.handleCharlestonVote(socket, data);
  });

  // Declare Mah Jongg
  socket.on('declare-mahjong', (data) => {
    gameManager.handleDeclareMahjong(socket, data);
  });

  // Joker exchange - request
  socket.on('joker-exchange-request', (data) => {
    gameManager.handleJokerExchangeRequest(socket, data);
  });

  // Joker exchange - respond (accept/reject)
  socket.on('joker-exchange-response', (data) => {
    gameManager.handleJokerExchangeResponse(socket, data);
  });

  // Joker exchange - cancel
  socket.on('joker-exchange-cancel', (data) => {
    gameManager.handleJokerExchangeCancel(socket, data);
  });

  // Blank tile exchange - take any discard
  socket.on('blank-exchange', (data) => {
    gameManager.handleBlankExchange(socket, data);
  });

  // Pattern suggestions (practice mode)
  socket.on('get-pattern-suggestions', (data) => {
    gameManager.handleGetPatternSuggestions(socket, data);
  });

  // Chat message
  socket.on('chat-message', (data) => {
    gameManager.handleChatMessage(socket, data);
  });

  // Video/audio signaling for WebRTC
  socket.on('signal', (data) => {
    gameManager.handleSignal(socket, data);
  });

  // Disconnect
  socket.on('disconnect', () => {
    console.log('User disconnected:', socket.id);
    gameManager.handleDisconnect(socket);
  });
});

// Serve static files from React build
app.use(express.static(path.join(__dirname, '../client/build')));
app.get('/{*path}', (req, res) => {
  res.sendFile(path.join(__dirname, '../client/build', 'index.html'));
});

const PORT = process.env.PORT || 5000;
server.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
  console.log(`Open http://localhost:${PORT} in your browser`);
});

module.exports = { app, server, io };
