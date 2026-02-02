/**
 * Database setup using better-sqlite3
 * Optional - game works without database (for cloud deployment)
 */

let db = null;

try {
  const Database = require('better-sqlite3');
  const path = require('path');
  const fs = require('fs');

  const dataDir = path.join(__dirname, '../../data');
  if (!fs.existsSync(dataDir)) {
    fs.mkdirSync(dataDir, { recursive: true });
  }

  const dbPath = path.join(dataDir, 'mahjong.db');
  db = new Database(dbPath);

// Enable foreign keys
db.pragma('foreign_keys = ON');

// Create tables
db.exec(`
  -- Users table
  CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    display_name TEXT,
    avatar_url TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME
  );

  -- User statistics
  CREATE TABLE IF NOT EXISTS user_stats (
    user_id INTEGER PRIMARY KEY,
    games_played INTEGER DEFAULT 0,
    games_won INTEGER DEFAULT 0,
    wall_games INTEGER DEFAULT 0,
    total_points INTEGER DEFAULT 0,
    rating INTEGER DEFAULT 1000,
    avg_game_duration INTEGER DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id)
  );

  -- Game history
  CREATE TABLE IF NOT EXISTS games (
    id TEXT PRIMARY KEY,
    started_at DATETIME,
    finished_at DATETIME,
    winner_id INTEGER,
    game_type TEXT,
    is_wall_game BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (winner_id) REFERENCES users(id)
  );

  -- Game participants
  CREATE TABLE IF NOT EXISTS game_players (
    game_id TEXT,
    user_id INTEGER,
    seat_position INTEGER,
    final_score INTEGER,
    is_winner BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (game_id, user_id),
    FOREIGN KEY (game_id) REFERENCES games(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
  );

  -- Groups (for organizing games with friends)
  CREATE TABLE IF NOT EXISTS groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    owner_id INTEGER NOT NULL,
    is_private BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (owner_id) REFERENCES users(id)
  );

  -- Group members
  CREATE TABLE IF NOT EXISTS group_members (
    group_id INTEGER,
    user_id INTEGER,
    role TEXT DEFAULT 'member',
    joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (group_id, user_id),
    FOREIGN KEY (group_id) REFERENCES groups(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
  );

  -- Scheduled games
  CREATE TABLE IF NOT EXISTS scheduled_games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id INTEGER,
    host_id INTEGER NOT NULL,
    scheduled_time DATETIME NOT NULL,
    max_players INTEGER DEFAULT 4,
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (group_id) REFERENCES groups(id),
    FOREIGN KEY (host_id) REFERENCES users(id)
  );

  -- RSVPs for scheduled games
  CREATE TABLE IF NOT EXISTS game_rsvps (
    scheduled_game_id INTEGER,
    user_id INTEGER,
    status TEXT DEFAULT 'pending',
    responded_at DATETIME,
    PRIMARY KEY (scheduled_game_id, user_id),
    FOREIGN KEY (scheduled_game_id) REFERENCES scheduled_games(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
  );

  -- Friends list
  CREATE TABLE IF NOT EXISTS friends (
    user_id INTEGER,
    friend_id INTEGER,
    status TEXT DEFAULT 'pending',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, friend_id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (friend_id) REFERENCES users(id)
  );
`);
} catch (err) {
  console.log('Database not available (optional for gameplay):', err.message);
  db = null;
}

module.exports = db;
