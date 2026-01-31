/**
 * Hand Analyzer - Analyzes a player's hand against NMJL card patterns
 * and calculates odds/progress for each pattern
 */

const tiles = require('./tiles');
const TILE_TYPES = tiles.TILE_TYPES;

// Load current card (can be swapped for new year)
const { PATTERNS, CARD_YEAR } = require('./cards/2025-nmjl');

/**
 * Count tiles by type and value
 */
function countTiles(tiles) {
  const counts = {
    dot: {},
    bam: {},
    crak: {},
    wind: {},
    dragon: {},
    flower: 0,
    joker: 0,
    blank: 0
  };

  for (const tile of tiles) {
    if (tile.type === 'flower') {
      counts.flower++;
    } else if (tile.type === 'joker') {
      counts.joker++;
    } else if (tile.type === 'blank') {
      counts.blank++;
    } else if (tile.type === 'wind' || tile.type === 'dragon') {
      counts[tile.type][tile.value] = (counts[tile.type][tile.value] || 0) + 1;
    } else {
      counts[tile.type][tile.value] = (counts[tile.type][tile.value] || 0) + 1;
    }
  }

  return counts;
}

/**
 * Get the dragon that matches a suit
 */
function getMatchingDragon(suit) {
  switch (suit) {
    case 'crak': return 'red';
    case 'bam': return 'green';
    case 'dot': return 'white';
    default: return null;
  }
}

/**
 * Calculate how many tiles are needed to complete a group
 */
function tilesNeededForGroup(group, counts, suit, jokerCount) {
  const { type, value, jokerAllowed } = group;
  let needed = 0;
  let have = 0;

  // Determine target count based on group type
  const targetCount = {
    single: 1,
    pair: 2,
    pung: 3,
    kong: 4,
    quint: 5,
    sextet: 6
  }[type] || (type === 'flower' ? group.count : 0);

  if (type === 'flower') {
    have = counts.flower;
    needed = Math.max(0, targetCount - have);
    return { needed, have, canUseJoker: false };
  }

  // Handle dragon value
  if (value === 'dragon') {
    // Any dragon
    const dragonCounts = Object.values(counts.dragon);
    have = Math.max(...dragonCounts, 0);
    needed = Math.max(0, targetCount - have);
    if (jokerAllowed && jokerCount > 0) {
      needed = Math.max(0, needed - jokerCount);
    }
    return { needed, have, canUseJoker: jokerAllowed };
  }

  // Handle wind values
  if (typeof value === 'string' && ['north', 'east', 'west', 'south'].includes(value)) {
    have = counts.wind[value] || 0;
    needed = Math.max(0, targetCount - have);
    if (jokerAllowed && jokerCount > 0) {
      needed = Math.max(0, needed - jokerCount);
    }
    return { needed, have, canUseJoker: jokerAllowed };
  }

  // Handle number tiles
  if (suit && ['dot', 'bam', 'crak'].includes(suit)) {
    have = counts[suit][value] || 0;
    needed = Math.max(0, targetCount - have);
    if (jokerAllowed && jokerCount > 0) {
      needed = Math.max(0, needed - jokerCount);
    }
    return { needed, have, canUseJoker: jokerAllowed };
  }

  return { needed: targetCount, have: 0, canUseJoker: jokerAllowed };
}

/**
 * Analyze a hand against a single pattern
 * Returns progress info and tiles needed
 */
function analyzePattern(pattern, tiles, exposures = []) {
  const counts = countTiles(tiles);
  const allTiles = [...tiles];

  // Add exposed tiles to counts
  for (const exposure of exposures) {
    for (const tile of exposure.tiles) {
      allTiles.push(tile);
    }
  }
  const totalCounts = countTiles(allTiles);

  const suits = ['dot', 'bam', 'crak'];
  let bestMatch = null;
  let bestScore = -1;

  // Try each suit as the primary suit
  for (const primarySuit of suits) {
    let totalNeeded = 0;
    let totalHave = 0;
    let totalRequired = 0;
    let usedJokers = 0;
    const availableJokers = totalCounts.joker;
    let currentSuit = primarySuit;
    const usedSuits = [primarySuit];

    let valid = true;

    for (const group of pattern.pattern) {
      let groupSuit = currentSuit;

      // Determine suit for this group
      if (group.suit === 'different') {
        // Find a different suit
        for (const s of suits) {
          if (!usedSuits.includes(s)) {
            groupSuit = s;
            usedSuits.push(s);
            break;
          }
        }
      } else if (group.suit === 'third') {
        // Find the third suit
        for (const s of suits) {
          if (!usedSuits.includes(s)) {
            groupSuit = s;
            usedSuits.push(s);
            break;
          }
        }
      } else if (group.suit === 'match') {
        groupSuit = currentSuit;
      } else if (group.suit === 'any') {
        // For 'any', we already set it to primarySuit
        currentSuit = primarySuit;
        groupSuit = primarySuit;
      }

      const result = tilesNeededForGroup(group, totalCounts, groupSuit, availableJokers - usedJokers);

      // Track joker usage
      if (result.canUseJoker && result.needed > 0) {
        const jokersToUse = Math.min(result.needed, availableJokers - usedJokers);
        usedJokers += jokersToUse;
        result.needed -= jokersToUse;
      }

      // Determine required count for this group
      const targetCount = {
        single: 1,
        pair: 2,
        pung: 3,
        kong: 4,
        quint: 5,
        sextet: 6,
        flower: group.count || 0
      }[group.type] || 0;

      totalNeeded += result.needed;
      totalHave += Math.min(result.have, targetCount);
      totalRequired += targetCount;
    }

    // Calculate score (higher is better - closer to completion)
    const score = totalHave / totalRequired;

    if (score > bestScore) {
      bestScore = score;
      bestMatch = {
        tilesNeeded: totalNeeded,
        tilesHave: totalHave,
        tilesRequired: totalRequired,
        progress: score,
        primarySuit
      };
    }
  }

  return bestMatch || {
    tilesNeeded: 14,
    tilesHave: 0,
    tilesRequired: 14,
    progress: 0,
    primarySuit: 'dot'
  };
}

/**
 * Analyze a hand against all patterns and return top matches
 */
function analyzeHand(hand, exposures = [], topN = 5) {
  const results = [];

  for (const pattern of PATTERNS) {
    const analysis = analyzePattern(pattern, hand, exposures);

    results.push({
      pattern: {
        id: pattern.id,
        name: pattern.name,
        category: pattern.category,
        description: pattern.description,
        value: pattern.value,
        concealed: pattern.concealed
      },
      ...analysis,
      // Calculate odds as a percentage (simplified)
      odds: Math.round(analysis.progress * 100)
    });
  }

  // Sort by progress (descending) and take top N
  results.sort((a, b) => {
    // First by progress
    if (b.progress !== a.progress) {
      return b.progress - a.progress;
    }
    // Then by fewer tiles needed
    if (a.tilesNeeded !== b.tilesNeeded) {
      return a.tilesNeeded - b.tilesNeeded;
    }
    // Then by higher value
    return b.pattern.value - a.pattern.value;
  });

  return results.slice(0, topN);
}

/**
 * Get suggestions for which tiles to keep/discard
 */
function getTileSuggestions(hand, exposures = [], topPatterns = null) {
  if (!topPatterns) {
    topPatterns = analyzeHand(hand, exposures, 3);
  }

  const suggestions = {
    keep: [],
    maybeDiscard: [],
    topPatterns
  };

  // Count tile usage across top patterns
  const tileScores = {};

  for (const tile of hand) {
    const key = `${tile.type}-${tile.value}`;
    if (!tileScores[key]) {
      tileScores[key] = {
        tile: { type: tile.type, value: tile.value },
        usefulFor: 0,
        patterns: []
      };
    }
  }

  // Simple heuristic: tiles that appear in multiple top patterns are more valuable
  // This is a simplified version - a full implementation would be more sophisticated

  return suggestions;
}

module.exports = {
  analyzeHand,
  analyzePattern,
  getTileSuggestions,
  countTiles,
  CARD_YEAR,
  PATTERNS
};
