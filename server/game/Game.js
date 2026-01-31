/**
 * American Mah Jongg Game Logic
 *
 * Game phases:
 * 1. SETUP - Tiles are shuffled and dealt
 * 2. CHARLESTON - Players pass tiles (3 passes)
 * 3. PLAYING - Main game loop
 * 4. FINISHED - Game over
 */

const {
  generateTileSet,
  shuffleTiles,
  sortTiles,
  TILE_TYPES
} = require('./tiles');

const GAME_PHASES = {
  WAITING: 'waiting',
  SETUP: 'setup',
  CHARLESTON: 'charleston',
  CHARLESTON_VOTE: 'charleston_vote', // Voting to stop or continue Charleston
  PLAYING: 'playing',
  CALLING: 'calling', // Waiting for players to call/pass on a discard
  FINISHED: 'finished'
};

const CHARLESTON_PASSES = {
  FIRST_RIGHT: 'first_right',
  FIRST_ACROSS: 'first_across',
  FIRST_LEFT: 'first_left',
  SECOND_LEFT: 'second_left',
  SECOND_ACROSS: 'second_across',
  SECOND_RIGHT: 'second_right',
  COURTESY: 'courtesy', // Optional
  DONE: 'done'
};

const CALL_TYPES = {
  PASS: 'pass',
  CHOW: 'chow', // Not used in American Mahjong typically
  PUNG: 'pung',
  KONG: 'kong',
  QUINT: 'quint',
  MAH_JONGG: 'mahjong'
};

class Game {
  constructor(gameId, hostPlayerId, options = {}) {
    this.id = gameId;
    this.hostPlayerId = hostPlayerId;
    this.options = {
      botCount: options.botCount || 0,
      botDifficulty: options.botDifficulty || 'medium', // easy, medium, hard
      private: options.private || false,
      waitForPlayers: options.waitForPlayers || 4, // How many human players to wait for
      ...options
    };

    // Players array (always 4 players, some may be bots)
    this.players = [];
    this.playerMap = new Map(); // odId -> player index

    // Game state
    this.phase = GAME_PHASES.WAITING;
    this.wall = [];
    this.discardPile = [];
    this.currentPlayerIndex = 0; // East starts
    this.currentDiscard = null;
    this.callResponses = {}; // Track who has responded to a call opportunity

    // Charleston state
    this.charlestonPhase = null;
    this.charlestonPasses = {}; // playerId -> tiles to pass
    this.charlestonOptOut = {}; // For courtesy pass
    this.charlestonStopVotes = {}; // playerId -> true/false (true = stop, false = continue)

    // Turn state
    this.turnNumber = 0;
    this.lastAction = null;
    this.winner = null;
    this.winningHand = null;

    // Timestamps
    this.createdAt = new Date();
    this.startedAt = null;
    this.finishedAt = null;

    // Joker exchange state
    this.pendingJokerExchange = null; // { requesterId, targetPlayerId, exposureIndex, jokerIndex, offerTileId }
  }

  /**
   * Add a player to the game
   */
  addPlayer(playerId, playerName, isBot = false) {
    if (this.players.length >= 4) {
      throw new Error('Game is full');
    }
    if (this.phase !== GAME_PHASES.WAITING) {
      throw new Error('Game has already started');
    }

    const winds = ['East', 'South', 'West', 'North'];
    const playerIndex = this.players.length;

    const player = {
      id: playerId,
      name: playerName,
      isBot,
      wind: winds[playerIndex],
      hand: [],
      exposures: [], // Exposed melds (pungs, kongs, etc.)
      score: 0,
      isReady: false,
      connected: !isBot
    };

    this.players.push(player);
    this.playerMap.set(playerId, playerIndex);

    return player;
  }

  /**
   * Remove a player from the game
   */
  removePlayer(playerId) {
    const index = this.playerMap.get(playerId);
    if (index === undefined) return false;

    if (this.phase !== GAME_PHASES.WAITING) {
      // Mark as disconnected instead of removing
      this.players[index].connected = false;
      return true;
    }

    this.players.splice(index, 1);
    this.playerMap.delete(playerId);

    // Update player map indices
    this.playerMap.clear();
    this.players.forEach((p, i) => this.playerMap.set(p.id, i));

    return true;
  }

  /**
   * Add bots to fill remaining slots
   */
  addBots() {
    const botNames = ['Alice Bot', 'Bob Bot', 'Carol Bot', 'Dave Bot'];
    let botIndex = 0;

    while (this.players.length < 4) {
      const botId = `bot_${this.id}_${botIndex}`;
      this.addPlayer(botId, botNames[botIndex], true);
      botIndex++;
    }
  }

  /**
   * Start the game - deal tiles
   */
  startGame() {
    if (this.players.length !== 4) {
      throw new Error('Need exactly 4 players to start');
    }

    this.phase = GAME_PHASES.SETUP;
    this.startedAt = new Date();

    // Generate and shuffle tiles (with blanks option from game options)
    this.wall = shuffleTiles(generateTileSet({
      includeBlanks: this.options.includeBlanks || false
    }));

    // Deal tiles - East gets 14, others get 13
    for (let i = 0; i < 4; i++) {
      const tileCount = i === 0 ? 14 : 13; // East gets 14
      this.players[i].hand = this.wall.splice(0, tileCount);
      this.players[i].hand = sortTiles(this.players[i].hand);
    }

    // Start Charleston
    this.phase = GAME_PHASES.CHARLESTON;
    this.charlestonPhase = CHARLESTON_PASSES.FIRST_RIGHT;

    return this.getGameState();
  }

  /**
   * Handle Charleston tile passing
   */
  submitCharlestonPass(playerId, tileIds) {
    if (this.phase !== GAME_PHASES.CHARLESTON) {
      throw new Error('Not in Charleston phase');
    }

    if (tileIds.length !== 3) {
      throw new Error('Must pass exactly 3 tiles');
    }

    const playerIndex = this.playerMap.get(playerId);
    if (playerIndex === undefined) {
      throw new Error('Player not found');
    }

    const player = this.players[playerIndex];

    // Verify player has these tiles
    const tilesToPass = [];
    for (const tileId of tileIds) {
      const tile = player.hand.find(t => t.id === tileId);
      if (!tile) {
        throw new Error('Tile not in hand');
      }
      tilesToPass.push(tile);
    }

    this.charlestonPasses[playerId] = tilesToPass;

    // Check if all players have submitted
    if (Object.keys(this.charlestonPasses).length === 4) {
      this.executeCharlestonPass();
    }

    return true;
  }

  /**
   * Execute the Charleston pass
   */
  executeCharlestonPass() {
    const passDirection = this.getPassDirection();

    // Execute the pass for each player
    for (let i = 0; i < 4; i++) {
      const player = this.players[i];
      const targetIndex = (i + passDirection + 4) % 4;
      const targetPlayer = this.players[targetIndex];

      const tilesToPass = this.charlestonPasses[player.id];

      // Remove tiles from current player
      player.hand = player.hand.filter(t =>
        !tilesToPass.some(pt => pt.id === t.id)
      );

      // Add to target player
      targetPlayer.hand.push(...tilesToPass);
      targetPlayer.hand = sortTiles(targetPlayer.hand);
    }

    // Clear passes and advance phase
    this.charlestonPasses = {};
    this.advanceCharlestonPhase();
  }

  /**
   * Get pass direction: 1 = right, 2 = across, 3/-1 = left
   */
  getPassDirection() {
    switch (this.charlestonPhase) {
      case CHARLESTON_PASSES.FIRST_RIGHT:
      case CHARLESTON_PASSES.SECOND_RIGHT:
        return 1;
      case CHARLESTON_PASSES.FIRST_ACROSS:
      case CHARLESTON_PASSES.SECOND_ACROSS:
        return 2;
      case CHARLESTON_PASSES.FIRST_LEFT:
      case CHARLESTON_PASSES.SECOND_LEFT:
        return -1;
      default:
        return 0;
    }
  }

  /**
   * Advance to next Charleston phase
   */
  advanceCharlestonPhase() {
    const phases = [
      CHARLESTON_PASSES.FIRST_RIGHT,
      CHARLESTON_PASSES.FIRST_ACROSS,
      CHARLESTON_PASSES.FIRST_LEFT,
      CHARLESTON_PASSES.SECOND_LEFT,
      CHARLESTON_PASSES.SECOND_ACROSS,
      CHARLESTON_PASSES.SECOND_RIGHT,
      CHARLESTON_PASSES.DONE
    ];

    const currentIndex = phases.indexOf(this.charlestonPhase);

    // After first_left, enter voting phase to decide whether to continue
    if (this.charlestonPhase === CHARLESTON_PASSES.FIRST_LEFT) {
      this.phase = GAME_PHASES.CHARLESTON_VOTE;
      this.charlestonStopVotes = {};
      return;
    }

    if (currentIndex < phases.length - 1) {
      this.charlestonPhase = phases[currentIndex + 1];
    }

    if (this.charlestonPhase === CHARLESTON_PASSES.DONE) {
      this.startPlayPhase();
    }
  }

  /**
   * Submit a vote to stop or continue the Charleston
   */
  submitCharlestonVote(playerId, stopCharleston) {
    if (this.phase !== GAME_PHASES.CHARLESTON_VOTE) {
      throw new Error('Not in Charleston voting phase');
    }

    const playerIndex = this.playerMap.get(playerId);
    if (playerIndex === undefined) {
      throw new Error('Player not found');
    }

    this.charlestonStopVotes[playerId] = stopCharleston;

    // Check if all players have voted
    if (Object.keys(this.charlestonStopVotes).length === 4) {
      this.resolveCharlestonVote();
    }

    return true;
  }

  /**
   * Resolve the Charleston vote
   */
  resolveCharlestonVote() {
    // If ANY player wants to stop, the Charleston ends
    const anyoneWantsToStop = Object.values(this.charlestonStopVotes).some(vote => vote === true);

    if (anyoneWantsToStop) {
      // End Charleston, start playing
      this.charlestonPhase = CHARLESTON_PASSES.DONE;
      this.startPlayPhase();
    } else {
      // Continue with second Charleston
      this.phase = GAME_PHASES.CHARLESTON;
      this.charlestonPhase = CHARLESTON_PASSES.SECOND_LEFT;
    }
  }

  /**
   * Start the main playing phase
   */
  startPlayPhase() {
    this.phase = GAME_PHASES.PLAYING;
    this.currentPlayerIndex = 0; // East starts
    this.turnNumber = 1;

    // East already has 14 tiles, so they discard first
  }

  /**
   * Current player draws a tile from the wall
   */
  drawTile(playerId) {
    if (this.phase !== GAME_PHASES.PLAYING) {
      throw new Error('Not in playing phase');
    }

    // Block actions during pending joker exchange
    if (this.pendingJokerExchange) {
      throw new Error('Cannot draw while joker exchange is pending');
    }

    const playerIndex = this.playerMap.get(playerId);
    if (playerIndex !== this.currentPlayerIndex) {
      throw new Error('Not your turn');
    }

    if (this.wall.length === 0) {
      this.endGameWallDraw();
      return null;
    }

    const player = this.players[playerIndex];

    // Player should have 13 tiles to draw (or 14 if it's the first turn for East)
    if (player.hand.length >= 14) {
      throw new Error('Already have maximum tiles, must discard');
    }

    const tile = this.wall.shift();
    player.hand.push(tile);
    player.hand = sortTiles(player.hand);

    this.lastAction = { type: 'draw', playerId, tile };

    return tile;
  }

  /**
   * Current player discards a tile
   */
  discardTile(playerId, tileId) {
    if (this.phase !== GAME_PHASES.PLAYING) {
      throw new Error('Not in playing phase');
    }

    // Block actions during pending joker exchange
    if (this.pendingJokerExchange) {
      throw new Error('Cannot discard while joker exchange is pending');
    }

    const playerIndex = this.playerMap.get(playerId);
    if (playerIndex !== this.currentPlayerIndex) {
      throw new Error('Not your turn');
    }

    const player = this.players[playerIndex];
    const tileIndex = player.hand.findIndex(t => t.id === tileId);

    if (tileIndex === -1) {
      throw new Error('Tile not in hand');
    }

    const tile = player.hand.splice(tileIndex, 1)[0];
    this.currentDiscard = {
      tile,
      discardedBy: playerIndex
    };

    this.lastAction = { type: 'discard', playerId, tile };

    // Enter calling phase
    this.phase = GAME_PHASES.CALLING;
    this.callResponses = {};
    this.blankExchangeResponses = {}; // Track blank exchange requests

    // Mark current player as passed (can't call own discard)
    this.callResponses[playerId] = { type: CALL_TYPES.PASS };

    return tile;
  }

  /**
   * Player uses a blank tile to take any discarded tile
   * This can be done at any time during the calling phase
   */
  useBlankForDiscard(playerId, blankTileId) {
    if (this.phase !== GAME_PHASES.CALLING) {
      throw new Error('Can only use blank during calling phase');
    }

    if (!this.currentDiscard) {
      throw new Error('No discard to take');
    }

    const playerIndex = this.playerMap.get(playerId);
    if (playerIndex === undefined) {
      throw new Error('Player not found');
    }

    // Can take your own discard with a blank
    const player = this.players[playerIndex];

    // Find the blank tile in hand
    const blankTile = player.hand.find(t => t.id === blankTileId && t.type === TILE_TYPES.BLANK);
    if (!blankTile) {
      throw new Error('You do not have that blank tile');
    }

    // Remove blank from hand
    const blankIndex = player.hand.findIndex(t => t.id === blankTileId);
    player.hand.splice(blankIndex, 1);

    // Add blank to discard pile (it's used up)
    this.discardPile.push(blankTile);

    // Give player the discarded tile
    const takenTile = this.currentDiscard.tile;
    player.hand.push(takenTile);
    player.hand = sortTiles(player.hand);

    // Clear current discard
    this.currentDiscard = null;

    // Player who used blank must now discard
    this.currentPlayerIndex = playerIndex;
    this.phase = GAME_PHASES.PLAYING;
    this.callResponses = {};

    this.lastAction = {
      type: 'blank_exchange',
      playerId,
      blankTile,
      takenTile
    };

    return { blankTile, takenTile };
  }

  /**
   * Player calls the current discard
   */
  callTile(playerId, callType, meldTileIds = []) {
    if (this.phase !== GAME_PHASES.CALLING) {
      throw new Error('No tile to call');
    }

    const playerIndex = this.playerMap.get(playerId);
    if (playerIndex === undefined) {
      throw new Error('Player not found');
    }

    // Can't call your own discard
    if (playerIndex === this.currentDiscard.discardedBy) {
      throw new Error('Cannot call your own discard');
    }

    // Validate the call
    const player = this.players[playerIndex];
    const discardTile = this.currentDiscard.tile;
    const meldTiles = meldTileIds.map(id => player.hand.find(t => t.id === id));

    if (meldTiles.some(t => t === undefined)) {
      throw new Error('One or more selected tiles are not in your hand');
    }

    // Validate specific call types
    this.validateCall(callType, meldTiles, discardTile, player.hand);

    // Store the call
    this.callResponses[playerId] = {
      type: callType,
      meldTiles,
      playerIndex
    };

    // Check if all players have responded
    if (Object.keys(this.callResponses).length === 4) {
      this.resolveCall();
    }

    return true;
  }

  /**
   * Validate that a call is legal
   */
  validateCall(callType, meldTiles, discardTile, hand) {
    const jokerCount = meldTiles.filter(t => t.type === TILE_TYPES.JOKER).length;
    const nonJokerMeldTiles = meldTiles.filter(t => t.type !== TILE_TYPES.JOKER);

    // Can't call flowers
    if (discardTile.type === TILE_TYPES.FLOWER) {
      throw new Error('Cannot call flowers');
    }

    // After calling, player must have at least 1 tile left to discard
    // (unless it's Mah Jongg which ends the game)
    if (callType !== CALL_TYPES.MAH_JONGG) {
      const remainingHandSize = hand.length - meldTiles.length;
      if (remainingHandSize < 1) {
        throw new Error('You must have at least 1 tile remaining to discard after calling');
      }
    }

    // Check if non-joker tiles match the discard
    for (const tile of nonJokerMeldTiles) {
      if (tile.type !== discardTile.type || tile.value !== discardTile.value) {
        throw new Error(`Tile ${tile.type} ${tile.value} does not match the discarded ${discardTile.type} ${discardTile.value}`);
      }
    }

    switch (callType) {
      case CALL_TYPES.PUNG:
        // Need 2 tiles from hand (discarded is 3rd)
        if (meldTiles.length !== 2) {
          throw new Error('Pung requires exactly 2 tiles from your hand');
        }
        // At least 1 must match (can use 1 joker)
        if (nonJokerMeldTiles.length < 1 && jokerCount < 2) {
          throw new Error('You need at least 1 matching tile or 2 jokers for a Pung');
        }
        break;

      case CALL_TYPES.KONG:
        // Need 3 tiles from hand (discarded is 4th)
        if (meldTiles.length !== 3) {
          throw new Error('Kong requires exactly 3 tiles from your hand');
        }
        break;

      case CALL_TYPES.QUINT:
        // Need 4 tiles from hand (discarded is 5th)
        if (meldTiles.length !== 4) {
          throw new Error('Quint requires exactly 4 tiles from your hand');
        }
        break;

      case CALL_TYPES.MAH_JONGG:
        // This requires full hand validation - simplified for now
        // Would need to check against the NMJL card patterns
        break;

      default:
        throw new Error(`Unknown call type: ${callType}`);
    }
  }

  /**
   * Player passes on calling the current discard
   */
  passTile(playerId) {
    // Silently ignore if not in calling phase (might have already resolved)
    if (this.phase !== GAME_PHASES.CALLING) {
      return false;
    }

    // Already responded
    if (this.callResponses[playerId]) {
      return false;
    }

    this.callResponses[playerId] = { type: CALL_TYPES.PASS };

    // Check if all players have responded
    if (Object.keys(this.callResponses).length === 4) {
      this.resolveCall();
    }

    return true;
  }

  /**
   * Resolve calls after all players have responded
   */
  resolveCall() {
    // Priority: Mah Jongg > Kong/Quint > Pung > next player
    const callPriority = {
      [CALL_TYPES.MAH_JONGG]: 4,
      [CALL_TYPES.QUINT]: 3,
      [CALL_TYPES.KONG]: 2,
      [CALL_TYPES.PUNG]: 1,
      [CALL_TYPES.PASS]: 0
    };

    let winningCall = null;
    let winningPlayerId = null;

    for (const [playerId, call] of Object.entries(this.callResponses)) {
      if (call.type === CALL_TYPES.PASS) continue;

      const priority = callPriority[call.type] || 0;
      const currentPriority = winningCall ? callPriority[winningCall.type] : -1;

      if (priority > currentPriority) {
        winningCall = call;
        winningPlayerId = playerId;
      }
    }

    if (winningCall && winningCall.type !== CALL_TYPES.PASS) {
      this.executeCall(winningPlayerId, winningCall);
    } else {
      // No one called, move to next player
      this.advanceToNextPlayer();
    }
  }

  /**
   * Execute a successful call
   */
  executeCall(playerId, call) {
    const playerIndex = this.playerMap.get(playerId);
    const player = this.players[playerIndex];
    const discardTile = this.currentDiscard.tile;

    if (call.type === CALL_TYPES.MAH_JONGG) {
      // Player wins!
      this.winner = playerIndex;
      this.phase = GAME_PHASES.FINISHED;
      this.finishedAt = new Date();
      return;
    }

    // Remove meld tiles from hand
    for (const tile of call.meldTiles) {
      const idx = player.hand.findIndex(t => t.id === tile.id);
      if (idx !== -1) {
        player.hand.splice(idx, 1);
      }
    }

    // Create exposure (meld on table)
    const exposure = {
      type: call.type,
      tiles: [...call.meldTiles, discardTile],
      calledFrom: this.currentDiscard.discardedBy
    };
    player.exposures.push(exposure);

    // Clear current discard
    this.discardPile.push(discardTile);
    this.currentDiscard = null;

    // Player who called now discards
    this.currentPlayerIndex = playerIndex;
    this.phase = GAME_PHASES.PLAYING;
    this.callResponses = {};

    this.lastAction = {
      type: 'call',
      callType: call.type,
      playerId,
      tiles: exposure.tiles
    };
  }

  /**
   * Advance to the next player
   */
  advanceToNextPlayer() {
    if (this.currentDiscard) {
      this.discardPile.push(this.currentDiscard.tile);
      this.currentDiscard = null;
    }

    this.currentPlayerIndex = (this.currentPlayerIndex + 1) % 4;
    this.turnNumber++;
    this.phase = GAME_PHASES.PLAYING;
    this.callResponses = {};
  }

  /**
   * Handle wall exhaustion (no winner)
   */
  endGameWallDraw() {
    this.phase = GAME_PHASES.FINISHED;
    this.finishedAt = new Date();
    this.winner = null; // Wall game - no winner
  }

  /**
   * Declare Mah Jongg
   */
  declareMahjong(playerId) {
    const playerIndex = this.playerMap.get(playerId);
    if (playerIndex === undefined) {
      throw new Error('Player not found');
    }

    const player = this.players[playerIndex];

    // TODO: Validate the winning hand against the card
    // For now, we'll do a simple validation

    this.winner = playerIndex;
    this.winningHand = {
      hand: [...player.hand],
      exposures: [...player.exposures]
    };
    this.phase = GAME_PHASES.FINISHED;
    this.finishedAt = new Date();

    return true;
  }

  /**
   * Request a joker exchange from another player's exposed meld
   * In American Mah Jongg, you can exchange a matching tile for a joker in an exposed pung/kong/quint
   */
  requestJokerExchange(requesterId, targetPlayerId, exposureIndex, jokerIndex, offerTileId) {
    if (this.phase !== GAME_PHASES.PLAYING) {
      throw new Error('Can only exchange jokers during playing phase');
    }

    const requesterIndex = this.playerMap.get(requesterId);
    const targetIndex = this.playerMap.get(targetPlayerId);

    if (requesterIndex === undefined || targetIndex === undefined) {
      throw new Error('Player not found');
    }

    if (requesterIndex === targetIndex) {
      throw new Error('Cannot exchange joker with yourself');
    }

    const requester = this.players[requesterIndex];
    const target = this.players[targetIndex];

    // Verify the exposure exists
    if (!target.exposures[exposureIndex]) {
      throw new Error('Exposure not found');
    }

    const exposure = target.exposures[exposureIndex];

    // Verify there's a joker at that position
    if (!exposure.tiles[jokerIndex] || exposure.tiles[jokerIndex].type !== TILE_TYPES.JOKER) {
      throw new Error('No joker at that position');
    }

    // Verify requester has the offered tile
    const offerTile = requester.hand.find(t => t.id === offerTileId);
    if (!offerTile) {
      throw new Error('You do not have that tile in your hand');
    }

    // Verify the offered tile matches the meld
    // Find the "natural" tile type in the exposure (non-joker tile)
    const naturalTile = exposure.tiles.find(t => t.type !== TILE_TYPES.JOKER);
    if (!naturalTile) {
      throw new Error('Cannot determine meld type - all jokers');
    }

    // The offered tile must match the meld's type and value
    if (offerTile.type !== naturalTile.type || offerTile.value !== naturalTile.value) {
      throw new Error(`Offered tile (${offerTile.type} ${offerTile.value || ''}) does not match the meld (${naturalTile.type} ${naturalTile.value || ''})`);
    }

    // Store the pending exchange request
    this.pendingJokerExchange = {
      requesterId,
      requesterIndex,
      targetPlayerId,
      targetIndex,
      exposureIndex,
      jokerIndex,
      offerTileId,
      offerTile
    };

    return this.pendingJokerExchange;
  }

  /**
   * Accept or reject a joker exchange request
   */
  respondToJokerExchange(responderId, accept) {
    if (!this.pendingJokerExchange) {
      throw new Error('No pending joker exchange');
    }

    if (responderId !== this.pendingJokerExchange.targetPlayerId) {
      throw new Error('You are not the target of this exchange');
    }

    if (!accept) {
      // Rejected - clear the request
      this.pendingJokerExchange = null;
      return { accepted: false };
    }

    // Accept - execute the exchange
    const { requesterIndex, targetIndex, exposureIndex, jokerIndex, offerTileId } = this.pendingJokerExchange;

    const requester = this.players[requesterIndex];
    const target = this.players[targetIndex];
    const exposure = target.exposures[exposureIndex];

    // Get the joker from the exposure
    const joker = exposure.tiles[jokerIndex];

    // Remove the offered tile from requester's hand
    const offerTileIndex = requester.hand.findIndex(t => t.id === offerTileId);
    const offerTile = requester.hand.splice(offerTileIndex, 1)[0];

    // Add the joker to requester's hand
    requester.hand.push(joker);
    requester.hand = sortTiles(requester.hand);

    // Replace the joker in the exposure with the offered tile
    exposure.tiles[jokerIndex] = offerTile;

    // Clear the pending exchange
    const exchangeInfo = { ...this.pendingJokerExchange, accepted: true };
    this.pendingJokerExchange = null;

    this.lastAction = {
      type: 'joker_exchange',
      requesterId: exchangeInfo.requesterId,
      targetPlayerId: exchangeInfo.targetPlayerId,
      joker,
      replacementTile: offerTile
    };

    return exchangeInfo;
  }

  /**
   * Cancel a pending joker exchange (by the requester)
   */
  cancelJokerExchange(requesterId) {
    if (!this.pendingJokerExchange) {
      return false;
    }

    if (requesterId !== this.pendingJokerExchange.requesterId) {
      throw new Error('Only the requester can cancel the exchange');
    }

    this.pendingJokerExchange = null;
    return true;
  }

  /**
   * Get game state for a specific player (hides other players' hands)
   */
  getGameStateForPlayer(playerId) {
    const playerIndex = this.playerMap.get(playerId);
    const state = this.getGameState();

    // Hide ALL other players' hands (including bots)
    state.players = state.players.map((p, i) => {
      if (i === playerIndex) {
        // This is the current player - show their full hand
        return p;
      }
      // All other players (including bots) - hide their hand tiles
      return {
        ...p,
        hand: p.hand.map(() => ({ hidden: true })),
        handCount: p.hand.length
      };
    });

    state.yourPlayerIndex = playerIndex;

    return state;
  }

  /**
   * Get full game state (for server/bots)
   */
  getGameState() {
    return {
      id: this.id,
      phase: this.phase,
      players: this.players.map(p => ({
        id: p.id,
        name: p.name,
        isBot: p.isBot,
        wind: p.wind,
        hand: p.hand,
        handCount: p.hand.length,
        exposures: p.exposures,
        score: p.score,
        connected: p.connected
      })),
      currentPlayerIndex: this.currentPlayerIndex,
      currentDiscard: this.currentDiscard,
      discardPile: this.discardPile,
      wallCount: this.wall.length,
      charlestonPhase: this.charlestonPhase,
      charlestonVoteCount: Object.keys(this.charlestonStopVotes).length,
      turnNumber: this.turnNumber,
      lastAction: this.lastAction,
      winner: this.winner,
      winningHand: this.winningHand,
      pendingJokerExchange: this.pendingJokerExchange ? {
        requesterId: this.pendingJokerExchange.requesterId,
        requesterIndex: this.pendingJokerExchange.requesterIndex,
        targetPlayerId: this.pendingJokerExchange.targetPlayerId,
        targetIndex: this.pendingJokerExchange.targetIndex,
        exposureIndex: this.pendingJokerExchange.exposureIndex,
        jokerIndex: this.pendingJokerExchange.jokerIndex
      } : null,
      options: {
        practiceMode: this.options.practiceMode || false,
        includeBlanks: this.options.includeBlanks || false
      }
    };
  }
}

module.exports = {
  Game,
  GAME_PHASES,
  CHARLESTON_PASSES,
  CALL_TYPES
};
