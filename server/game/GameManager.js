/**
 * Game Manager - Handles all game instances and socket communication
 */

const { v4: uuidv4 } = require('uuid');
const { Game, GAME_PHASES, CALL_TYPES } = require('./Game');
const BotPlayer = require('./BotPlayer');
const { analyzeHand, CARD_YEAR } = require('./handAnalyzer');

class GameManager {
  constructor(io) {
    this.io = io;
    this.games = new Map(); // gameId -> Game
    this.playerGames = new Map(); // odId -> gameId
    this.bots = new Map(); // botId -> BotPlayer instance
  }

  /**
   * Create a new game
   */
  createGame(hostPlayerId, hostPlayerName, options = {}) {
    const gameId = uuidv4().substring(0, 8);
    const game = new Game(gameId, hostPlayerId, options);
    game.addPlayer(hostPlayerId, hostPlayerName);

    this.games.set(gameId, game);
    this.playerGames.set(hostPlayerId, gameId);

    return game;
  }

  /**
   * Get game by ID
   */
  getGame(gameId) {
    return this.games.get(gameId);
  }

  /**
   * Handle player joining a game
   */
  handleJoinGame(socket, data) {
    const { gameId, playerName } = data;
    const game = this.games.get(gameId);

    if (!game) {
      socket.emit('error', { message: 'Game not found' });
      return;
    }

    try {
      game.addPlayer(socket.id, playerName);
      this.playerGames.set(socket.id, gameId);
      socket.join(gameId);

      // Notify all players in the game
      this.io.to(gameId).emit('player-joined', {
        player: { id: socket.id, name: playerName },
        gameState: game.getGameState()
      });

      // Check if we have enough players to start
      const humanPlayers = game.players.filter(p => !p.isBot).length;
      const requiredPlayers = game.options.waitForPlayers || 4;

      if (humanPlayers >= requiredPlayers && game.phase === GAME_PHASES.WAITING) {
        // Auto-start the game with bots filling remaining spots
        this.autoStartGame(game);
      }
    } catch (error) {
      socket.emit('error', { message: error.message });
    }
  }

  /**
   * Auto-start a game when enough players have joined
   */
  autoStartGame(game) {
    try {
      // Add bots to fill remaining spots
      if (game.players.length < 4) {
        game.addBots();

        // Create bot instances
        for (const player of game.players) {
          if (player.isBot) {
            this.bots.set(player.id, new BotPlayer(game.options.botDifficulty || 'medium'));
          }
        }
      }

      // Start the game
      game.startGame();

      // Send initial state to all players
      for (const player of game.players) {
        if (!player.isBot) {
          const playerSocket = this.io.sockets.sockets.get(player.id);
          if (playerSocket) {
            playerSocket.emit('game-started', game.getGameStateForPlayer(player.id));
          }
        }
      }

      // If in Charleston, bots need to select tiles
      if (game.phase === GAME_PHASES.CHARLESTON) {
        this.processBotCharleston(game);
      }
    } catch (error) {
      console.error('Error auto-starting game:', error);
    }
  }

  /**
   * Handle starting a game
   */
  handleStartGame(socket, data) {
    const { gameId, withBots, waitForPlayers } = data;
    let game = this.games.get(gameId);

    // If no gameId, create a new game
    if (!game) {
      const playerName = data.playerName || 'Player';
      const options = {
        botCount: withBots ? 3 : 0,
        waitForPlayers: waitForPlayers || (withBots ? 1 : 4)
      };
      game = this.createGame(socket.id, playerName, options);
      socket.join(game.id);
    }

    // Verify the socket is the host
    if (game.hostPlayerId !== socket.id) {
      socket.emit('error', { message: 'Only the host can start the game' });
      return;
    }

    // Check if we have enough human players
    const humanPlayers = game.players.filter(p => !p.isBot).length;
    const requiredPlayers = game.options.waitForPlayers || 4;

    if (humanPlayers < requiredPlayers && !withBots) {
      // Send waiting state - game code for others to join
      socket.emit('game-waiting', {
        gameId: game.id,
        playersJoined: humanPlayers,
        playersNeeded: requiredPlayers,
        gameState: game.getGameState()
      });
      return;
    }

    try {
      // Add bots to fill remaining spots
      if (withBots || game.players.length < 4) {
        game.addBots();

        // Create bot instances
        for (const player of game.players) {
          if (player.isBot) {
            this.bots.set(player.id, new BotPlayer(game.options.botDifficulty || 'medium'));
          }
        }
      }

      // Start the game
      game.startGame();

      // Send initial state to all players
      for (const player of game.players) {
        if (!player.isBot) {
          const playerSocket = this.io.sockets.sockets.get(player.id);
          if (playerSocket) {
            playerSocket.emit('game-started', game.getGameStateForPlayer(player.id));
          }
        }
      }

      // If in Charleston, bots need to select tiles
      if (game.phase === GAME_PHASES.CHARLESTON) {
        this.processBotCharleston(game);
      }
    } catch (error) {
      socket.emit('error', { message: error.message });
    }
  }

  /**
   * Process bot Charleston passes
   */
  processBotCharleston(game) {
    console.log('Processing bot Charleston, phase:', game.charlestonPhase);
    setTimeout(() => {
      try {
        for (const player of game.players) {
          if (player.isBot && !game.charlestonPasses[player.id]) {
            console.log('Bot', player.name, 'selecting Charleston tiles');
            const bot = this.bots.get(player.id);
            if (!bot) {
              console.error('Bot not found for player:', player.id);
              continue;
            }
            const tilesToPass = bot.selectCharlestonTiles(
              player.hand,
              game.charlestonPhase
            );
            console.log('Bot', player.name, 'passing tiles:', tilesToPass.map(t => t.id));
            game.submitCharlestonPass(player.id, tilesToPass.map(t => t.id));
          }
        }

        // Broadcast updated state
        this.broadcastGameState(game);
        console.log('Charleston passes submitted:', Object.keys(game.charlestonPasses).length, '/ 4');

        // Handle next phase
        if (game.phase === GAME_PHASES.CHARLESTON) {
          // Still in Charleston, process again
          this.processBotCharleston(game);
        } else if (game.phase === GAME_PHASES.CHARLESTON_VOTE) {
          // Entered vote phase, trigger bot votes
          console.log('Charleston passes complete, entering vote phase');
          this.processBotCharlestonVote(game);
        } else if (game.phase === GAME_PHASES.PLAYING) {
          // If it's a bot's turn, make them play
          console.log('Charleston done, starting play phase');
          this.processBotTurn(game);
        }
      } catch (error) {
        console.error('Error in processBotCharleston:', error);
      }
    }, 1000); // 1 second delay for bots
  }

  /**
   * Handle Charleston pass submission
   */
  handleCharlestonPass(socket, data) {
    console.log('Charleston pass received from:', socket.id, 'tiles:', data.tileIds);
    const gameId = this.playerGames.get(socket.id);
    const game = this.games.get(gameId);

    if (!game) {
      console.error('Game not found for charleston pass');
      socket.emit('error', { message: 'Game not found' });
      return;
    }

    try {
      console.log('Submitting charleston pass for player:', socket.id);
      game.submitCharlestonPass(socket.id, data.tileIds);
      console.log('Charleston passes now:', Object.keys(game.charlestonPasses).length, '/ 4');
      this.broadcastGameState(game);

      // If Charleston is done and it's a bot's turn
      if (game.phase === GAME_PHASES.PLAYING) {
        console.log('Charleston complete, moving to play phase');
        this.processBotTurn(game);
      } else if (game.phase === GAME_PHASES.CHARLESTON_VOTE) {
        console.log('Entering Charleston vote phase');
        this.processBotCharlestonVote(game);
      } else if (game.phase === GAME_PHASES.CHARLESTON) {
        console.log('Still in Charleston, triggering bot passes');
        this.processBotCharleston(game);
      }
    } catch (error) {
      console.error('Error in handleCharlestonPass:', error.message);
      socket.emit('error', { message: error.message });
    }
  }

  /**
   * Handle Charleston vote (stop or continue)
   */
  handleCharlestonVote(socket, data) {
    console.log('=== CHARLESTON VOTE RECEIVED ===');
    console.log('Charleston vote from:', socket.id, 'stop:', data.stopCharleston, 'gameId in data:', data.gameId);
    const gameId = this.playerGames.get(socket.id);
    console.log('Player gameId from map:', gameId);
    const game = this.games.get(gameId);

    if (!game) {
      socket.emit('error', { message: 'Game not found' });
      return;
    }

    try {
      game.submitCharlestonVote(socket.id, data.stopCharleston);
      console.log('Charleston votes:', Object.keys(game.charlestonStopVotes).length, '/ 4');
      this.broadcastGameState(game);

      // If vote phase is done, handle next step
      if (game.phase === GAME_PHASES.PLAYING) {
        console.log('Charleston ended by vote, starting play phase');
        this.processBotTurn(game);
      } else if (game.phase === GAME_PHASES.CHARLESTON) {
        console.log('Charleston continuing with second round');
        this.processBotCharleston(game);
      } else if (game.phase === GAME_PHASES.CHARLESTON_VOTE) {
        // Still in vote phase, trigger bots to vote
        console.log('Still in vote phase, triggering bot votes');
        this.processBotCharlestonVote(game);
      }
    } catch (error) {
      console.error('Error in handleCharlestonVote:', error.message);
      socket.emit('error', { message: error.message });
    }
  }

  /**
   * Process bot Charleston votes
   */
  processBotCharlestonVote(game) {
    console.log('Processing bot Charleston votes');
    setTimeout(() => {
      try {
        for (const player of game.players) {
          if (player.isBot && !game.charlestonStopVotes[player.id]) {
            // Bots always vote to continue (they don't mind passing more tiles)
            console.log('Bot', player.name, 'voting to continue');
            game.submitCharlestonVote(player.id, false);
          }
        }

        console.log('After bot votes, total votes:', Object.keys(game.charlestonStopVotes).length, '/ 4', 'phase:', game.phase);
        this.broadcastGameState(game);

        // If vote phase resolved
        if (game.phase === GAME_PHASES.PLAYING) {
          console.log('Charleston ended by vote, starting play phase');
          this.processBotTurn(game);
        } else if (game.phase === GAME_PHASES.CHARLESTON) {
          console.log('Charleston continuing with second round');
          this.processBotCharleston(game);
        }
      } catch (error) {
        console.error('Error in processBotCharlestonVote:', error);
      }
    }, 500);
  }

  /**
   * Handle drawing a tile
   */
  handleDrawTile(socket, data) {
    const gameId = this.playerGames.get(socket.id);
    const game = this.games.get(gameId);

    if (!game) {
      socket.emit('error', { message: 'Game not found' });
      return;
    }

    try {
      const tile = game.drawTile(socket.id);

      // Send the drawn tile to the player
      socket.emit('tile-drawn', { tile });

      // Broadcast state update (without revealing the tile to others)
      this.broadcastGameState(game);
    } catch (error) {
      socket.emit('error', { message: error.message });
    }
  }

  /**
   * Handle discarding a tile
   */
  handleDiscardTile(socket, data) {
    const gameId = this.playerGames.get(socket.id);
    const game = this.games.get(gameId);

    if (!game) {
      socket.emit('error', { message: 'Game not found' });
      return;
    }

    try {
      const tile = game.discardTile(socket.id, data.tileId);
      const discardPlayerIndex = game.playerMap.get(socket.id);
      const discardPlayerName = game.players[discardPlayerIndex].name;

      // Broadcast the discard to all players
      this.io.to(gameId).emit('tile-discarded', {
        tile,
        playerId: socket.id,
        playerIndex: discardPlayerIndex
      });

      // Notify all players they can call (with more info)
      this.io.to(gameId).emit('call-opportunity', {
        tile,
        discardedBy: socket.id,
        discardedByName: discardPlayerName,
        discardedByIndex: discardPlayerIndex
      });

      // Process bot calls after a delay to give human player time
      setTimeout(() => {
        this.processBotCalls(game);
      }, 3000); // 3 second delay before bots respond
    } catch (error) {
      socket.emit('error', { message: error.message });
    }
  }

  /**
   * Handle calling a tile
   */
  handleCallTile(socket, data) {
    const gameId = this.playerGames.get(socket.id);
    const game = this.games.get(gameId);

    if (!game) {
      socket.emit('error', { message: 'Game not found' });
      return;
    }

    try {
      game.callTile(socket.id, data.callType, data.meldTileIds);
      this.broadcastGameState(game);

      // If still in calling phase, wait for others
      // If resolved, check if bot's turn
      if (game.phase === GAME_PHASES.PLAYING) {
        this.processBotTurn(game);
      }
    } catch (error) {
      socket.emit('error', { message: error.message });
    }
  }

  /**
   * Handle using a blank tile to take any discard
   */
  handleBlankExchange(socket, data) {
    const gameId = this.playerGames.get(socket.id);
    const game = this.games.get(gameId);

    if (!game) {
      socket.emit('error', { message: 'Game not found' });
      return;
    }

    try {
      const result = game.useBlankForDiscard(socket.id, data.blankTileId);

      // Notify all players about the blank exchange
      this.io.to(game.id).emit('blank-exchange', {
        playerId: socket.id,
        playerName: game.players[game.playerMap.get(socket.id)].name,
        takenTile: result.takenTile
      });

      this.broadcastGameState(game);
    } catch (error) {
      socket.emit('error', { message: error.message });
    }
  }

  /**
   * Handle passing on a call
   */
  handlePassCall(socket, data) {
    const gameId = this.playerGames.get(socket.id);
    const game = this.games.get(gameId);

    if (!game) {
      socket.emit('error', { message: 'Game not found' });
      return;
    }

    try {
      game.passTile(socket.id);
      this.broadcastGameState(game);

      // If resolved, check if bot's turn
      if (game.phase === GAME_PHASES.PLAYING) {
        this.processBotTurn(game);
      }
    } catch (error) {
      socket.emit('error', { message: error.message });
    }
  }

  /**
   * Process bot calls when a tile is discarded
   * Bots will make their decisions but won't trigger resolution until human responds
   */
  processBotCalls(game) {
    // Only process if still in calling phase and there's a discard to call
    if (game.phase !== GAME_PHASES.CALLING) return;
    if (!game.currentDiscard) return;

    setTimeout(() => {
      // Double-check we're still in calling phase with a valid discard
      if (game.phase !== GAME_PHASES.CALLING) return;
      if (!game.currentDiscard || !game.currentDiscard.tile) return;

      const discardTile = game.currentDiscard.tile;

      for (const player of game.players) {
        if (player.isBot && !game.callResponses[player.id]) {
          const bot = this.bots.get(player.id);
          if (!bot) continue;

          // Get possible calls
          const possibleCalls = bot.getPossibleCalls(player.hand, discardTile);

          // Let bot decide
          const decision = bot.decideCall(
            player.hand,
            player.exposures,
            discardTile,
            possibleCalls
          );

          if (decision.type === CALL_TYPES.PASS) {
            game.passTile(player.id);
          } else if (decision.type === CALL_TYPES.MAH_JONGG) {
            // Bot declares Mah Jongg!
            console.log('Bot', player.name, 'declares Mah Jongg!');
            try {
              game.declareMahjong(player.id);
              this.io.to(game.id).emit('game-over', {
                winner: player.id,
                winnerName: player.name,
                winnerIndex: game.winner,
                winningHand: game.winningHand,
                gameState: game.getGameState()
              });
              return; // Game is over
            } catch (e) {
              console.log('Bot Mah Jongg failed:', e.message);
              game.passTile(player.id);
            }
          } else {
            const meldTileIds = decision.tiles.map(t => t.id);
            try {
              game.callTile(player.id, decision.type, meldTileIds);
            } catch (e) {
              // If call fails, just pass
              console.log('Bot call failed:', e.message);
              game.passTile(player.id);
            }
          }
        }
      }

      this.broadcastGameState(game);

      // Check if game is finished
      if (game.phase === GAME_PHASES.FINISHED) {
        if (game.winner !== null) {
          const winner = game.players[game.winner];
          this.io.to(game.id).emit('game-over', {
            winner: winner.id,
            winnerName: winner.name,
            winnerIndex: game.winner,
            winningHand: game.winningHand,
            gameState: game.getGameState()
          });
        } else {
          // Wall game
          this.io.to(game.id).emit('game-over', {
            winner: null,
            wallGame: true,
            gameState: game.getGameState()
          });
        }
        return;
      }

      // If game moved to playing phase (all responded including human), check for bot turn
      if (game.phase === GAME_PHASES.PLAYING) {
        this.processBotTurn(game);
      }
    }, 500);
  }

  /**
   * Process bot turn (draw and discard)
   */
  processBotTurn(game) {
    console.log('processBotTurn called, currentPlayerIndex:', game.currentPlayerIndex, 'phase:', game.phase);
    const currentPlayer = game.players[game.currentPlayerIndex];
    console.log('Current player:', currentPlayer.name, 'isBot:', currentPlayer.isBot, 'hand:', currentPlayer.hand.length);

    if (!currentPlayer.isBot) {
      console.log('Not a bot turn, waiting for human player');
      return;
    }

    setTimeout(() => {
      const bot = this.bots.get(currentPlayer.id);

      // Calculate expected hand size based on exposures
      const exposedTiles = currentPlayer.exposures.reduce((sum, exp) => sum + exp.tiles.length, 0);
      const restingHandSize = 13 - exposedTiles;

      // Draw if needed (hand at resting size)
      if (currentPlayer.hand.length <= restingHandSize) {
        const drawnTile = game.drawTile(currentPlayer.id);
        this.broadcastGameState(game);

        // Check if wall is exhausted (game over)
        if (!drawnTile || game.phase === GAME_PHASES.FINISHED) {
          this.io.to(game.id).emit('game-over', {
            winner: null,
            wallGame: true,
            gameState: game.getGameState()
          });
          return;
        }
      }

      // Small delay, then discard
      setTimeout(() => {
        // Make sure we still need to discard
        if (game.phase !== GAME_PHASES.PLAYING) return;

        const botPlayerIndex = game.currentPlayerIndex;
        const tileToDiscard = bot.selectDiscard(currentPlayer.hand, currentPlayer.exposures);

        if (!tileToDiscard) {
          console.log('Bot has no tile to discard, hand:', currentPlayer.hand.length);
          return;
        }

        game.discardTile(currentPlayer.id, tileToDiscard.id);

        const discardPlayerName = currentPlayer.name;

        this.io.to(game.id).emit('tile-discarded', {
          tile: tileToDiscard,
          playerId: currentPlayer.id,
          playerIndex: botPlayerIndex
        });

        this.io.to(game.id).emit('call-opportunity', {
          tile: tileToDiscard,
          discardedBy: currentPlayer.id,
          discardedByName: discardPlayerName,
          discardedByIndex: botPlayerIndex
        });

        // Process other bot calls after delay - give human time to respond
        setTimeout(() => {
          this.processBotCalls(game);
        }, 3000); // 3 second delay before bots respond
      }, 800);
    }, 600);
  }

  /**
   * Handle declaring Mah Jongg
   */
  handleDeclareMahjong(socket, data) {
    const gameId = this.playerGames.get(socket.id);
    const game = this.games.get(gameId);

    if (!game) {
      socket.emit('error', { message: 'Game not found' });
      return;
    }

    try {
      game.declareMahjong(socket.id);

      this.io.to(gameId).emit('game-over', {
        winner: socket.id,
        winnerIndex: game.winner,
        winningHand: game.winningHand,
        gameState: game.getGameState()
      });
    } catch (error) {
      socket.emit('error', { message: error.message });
    }
  }

  /**
   * Handle joker exchange request
   */
  handleJokerExchangeRequest(socket, data) {
    const gameId = this.playerGames.get(socket.id);
    const game = this.games.get(gameId);

    if (!game) {
      socket.emit('error', { message: 'Game not found' });
      return;
    }

    try {
      const { targetPlayerId, exposureIndex, jokerIndex, offerTileId } = data;
      const exchange = game.requestJokerExchange(socket.id, targetPlayerId, exposureIndex, jokerIndex, offerTileId);

      // Notify the target player about the exchange request
      const targetSocket = this.io.sockets.sockets.get(targetPlayerId);
      if (targetSocket) {
        const requester = game.players[exchange.requesterIndex];
        targetSocket.emit('joker-exchange-request', {
          requesterId: socket.id,
          requesterName: requester.name,
          exposureIndex,
          jokerIndex,
          offerTile: exchange.offerTile
        });
      }

      // Also notify requester that request was sent
      socket.emit('joker-exchange-pending', {
        targetPlayerId,
        exposureIndex,
        jokerIndex
      });

      this.broadcastGameState(game);
    } catch (error) {
      socket.emit('error', { message: error.message });
    }
  }

  /**
   * Handle joker exchange response (accept/reject)
   */
  handleJokerExchangeResponse(socket, data) {
    const gameId = this.playerGames.get(socket.id);
    const game = this.games.get(gameId);

    if (!game) {
      socket.emit('error', { message: 'Game not found' });
      return;
    }

    try {
      const { accept } = data;
      const result = game.respondToJokerExchange(socket.id, accept);

      if (result.accepted) {
        // Notify both players about successful exchange
        const requesterSocket = this.io.sockets.sockets.get(result.requesterId);
        if (requesterSocket) {
          requesterSocket.emit('joker-exchange-complete', {
            success: true,
            message: 'Joker exchange successful!'
          });
        }
        socket.emit('joker-exchange-complete', {
          success: true,
          message: 'You gave up the joker'
        });
      } else {
        // Notify requester about rejection
        if (game.pendingJokerExchange) {
          const requesterSocket = this.io.sockets.sockets.get(game.pendingJokerExchange.requesterId);
          if (requesterSocket) {
            requesterSocket.emit('joker-exchange-complete', {
              success: false,
              message: 'Exchange request was declined'
            });
          }
        }
      }

      this.broadcastGameState(game);
    } catch (error) {
      socket.emit('error', { message: error.message });
    }
  }

  /**
   * Handle joker exchange cancellation
   */
  handleJokerExchangeCancel(socket, data) {
    const gameId = this.playerGames.get(socket.id);
    const game = this.games.get(gameId);

    if (!game) {
      socket.emit('error', { message: 'Game not found' });
      return;
    }

    try {
      const targetPlayerId = game.pendingJokerExchange?.targetPlayerId;
      game.cancelJokerExchange(socket.id);

      // Notify target that request was cancelled
      if (targetPlayerId) {
        const targetSocket = this.io.sockets.sockets.get(targetPlayerId);
        if (targetSocket) {
          targetSocket.emit('joker-exchange-cancelled', {
            message: 'Exchange request was cancelled'
          });
        }
      }

      this.broadcastGameState(game);
    } catch (error) {
      socket.emit('error', { message: error.message });
    }
  }

  /**
   * Handle chat messages
   */
  handleChatMessage(socket, data) {
    const gameId = this.playerGames.get(socket.id);
    if (gameId) {
      this.io.to(gameId).emit('chat-message', {
        playerId: socket.id,
        message: data.message,
        timestamp: new Date()
      });
    }
  }

  /**
   * Handle WebRTC signaling for video chat
   */
  handleSignal(socket, data) {
    const { targetId, signal } = data;
    const targetSocket = this.io.sockets.sockets.get(targetId);
    if (targetSocket) {
      targetSocket.emit('signal', {
        fromId: socket.id,
        signal
      });
    }
  }

  /**
   * Handle player disconnect
   */
  handleDisconnect(socket) {
    const gameId = this.playerGames.get(socket.id);
    if (!gameId) return;

    const game = this.games.get(gameId);
    if (!game) return;

    game.removePlayer(socket.id);
    this.playerGames.delete(socket.id);

    // Notify other players
    this.io.to(gameId).emit('player-left', {
      playerId: socket.id,
      gameState: game.getGameState()
    });

    // If game is empty, delete it
    const remainingPlayers = game.players.filter(p => !p.isBot && p.connected);
    if (remainingPlayers.length === 0) {
      this.games.delete(gameId);
    }
  }

  /**
   * Broadcast game state to all players in a game
   */
  broadcastGameState(game) {
    for (const player of game.players) {
      if (!player.isBot) {
        const playerSocket = this.io.sockets.sockets.get(player.id);
        if (playerSocket) {
          playerSocket.emit('game-state', game.getGameStateForPlayer(player.id));
        }
      }
    }
  }

  /**
   * Handle pattern analysis request (for practice mode)
   * Returns top 5 patterns the player's hand is closest to
   * Only allowed in bot games (for practice)
   */
  handleGetPatternSuggestions(socket, data) {
    console.log('Pattern suggestions requested by:', socket.id);
    const gameId = this.playerGames.get(socket.id);
    const game = this.games.get(gameId);

    if (!game) {
      console.log('Game not found for player:', socket.id);
      socket.emit('error', { message: 'Game not found' });
      return;
    }

    // Only allow in games with bots (practice games)
    const hasBots = game.players.some(p => p.isBot);
    if (!hasBots) {
      console.log('Not a bot game, rejecting pattern suggestions');
      socket.emit('error', { message: 'Pattern suggestions only available in bot games' });
      return;
    }

    const playerIndex = game.playerMap.get(socket.id);
    if (playerIndex === undefined) {
      console.log('Player not found in game');
      socket.emit('error', { message: 'Player not found' });
      return;
    }

    const player = game.players[playerIndex];
    console.log('Analyzing hand with', player.hand.length, 'tiles');

    try {
      const suggestions = analyzeHand(player.hand, player.exposures, 5);
      console.log('Got', suggestions.length, 'pattern suggestions');

      socket.emit('pattern-suggestions', {
        cardYear: CARD_YEAR,
        suggestions
      });
    } catch (error) {
      console.error('Error analyzing hand:', error);
      socket.emit('error', { message: 'Error analyzing hand: ' + error.message });
    }
  }
}

module.exports = GameManager;
