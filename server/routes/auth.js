/**
 * Authentication routes
 */

const express = require('express');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const db = require('../models/database');

const router = express.Router();

const JWT_SECRET = process.env.JWT_SECRET || 'your-secret-key-change-in-production';

/**
 * Register a new user
 * POST /api/auth/register
 */
router.post('/register', async (req, res) => {
  try {
    const { username, email, password, displayName } = req.body;

    // Validate input
    if (!username || !email || !password) {
      return res.status(400).json({ error: 'Username, email, and password are required' });
    }

    if (password.length < 6) {
      return res.status(400).json({ error: 'Password must be at least 6 characters' });
    }

    // Check if user already exists
    const existingUser = db.prepare(
      'SELECT id FROM users WHERE username = ? OR email = ?'
    ).get(username, email);

    if (existingUser) {
      return res.status(400).json({ error: 'Username or email already exists' });
    }

    // Hash password
    const passwordHash = await bcrypt.hash(password, 10);

    // Insert user
    const result = db.prepare(`
      INSERT INTO users (username, email, password_hash, display_name)
      VALUES (?, ?, ?, ?)
    `).run(username, email, passwordHash, displayName || username);

    const userId = result.lastInsertRowid;

    // Create initial stats
    db.prepare('INSERT INTO user_stats (user_id) VALUES (?)').run(userId);

    // Generate JWT
    const token = jwt.sign({ userId, username }, JWT_SECRET, { expiresIn: '7d' });

    res.status(201).json({
      message: 'User registered successfully',
      token,
      user: {
        id: userId,
        username,
        email,
        displayName: displayName || username
      }
    });
  } catch (error) {
    console.error('Registration error:', error);
    res.status(500).json({ error: 'Server error during registration' });
  }
});

/**
 * Login
 * POST /api/auth/login
 */
router.post('/login', async (req, res) => {
  try {
    const { username, password } = req.body;

    if (!username || !password) {
      return res.status(400).json({ error: 'Username and password are required' });
    }

    // Find user
    const user = db.prepare(
      'SELECT * FROM users WHERE username = ? OR email = ?'
    ).get(username, username);

    if (!user) {
      return res.status(401).json({ error: 'Invalid credentials' });
    }

    // Check password
    const validPassword = await bcrypt.compare(password, user.password_hash);
    if (!validPassword) {
      return res.status(401).json({ error: 'Invalid credentials' });
    }

    // Update last login
    db.prepare('UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?').run(user.id);

    // Generate JWT
    const token = jwt.sign({ userId: user.id, username: user.username }, JWT_SECRET, { expiresIn: '7d' });

    // Get user stats
    const stats = db.prepare('SELECT * FROM user_stats WHERE user_id = ?').get(user.id);

    res.json({
      token,
      user: {
        id: user.id,
        username: user.username,
        email: user.email,
        displayName: user.display_name,
        avatarUrl: user.avatar_url,
        stats
      }
    });
  } catch (error) {
    console.error('Login error:', error);
    res.status(500).json({ error: 'Server error during login' });
  }
});

/**
 * Get current user
 * GET /api/auth/me
 */
router.get('/me', (req, res) => {
  const authHeader = req.headers.authorization;
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return res.status(401).json({ error: 'No token provided' });
  }

  const token = authHeader.split(' ')[1];

  try {
    const decoded = jwt.verify(token, JWT_SECRET);
    const user = db.prepare(`
      SELECT id, username, email, display_name, avatar_url
      FROM users WHERE id = ?
    `).get(decoded.userId);

    if (!user) {
      return res.status(404).json({ error: 'User not found' });
    }

    const stats = db.prepare('SELECT * FROM user_stats WHERE user_id = ?').get(user.id);

    res.json({
      user: {
        id: user.id,
        username: user.username,
        email: user.email,
        displayName: user.display_name,
        avatarUrl: user.avatar_url,
        stats
      }
    });
  } catch (error) {
    return res.status(401).json({ error: 'Invalid token' });
  }
});

/**
 * Update user profile
 * PUT /api/auth/profile
 */
router.put('/profile', (req, res) => {
  const authHeader = req.headers.authorization;
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return res.status(401).json({ error: 'No token provided' });
  }

  const token = authHeader.split(' ')[1];

  try {
    const decoded = jwt.verify(token, JWT_SECRET);
    const { displayName, avatarUrl } = req.body;

    db.prepare(`
      UPDATE users SET display_name = ?, avatar_url = ? WHERE id = ?
    `).run(displayName, avatarUrl, decoded.userId);

    res.json({ message: 'Profile updated successfully' });
  } catch (error) {
    return res.status(401).json({ error: 'Invalid token' });
  }
});

/**
 * Guest login (no account required)
 * POST /api/auth/guest
 */
router.post('/guest', (req, res) => {
  const { displayName } = req.body;
  const guestName = displayName || `Guest_${Math.random().toString(36).substring(7)}`;

  // Generate a temporary token for guest
  const guestId = `guest_${Date.now()}_${Math.random().toString(36).substring(7)}`;
  const token = jwt.sign({ guestId, displayName: guestName, isGuest: true }, JWT_SECRET, { expiresIn: '24h' });

  res.json({
    token,
    user: {
      id: guestId,
      displayName: guestName,
      isGuest: true
    }
  });
});

module.exports = router;
