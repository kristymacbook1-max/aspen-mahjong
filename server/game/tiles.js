/**
 * American Mah Jongg Tile Set
 *
 * The complete set includes:
 * - Dots (1-9): 4 of each = 36 tiles
 * - Bams (Bamboo) (1-9): 4 of each = 36 tiles
 * - Craks (Characters) (1-9): 4 of each = 36 tiles
 * - Winds (East, South, West, North): 4 of each = 16 tiles
 * - Dragons (Red, Green, White/Soap): 4 of each = 12 tiles
 * - Flowers (1-8): 1 of each = 8 tiles
 * - Jokers: 8 tiles
 *
 * Total: 152 tiles
 */

const TILE_TYPES = {
  DOT: 'dot',
  BAM: 'bam',
  CRAK: 'crak',
  WIND: 'wind',
  DRAGON: 'dragon',
  FLOWER: 'flower',
  JOKER: 'joker',
  BLANK: 'blank'  // Blank tiles - can be exchanged for any discarded tile
};

const WINDS = ['east', 'south', 'west', 'north'];
const DRAGONS = ['red', 'green', 'white'];

/**
 * Create a single tile object
 */
function createTile(type, value, id) {
  return {
    id,
    type,
    value,
    display: getTileDisplay(type, value)
  };
}

/**
 * Get display string for a tile
 */
function getTileDisplay(type, value) {
  switch (type) {
    case TILE_TYPES.DOT:
      return `${value} Dot`;
    case TILE_TYPES.BAM:
      return `${value} Bam`;
    case TILE_TYPES.CRAK:
      return `${value} Crak`;
    case TILE_TYPES.WIND:
      return `${value.charAt(0).toUpperCase() + value.slice(1)} Wind`;
    case TILE_TYPES.DRAGON:
      if (value === 'white') return 'Soap';
      return `${value.charAt(0).toUpperCase() + value.slice(1)} Dragon`;
    case TILE_TYPES.FLOWER:
      return `Flower ${value}`;
    case TILE_TYPES.JOKER:
      return 'Joker';
    case TILE_TYPES.BLANK:
      return 'Blank';
    default:
      return 'Unknown';
  }
}

/**
 * Generate a complete American Mah Jongg tile set
 * @param {Object} options - Generation options
 * @param {boolean} options.includeBlanks - Whether to include blank tiles (default: false)
 * @returns {Array} Array of tile objects (152 tiles, or 154 with blanks)
 */
function generateTileSet(options = {}) {
  const { includeBlanks = false } = options;
  const tiles = [];
  let id = 0;

  // Dots (1-9, 4 of each)
  for (let value = 1; value <= 9; value++) {
    for (let copy = 0; copy < 4; copy++) {
      tiles.push(createTile(TILE_TYPES.DOT, value, id++));
    }
  }

  // Bams (1-9, 4 of each)
  for (let value = 1; value <= 9; value++) {
    for (let copy = 0; copy < 4; copy++) {
      tiles.push(createTile(TILE_TYPES.BAM, value, id++));
    }
  }

  // Craks (1-9, 4 of each)
  for (let value = 1; value <= 9; value++) {
    for (let copy = 0; copy < 4; copy++) {
      tiles.push(createTile(TILE_TYPES.CRAK, value, id++));
    }
  }

  // Winds (4 of each)
  for (const wind of WINDS) {
    for (let copy = 0; copy < 4; copy++) {
      tiles.push(createTile(TILE_TYPES.WIND, wind, id++));
    }
  }

  // Dragons (4 of each)
  for (const dragon of DRAGONS) {
    for (let copy = 0; copy < 4; copy++) {
      tiles.push(createTile(TILE_TYPES.DRAGON, dragon, id++));
    }
  }

  // Flowers (8 unique)
  for (let value = 1; value <= 8; value++) {
    tiles.push(createTile(TILE_TYPES.FLOWER, value, id++));
  }

  // Jokers (8)
  for (let copy = 0; copy < 8; copy++) {
    tiles.push(createTile(TILE_TYPES.JOKER, 'joker', id++));
  }

  // Blanks (2) - optional, can be exchanged for any discarded tile
  if (includeBlanks) {
    for (let copy = 0; copy < 2; copy++) {
      tiles.push(createTile(TILE_TYPES.BLANK, 'blank', id++));
    }
  }

  return tiles;
}

/**
 * Shuffle tiles using Fisher-Yates algorithm
 */
function shuffleTiles(tiles) {
  const shuffled = [...tiles];
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }
  return shuffled;
}

/**
 * Check if two tiles match (for sets)
 * Jokers can match anything except flowers
 */
function tilesMatch(tile1, tile2) {
  if (tile1.type === TILE_TYPES.JOKER || tile2.type === TILE_TYPES.JOKER) {
    // Jokers can't be used with flowers
    if (tile1.type === TILE_TYPES.FLOWER || tile2.type === TILE_TYPES.FLOWER) {
      return false;
    }
    return true;
  }
  return tile1.type === tile2.type && tile1.value === tile2.value;
}

/**
 * Check if tiles form a valid sequence (for Chow)
 * Only suits (Dots, Bams, Craks) can form sequences
 */
function isValidSequence(tiles) {
  if (tiles.length !== 3) return false;

  // Filter out jokers
  const nonJokers = tiles.filter(t => t.type !== TILE_TYPES.JOKER);

  // Must be same suit
  const suits = [TILE_TYPES.DOT, TILE_TYPES.BAM, TILE_TYPES.CRAK];
  const tileTypes = nonJokers.map(t => t.type);
  const suit = tileTypes.find(t => suits.includes(t));

  if (!suit || !tileTypes.every(t => t === suit || t === TILE_TYPES.JOKER)) {
    return false;
  }

  // Get values and sort
  const values = nonJokers.map(t => t.value).sort((a, b) => a - b);
  const jokerCount = tiles.length - nonJokers.length;

  // Check if they form a sequence (with joker gaps allowed)
  if (values.length === 3) {
    return values[1] === values[0] + 1 && values[2] === values[1] + 1;
  } else if (values.length === 2 && jokerCount === 1) {
    const diff = values[1] - values[0];
    return diff === 1 || diff === 2;
  } else if (values.length === 1 && jokerCount === 2) {
    return values[0] >= 1 && values[0] <= 7; // Can form sequence with jokers
  }

  return false;
}

/**
 * Check if tiles form a valid Pung (3 of a kind)
 */
function isValidPung(tiles) {
  if (tiles.length !== 3) return false;

  const nonJokers = tiles.filter(t => t.type !== TILE_TYPES.JOKER);
  if (nonJokers.length === 0) return false; // Can't have all jokers

  // All non-jokers must match
  const first = nonJokers[0];
  return nonJokers.every(t => t.type === first.type && t.value === first.value);
}

/**
 * Check if tiles form a valid Kong (4 of a kind)
 */
function isValidKong(tiles) {
  if (tiles.length !== 4) return false;

  const nonJokers = tiles.filter(t => t.type !== TILE_TYPES.JOKER);
  if (nonJokers.length === 0) return false;

  const first = nonJokers[0];
  return nonJokers.every(t => t.type === first.type && t.value === first.value);
}

/**
 * Check if tiles form a valid Quint (5 of a kind) - uses jokers
 */
function isValidQuint(tiles) {
  if (tiles.length !== 5) return false;

  const nonJokers = tiles.filter(t => t.type !== TILE_TYPES.JOKER);
  if (nonJokers.length === 0) return false;

  const first = nonJokers[0];
  return nonJokers.every(t => t.type === first.type && t.value === first.value);
}

/**
 * Check if tiles form a valid Sextet (6 of a kind) - uses jokers
 */
function isValidSextet(tiles) {
  if (tiles.length !== 6) return false;

  const nonJokers = tiles.filter(t => t.type !== TILE_TYPES.JOKER);
  if (nonJokers.length === 0) return false;

  const first = nonJokers[0];
  return nonJokers.every(t => t.type === first.type && t.value === first.value);
}

/**
 * Get the suit/type display name
 */
function getSuitName(type) {
  switch (type) {
    case TILE_TYPES.DOT: return 'Dots';
    case TILE_TYPES.BAM: return 'Bams';
    case TILE_TYPES.CRAK: return 'Craks';
    case TILE_TYPES.WIND: return 'Winds';
    case TILE_TYPES.DRAGON: return 'Dragons';
    case TILE_TYPES.FLOWER: return 'Flowers';
    case TILE_TYPES.JOKER: return 'Jokers';
    default: return 'Unknown';
  }
}

/**
 * Sort tiles by suit and value
 */
function sortTiles(tiles) {
  const suitOrder = {
    [TILE_TYPES.CRAK]: 0,
    [TILE_TYPES.DOT]: 1,
    [TILE_TYPES.BAM]: 2,
    [TILE_TYPES.WIND]: 3,
    [TILE_TYPES.DRAGON]: 4,
    [TILE_TYPES.FLOWER]: 5,
    [TILE_TYPES.JOKER]: 6,
    [TILE_TYPES.BLANK]: 7
  };

  const windOrder = { east: 0, south: 1, west: 2, north: 3 };
  const dragonOrder = { red: 0, green: 1, white: 2 };

  return [...tiles].sort((a, b) => {
    // First sort by suit
    if (suitOrder[a.type] !== suitOrder[b.type]) {
      return suitOrder[a.type] - suitOrder[b.type];
    }

    // Then sort by value within suit
    if (a.type === TILE_TYPES.WIND) {
      return windOrder[a.value] - windOrder[b.value];
    }
    if (a.type === TILE_TYPES.DRAGON) {
      return dragonOrder[a.value] - dragonOrder[b.value];
    }

    return a.value - b.value;
  });
}

module.exports = {
  TILE_TYPES,
  WINDS,
  DRAGONS,
  createTile,
  getTileDisplay,
  generateTileSet,
  shuffleTiles,
  tilesMatch,
  isValidSequence,
  isValidPung,
  isValidKong,
  isValidQuint,
  isValidSextet,
  getSuitName,
  sortTiles
};
