/**
 * Bot AI for American Mah Jongg
 *
 * Three difficulty levels:
 * - Easy: Random moves with basic logic
 * - Medium: Considers tile values and basic strategy
 * - Hard: Advanced strategy, uses pattern analysis
 */

const { TILE_TYPES, sortTiles } = require('./tiles');
const { CALL_TYPES, CHARLESTON_PASSES } = require('./Game');
const { analyzeHand, PATTERNS } = require('./handAnalyzer');

class BotPlayer {
  constructor(difficulty = 'medium') {
    this.difficulty = difficulty;
    this.discardMemory = []; // Track what's been discarded
    this.targetPattern = null; // The pattern we're working towards
  }

  /**
   * Get the top pattern to work towards based on current hand
   */
  getTargetPattern(hand, exposures = []) {
    const analysis = analyzeHand(hand, exposures, 3);
    if (analysis.length > 0) {
      return analysis[0];
    }
    return null;
  }

  /**
   * Check if a tile is useful for the target pattern
   */
  isTileUsefulForPattern(tile, targetPattern, hand) {
    if (!targetPattern) return false;

    const pattern = PATTERNS.find(p => p.id === targetPattern.pattern.id);
    if (!pattern) return false;

    // Check if this tile type/value appears in any group of the pattern
    for (const group of pattern.pattern) {
      if (group.type === 'flower' && tile.type === TILE_TYPES.FLOWER) {
        return true;
      }

      if (tile.type === TILE_TYPES.JOKER && group.jokerAllowed) {
        return true;
      }

      // Check wind/dragon matches
      if (group.value === 'dragon' && tile.type === TILE_TYPES.DRAGON) {
        return true;
      }
      if (typeof group.value === 'string' &&
          ['north', 'east', 'west', 'south'].includes(group.value) &&
          tile.type === TILE_TYPES.WIND && tile.value === group.value) {
        return true;
      }

      // Check number matches
      if (typeof group.value === 'number' &&
          tile.value === group.value &&
          [TILE_TYPES.DOT, TILE_TYPES.BAM, TILE_TYPES.CRAK].includes(tile.type)) {
        return true;
      }

      // Check 'X' (any number) patterns
      if (group.value === 'X' &&
          [TILE_TYPES.DOT, TILE_TYPES.BAM, TILE_TYPES.CRAK].includes(tile.type)) {
        return true;
      }
    }

    return false;
  }

  /**
   * Check if we can call Mah Jongg with the given tile
   */
  canCallMahjong(hand, exposures, discardTile) {
    // Calculate total tiles
    const handTiles = [...hand];
    if (discardTile) {
      handTiles.push(discardTile);
    }

    const exposedCount = exposures.reduce((sum, exp) => sum + exp.tiles.length, 0);
    const totalTiles = handTiles.length + exposedCount;

    // Must have exactly 14 tiles to win
    if (totalTiles !== 14) {
      return false;
    }

    // Check against all patterns using the analyzer
    const analysis = analyzeHand(handTiles, exposures, 15);

    for (const result of analysis) {
      // If we have 0 tiles needed, we can win!
      if (result.tilesNeeded === 0) {
        // For concealed patterns, check we have no exposures
        if (result.pattern.concealed && exposures.length > 0) {
          continue;
        }
        console.log(`  -> Can win with pattern: ${result.pattern.name} (${result.pattern.description})`);
        return true;
      }
    }

    // Also do a simpler check - if we have valid groups totaling 14 tiles
    return this.checkSimpleWin(handTiles, exposures);
  }

  /**
   * Simple win check - verify we have valid melds totaling 14 tiles
   */
  checkSimpleWin(hand, exposures) {
    // Count all tiles by type and value
    const counts = new Map();
    const allTiles = [...hand];

    for (const exp of exposures) {
      for (const tile of exp.tiles) {
        allTiles.push(tile);
      }
    }

    if (allTiles.length !== 14) return false;

    for (const tile of allTiles) {
      const key = `${tile.type}-${tile.value}`;
      counts.set(key, (counts.get(key) || 0) + 1);
    }

    // Check if all tiles form valid groups (pairs, pungs, kongs, etc.)
    // This is a simplified check - real validation should use pattern matching
    let totalGrouped = 0;
    const jokerCount = hand.filter(t => t.type === TILE_TYPES.JOKER).length;

    for (const [key, count] of counts) {
      if (key.includes('joker')) continue;
      // Accept groups of 2, 3, 4, 5, or 6
      if (count >= 2) {
        totalGrouped += count;
      }
    }

    // If most tiles are in groups and we have jokers to fill gaps, might be a win
    return totalGrouped + jokerCount >= 12;
  }

  /**
   * Decide which 3 tiles to pass during Charleston
   */
  selectCharlestonTiles(hand, passDirection) {
    const sorted = sortTiles([...hand]);

    switch (this.difficulty) {
      case 'easy':
        return this.easyCharlestonSelect(sorted);
      case 'hard':
        return this.hardCharlestonSelect(sorted, passDirection);
      default:
        return this.mediumCharlestonSelect(sorted);
    }
  }

  /**
   * Easy: Just pass random tiles, avoiding jokers
   */
  easyCharlestonSelect(hand) {
    const nonJokers = hand.filter(t => t.type !== TILE_TYPES.JOKER);
    const shuffled = [...nonJokers].sort(() => Math.random() - 0.5);
    return shuffled.slice(0, 3);
  }

  /**
   * Medium: Pass orphan tiles using pattern analysis
   */
  mediumCharlestonSelect(hand) {
    // Get target pattern
    this.targetPattern = this.getTargetPattern(hand);

    // Score tiles by usefulness
    const scored = hand
      .filter(t => t.type !== TILE_TYPES.JOKER) // Never pass jokers
      .map(tile => {
        let score = 0;

        // Check if useful for target pattern
        if (this.isTileUsefulForPattern(tile, this.targetPattern, hand)) {
          score += 10;
        }

        // Count duplicates (more = better to keep)
        const sameCount = hand.filter(
          t => t.type === tile.type && t.value === tile.value
        ).length;
        score += sameCount * 2;

        // Flowers are generally useful
        if (tile.type === TILE_TYPES.FLOWER) {
          score += 3;
        }

        return { tile, score };
      })
      .sort((a, b) => a.score - b.score);

    return scored.slice(0, 3).map(s => s.tile);
  }

  /**
   * Hard: Strategic passing based on pattern analysis
   */
  hardCharlestonSelect(hand, passDirection) {
    return this.mediumCharlestonSelect(hand);
  }

  /**
   * Analyze hand for potential patterns
   */
  analyzeHand(hand) {
    const analysis = {
      suitCounts: {
        [TILE_TYPES.DOT]: 0,
        [TILE_TYPES.BAM]: 0,
        [TILE_TYPES.CRAK]: 0
      },
      pairs: [],
      trips: [],
      jokerCount: 0,
      flowerCount: 0,
      windCount: 0,
      dragonCount: 0
    };

    const counts = new Map();

    for (const tile of hand) {
      if (tile.type === TILE_TYPES.JOKER) {
        analysis.jokerCount++;
        continue;
      }

      if (tile.type === TILE_TYPES.FLOWER) {
        analysis.flowerCount++;
        continue;
      }

      if (analysis.suitCounts[tile.type] !== undefined) {
        analysis.suitCounts[tile.type]++;
      }

      if (tile.type === TILE_TYPES.WIND) analysis.windCount++;
      if (tile.type === TILE_TYPES.DRAGON) analysis.dragonCount++;

      const key = `${tile.type}-${tile.value}`;
      counts.set(key, (counts.get(key) || 0) + 1);
    }

    // Find pairs and trips
    for (const [key, count] of counts) {
      if (count >= 3) analysis.trips.push(key);
      else if (count >= 2) analysis.pairs.push(key);
    }

    return analysis;
  }

  /**
   * Decide whether to call a discarded tile
   */
  decideCall(hand, exposures, discardedTile, callOptions) {
    // First check if we can call Mah Jongg
    if (callOptions.includes(CALL_TYPES.MAH_JONGG) ||
        this.canCallMahjong(hand, exposures, discardedTile)) {
      return { type: CALL_TYPES.MAH_JONGG, tiles: [] };
    }

    switch (this.difficulty) {
      case 'easy':
        return this.easyDecideCall(hand, discardedTile, callOptions);
      case 'hard':
        return this.hardDecideCall(hand, exposures, discardedTile, callOptions);
      default:
        return this.mediumDecideCall(hand, exposures, discardedTile, callOptions);
    }
  }

  /**
   * Easy: Random chance to call
   */
  easyDecideCall(hand, discardedTile, callOptions) {
    if (callOptions.length === 0) {
      return { type: CALL_TYPES.PASS };
    }

    // 50% chance to call if possible
    if (Math.random() > 0.5) {
      return { type: CALL_TYPES.PASS };
    }

    // Pick the highest priority call
    const priority = [CALL_TYPES.QUINT, CALL_TYPES.KONG, CALL_TYPES.PUNG];
    for (const callType of priority) {
      if (callOptions.includes(callType)) {
        const meldTiles = this.findMeldTiles(hand, discardedTile, callType);
        if (meldTiles.length > 0 && hand.length - meldTiles.length >= 1) {
          return { type: callType, tiles: meldTiles };
        }
      }
    }

    return { type: CALL_TYPES.PASS };
  }

  /**
   * Medium: Call if it helps the hand and fits a pattern
   */
  mediumDecideCall(hand, exposures, discardedTile, callOptions) {
    if (callOptions.length === 0) {
      return { type: CALL_TYPES.PASS };
    }

    // Update target pattern
    this.targetPattern = this.getTargetPattern(hand, exposures);

    // Check if the discarded tile fits our target pattern
    const tileUseful = this.isTileUsefulForPattern(discardedTile, this.targetPattern, hand);

    // Always call Quint if possible and useful
    if (callOptions.includes(CALL_TYPES.QUINT)) {
      const meldTiles = this.findMeldTiles(hand, discardedTile, CALL_TYPES.QUINT);
      if (meldTiles.length > 0 && hand.length - meldTiles.length >= 1) {
        return { type: CALL_TYPES.QUINT, tiles: meldTiles };
      }
    }

    // Call Kong if useful for pattern
    if (callOptions.includes(CALL_TYPES.KONG) && tileUseful) {
      const meldTiles = this.findMeldTiles(hand, discardedTile, CALL_TYPES.KONG);
      if (meldTiles.length > 0 && hand.length - meldTiles.length >= 1) {
        return { type: CALL_TYPES.KONG, tiles: meldTiles };
      }
    }

    // Call Pung if useful for pattern (70% of the time)
    if (callOptions.includes(CALL_TYPES.PUNG) && tileUseful && Math.random() < 0.7) {
      const meldTiles = this.findMeldTiles(hand, discardedTile, CALL_TYPES.PUNG);
      if (meldTiles.length > 0 && hand.length - meldTiles.length >= 1) {
        return { type: CALL_TYPES.PUNG, tiles: meldTiles };
      }
    }

    return { type: CALL_TYPES.PASS };
  }

  /**
   * Hard: Strategic calling based on pattern analysis
   */
  hardDecideCall(hand, exposures, discardedTile, callOptions) {
    return this.mediumDecideCall(hand, exposures, discardedTile, callOptions);
  }

  /**
   * Find tiles in hand to form a meld with the discarded tile
   */
  findMeldTiles(hand, discardedTile, callType) {
    const matching = hand.filter(
      t => t.type === discardedTile.type && t.value === discardedTile.value
    );

    const jokers = hand.filter(t => t.type === TILE_TYPES.JOKER);

    switch (callType) {
      case CALL_TYPES.PUNG:
        // Need 2 matching (discarded tile is the 3rd)
        if (matching.length >= 2) {
          return matching.slice(0, 2);
        }
        // Use jokers if needed
        if (matching.length === 1 && jokers.length >= 1) {
          return [matching[0], jokers[0]];
        }
        if (matching.length === 0 && jokers.length >= 2) {
          return jokers.slice(0, 2);
        }
        break;

      case CALL_TYPES.KONG:
        // Need 3 matching
        if (matching.length >= 3) {
          return matching.slice(0, 3);
        }
        // Use jokers
        const kongTiles = [...matching];
        let jokersNeeded = 3 - matching.length;
        for (let i = 0; i < jokersNeeded && i < jokers.length; i++) {
          kongTiles.push(jokers[i]);
        }
        if (kongTiles.length === 3) return kongTiles;
        break;

      case CALL_TYPES.QUINT:
        // Need 4 matching
        const quintTiles = [...matching];
        let quintJokersNeeded = 4 - matching.length;
        for (let i = 0; i < quintJokersNeeded && i < jokers.length; i++) {
          quintTiles.push(jokers[i]);
        }
        if (quintTiles.length === 4) return quintTiles;
        break;
    }

    return [];
  }

  /**
   * Decide which tile to discard
   */
  selectDiscard(hand, exposures) {
    if (!hand || hand.length === 0) {
      return null;
    }

    switch (this.difficulty) {
      case 'easy':
        return this.easySelectDiscard(hand);
      case 'hard':
        return this.hardSelectDiscard(hand, exposures);
      default:
        return this.mediumSelectDiscard(hand, exposures);
    }
  }

  /**
   * Easy: Discard random tile (not jokers)
   */
  easySelectDiscard(hand) {
    const nonJokers = hand.filter(t => t.type !== TILE_TYPES.JOKER);
    if (nonJokers.length === 0) return hand[0];
    return nonJokers[Math.floor(Math.random() * nonJokers.length)];
  }

  /**
   * Medium: Discard tiles that don't fit the target pattern
   */
  mediumSelectDiscard(hand, exposures) {
    if (!hand || hand.length === 0) {
      return null;
    }

    // Update target pattern
    this.targetPattern = this.getTargetPattern(hand, exposures);

    const scored = hand
      .filter(t => t.type !== TILE_TYPES.JOKER) // Never discard jokers
      .map(tile => {
        let score = 0;

        // If useful for pattern, higher score (keep it)
        if (this.isTileUsefulForPattern(tile, this.targetPattern, hand)) {
          score += 10;
        }

        // Count duplicates (more = better to keep)
        const sameCount = hand.filter(
          t => t.type === tile.type && t.value === tile.value
        ).length;
        score += sameCount * 3;

        // Flowers can be useful for many patterns
        if (tile.type === TILE_TYPES.FLOWER) {
          score += 2;
        }

        // Winds/dragons - keep pairs
        if (tile.type === TILE_TYPES.WIND || tile.type === TILE_TYPES.DRAGON) {
          if (sameCount >= 2) score += 4;
        }

        return { tile, score };
      })
      .sort((a, b) => a.score - b.score);

    if (scored.length === 0) {
      return hand[0]; // Fallback
    }

    return scored[0].tile;
  }

  /**
   * Hard: Strategic discard based on pattern analysis
   */
  hardSelectDiscard(hand, exposures) {
    return this.mediumSelectDiscard(hand, exposures);
  }

  /**
   * Record a discard (for tracking)
   */
  recordDiscard(tile, playerIndex) {
    this.discardMemory.push({ tile, playerIndex, turn: this.discardMemory.length });
  }

  /**
   * Check what possible calls can be made with hand + discard
   */
  getPossibleCalls(hand, discardedTile) {
    const calls = [];

    // Count matching tiles
    const matching = hand.filter(
      t => t.type === discardedTile.type && t.value === discardedTile.value
    );
    const jokers = hand.filter(t => t.type === TILE_TYPES.JOKER);

    // Can't call flowers with jokers
    if (discardedTile.type === TILE_TYPES.FLOWER) {
      return calls;
    }

    // Check for Pung (need 2 in hand + discard)
    if (matching.length >= 2 || (matching.length >= 1 && jokers.length >= 1) || jokers.length >= 2) {
      calls.push(CALL_TYPES.PUNG);
    }

    // Check for Kong (need 3 in hand + discard)
    if (matching.length >= 3 || matching.length + jokers.length >= 3) {
      calls.push(CALL_TYPES.KONG);
    }

    // Check for Quint (need 4 in hand + discard)
    if (matching.length >= 4 || matching.length + jokers.length >= 4) {
      calls.push(CALL_TYPES.QUINT);
    }

    return calls;
  }
}

module.exports = BotPlayer;
