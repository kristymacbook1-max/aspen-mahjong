/**
 * Groups routes for organizing games with friends
 */

const express = require('express');
const jwt = require('jsonwebtoken');
const db = require('../models/database');

const router = express.Router();
const JWT_SECRET = process.env.JWT_SECRET || 'your-secret-key-change-in-production';

// Middleware to verify token
const authenticate = (req, res, next) => {
  const authHeader = req.headers.authorization;
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return res.status(401).json({ error: 'No token provided' });
  }

  const token = authHeader.split(' ')[1];
  try {
    const decoded = jwt.verify(token, JWT_SECRET);
    req.user = decoded;
    next();
  } catch (error) {
    return res.status(401).json({ error: 'Invalid token' });
  }
};

/**
 * Create a new group
 * POST /api/groups
 */
router.post('/', authenticate, (req, res) => {
  const { name, description, isPrivate } = req.body;
  const userId = req.user.userId;

  if (!name) {
    return res.status(400).json({ error: 'Group name is required' });
  }

  try {
    const result = db.prepare(`
      INSERT INTO groups (name, description, owner_id, is_private)
      VALUES (?, ?, ?, ?)
    `).run(name, description || '', userId, isPrivate ? 1 : 0);

    const groupId = result.lastInsertRowid;

    // Add owner as member
    db.prepare(`
      INSERT INTO group_members (group_id, user_id, role)
      VALUES (?, ?, 'owner')
    `).run(groupId, userId);

    res.status(201).json({
      message: 'Group created successfully',
      group: {
        id: groupId,
        name,
        description,
        isPrivate,
        ownerId: userId
      }
    });
  } catch (error) {
    console.error('Error creating group:', error);
    res.status(500).json({ error: 'Server error creating group' });
  }
});

/**
 * Get user's groups
 * GET /api/groups
 */
router.get('/', authenticate, (req, res) => {
  const userId = req.user.userId;

  try {
    const groups = db.prepare(`
      SELECT g.*, gm.role,
        (SELECT COUNT(*) FROM group_members WHERE group_id = g.id) as member_count
      FROM groups g
      JOIN group_members gm ON g.id = gm.group_id
      WHERE gm.user_id = ?
    `).all(userId);

    res.json({ groups });
  } catch (error) {
    console.error('Error fetching groups:', error);
    res.status(500).json({ error: 'Server error fetching groups' });
  }
});

/**
 * Get group details
 * GET /api/groups/:id
 */
router.get('/:id', authenticate, (req, res) => {
  const { id } = req.params;
  const userId = req.user.userId;

  try {
    const group = db.prepare(`
      SELECT g.*, gm.role as user_role
      FROM groups g
      LEFT JOIN group_members gm ON g.id = gm.group_id AND gm.user_id = ?
      WHERE g.id = ?
    `).get(userId, id);

    if (!group) {
      return res.status(404).json({ error: 'Group not found' });
    }

    if (group.is_private && !group.user_role) {
      return res.status(403).json({ error: 'Not a member of this private group' });
    }

    // Get members
    const members = db.prepare(`
      SELECT u.id, u.username, u.display_name, u.avatar_url, gm.role, gm.joined_at
      FROM group_members gm
      JOIN users u ON gm.user_id = u.id
      WHERE gm.group_id = ?
    `).all(id);

    res.json({
      group: {
        ...group,
        members
      }
    });
  } catch (error) {
    console.error('Error fetching group:', error);
    res.status(500).json({ error: 'Server error fetching group' });
  }
});

/**
 * Join a group
 * POST /api/groups/:id/join
 */
router.post('/:id/join', authenticate, (req, res) => {
  const { id } = req.params;
  const userId = req.user.userId;

  try {
    const group = db.prepare('SELECT * FROM groups WHERE id = ?').get(id);

    if (!group) {
      return res.status(404).json({ error: 'Group not found' });
    }

    if (group.is_private) {
      return res.status(403).json({ error: 'Cannot join private group without invitation' });
    }

    // Check if already a member
    const existing = db.prepare(
      'SELECT * FROM group_members WHERE group_id = ? AND user_id = ?'
    ).get(id, userId);

    if (existing) {
      return res.status(400).json({ error: 'Already a member of this group' });
    }

    db.prepare(`
      INSERT INTO group_members (group_id, user_id, role)
      VALUES (?, ?, 'member')
    `).run(id, userId);

    res.json({ message: 'Joined group successfully' });
  } catch (error) {
    console.error('Error joining group:', error);
    res.status(500).json({ error: 'Server error joining group' });
  }
});

/**
 * Leave a group
 * POST /api/groups/:id/leave
 */
router.post('/:id/leave', authenticate, (req, res) => {
  const { id } = req.params;
  const userId = req.user.userId;

  try {
    const membership = db.prepare(
      'SELECT * FROM group_members WHERE group_id = ? AND user_id = ?'
    ).get(id, userId);

    if (!membership) {
      return res.status(400).json({ error: 'Not a member of this group' });
    }

    if (membership.role === 'owner') {
      return res.status(400).json({ error: 'Owner cannot leave group. Transfer ownership or delete the group.' });
    }

    db.prepare('DELETE FROM group_members WHERE group_id = ? AND user_id = ?').run(id, userId);

    res.json({ message: 'Left group successfully' });
  } catch (error) {
    console.error('Error leaving group:', error);
    res.status(500).json({ error: 'Server error leaving group' });
  }
});

/**
 * Invite user to group
 * POST /api/groups/:id/invite
 */
router.post('/:id/invite', authenticate, (req, res) => {
  const { id } = req.params;
  const { username } = req.body;
  const userId = req.user.userId;

  try {
    // Check if user is admin/owner
    const membership = db.prepare(
      'SELECT * FROM group_members WHERE group_id = ? AND user_id = ?'
    ).get(id, userId);

    if (!membership || !['owner', 'admin'].includes(membership.role)) {
      return res.status(403).json({ error: 'Only admins can invite members' });
    }

    // Find user to invite
    const invitee = db.prepare('SELECT id FROM users WHERE username = ?').get(username);
    if (!invitee) {
      return res.status(404).json({ error: 'User not found' });
    }

    // Check if already a member
    const existing = db.prepare(
      'SELECT * FROM group_members WHERE group_id = ? AND user_id = ?'
    ).get(id, invitee.id);

    if (existing) {
      return res.status(400).json({ error: 'User is already a member' });
    }

    db.prepare(`
      INSERT INTO group_members (group_id, user_id, role)
      VALUES (?, ?, 'member')
    `).run(id, invitee.id);

    res.json({ message: 'User invited successfully' });
  } catch (error) {
    console.error('Error inviting user:', error);
    res.status(500).json({ error: 'Server error inviting user' });
  }
});

/**
 * Schedule a game in a group
 * POST /api/groups/:id/schedule
 */
router.post('/:id/schedule', authenticate, (req, res) => {
  const { id } = req.params;
  const { scheduledTime, description, maxPlayers } = req.body;
  const userId = req.user.userId;

  if (!scheduledTime) {
    return res.status(400).json({ error: 'Scheduled time is required' });
  }

  try {
    // Check if user is a member
    const membership = db.prepare(
      'SELECT * FROM group_members WHERE group_id = ? AND user_id = ?'
    ).get(id, userId);

    if (!membership) {
      return res.status(403).json({ error: 'Not a member of this group' });
    }

    const result = db.prepare(`
      INSERT INTO scheduled_games (group_id, host_id, scheduled_time, description, max_players)
      VALUES (?, ?, ?, ?, ?)
    `).run(id, userId, scheduledTime, description || '', maxPlayers || 4);

    const gameId = result.lastInsertRowid;

    // Host automatically RSVPs as attending
    db.prepare(`
      INSERT INTO game_rsvps (scheduled_game_id, user_id, status, responded_at)
      VALUES (?, ?, 'attending', CURRENT_TIMESTAMP)
    `).run(gameId, userId);

    res.status(201).json({
      message: 'Game scheduled successfully',
      scheduledGame: {
        id: gameId,
        groupId: id,
        hostId: userId,
        scheduledTime,
        description,
        maxPlayers: maxPlayers || 4
      }
    });
  } catch (error) {
    console.error('Error scheduling game:', error);
    res.status(500).json({ error: 'Server error scheduling game' });
  }
});

/**
 * Get scheduled games for a group
 * GET /api/groups/:id/scheduled
 */
router.get('/:id/scheduled', authenticate, (req, res) => {
  const { id } = req.params;
  const userId = req.user.userId;

  try {
    const games = db.prepare(`
      SELECT sg.*,
        u.username as host_username,
        u.display_name as host_display_name,
        (SELECT COUNT(*) FROM game_rsvps WHERE scheduled_game_id = sg.id AND status = 'attending') as rsvp_count,
        (SELECT status FROM game_rsvps WHERE scheduled_game_id = sg.id AND user_id = ?) as user_rsvp
      FROM scheduled_games sg
      JOIN users u ON sg.host_id = u.id
      WHERE sg.group_id = ? AND sg.scheduled_time > datetime('now')
      ORDER BY sg.scheduled_time ASC
    `).all(userId, id);

    res.json({ scheduledGames: games });
  } catch (error) {
    console.error('Error fetching scheduled games:', error);
    res.status(500).json({ error: 'Server error fetching scheduled games' });
  }
});

/**
 * RSVP to a scheduled game
 * POST /api/groups/scheduled/:gameId/rsvp
 */
router.post('/scheduled/:gameId/rsvp', authenticate, (req, res) => {
  const { gameId } = req.params;
  const { status } = req.body; // 'attending', 'declined', 'maybe'
  const userId = req.user.userId;

  if (!['attending', 'declined', 'maybe'].includes(status)) {
    return res.status(400).json({ error: 'Invalid RSVP status' });
  }

  try {
    // Check if game exists and user is a member of the group
    const game = db.prepare(`
      SELECT sg.*, gm.user_id as is_member
      FROM scheduled_games sg
      LEFT JOIN group_members gm ON sg.group_id = gm.group_id AND gm.user_id = ?
      WHERE sg.id = ?
    `).get(userId, gameId);

    if (!game) {
      return res.status(404).json({ error: 'Scheduled game not found' });
    }

    if (!game.is_member) {
      return res.status(403).json({ error: 'Not a member of this group' });
    }

    // Upsert RSVP
    db.prepare(`
      INSERT INTO game_rsvps (scheduled_game_id, user_id, status, responded_at)
      VALUES (?, ?, ?, CURRENT_TIMESTAMP)
      ON CONFLICT(scheduled_game_id, user_id) DO UPDATE SET status = ?, responded_at = CURRENT_TIMESTAMP
    `).run(gameId, userId, status, status);

    res.json({ message: 'RSVP updated successfully' });
  } catch (error) {
    console.error('Error updating RSVP:', error);
    res.status(500).json({ error: 'Server error updating RSVP' });
  }
});

module.exports = router;
