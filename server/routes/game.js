/**
 * Game routes (REST API for game management)
 */

const express = require('express');
const router = express.Router();

// Note: Most game actions happen via WebSocket, but these routes
// provide REST endpoints for game management

/**
 * Get list of public games
 * GET /api/game/public
 */
router.get('/public', (req, res) => {
  // This would be implemented with the GameManager
  // For now, return empty list
  res.json({ games: [] });
});

/**
 * Get game by ID
 * GET /api/game/:id
 */
router.get('/:id', (req, res) => {
  const { id } = req.params;
  // Would look up game in GameManager
  res.json({ gameId: id, status: 'not_implemented' });
});

module.exports = router;
