/**
 * 2025 NMJL Card Pattern Definitions
 *
 * Each pattern has:
 * - name: Display name
 * - category: Category on the card
 * - pattern: Array describing the pattern (tiles/groups)
 * - value: Point value (25 for concealed, 30 for exposed, etc.)
 * - concealed: Whether it must be concealed
 * - description: Human readable description
 *
 * Pattern notation:
 * - Numbers represent tile counts
 * - 'X' = any number (variable)
 * - 'D' = Dragon matching suit
 * - 'F' = Flower
 * - 'J' = Joker allowed in this group
 * - Suits: 'dot', 'bam', 'crak', 'any', 'any2' (two different suits), 'any3' (all three)
 *
 * This file can be replaced with 2026-nmjl.js when the new card comes out.
 */

const CARD_YEAR = 2025;

const PATTERNS = [
  // ========== 2025 Category ==========
  {
    id: '2025-1',
    name: '2025 #1',
    category: '2025',
    value: 25,
    concealed: false,
    description: 'FF 222 000 2222 5555',
    pattern: [
      { type: 'flower', count: 2 },
      { type: 'pung', value: 2, suit: 'any', jokerAllowed: true },
      { type: 'kong', value: 0, suit: 'match', jokerAllowed: true },
      { type: 'kong', value: 2, suit: 'match', jokerAllowed: true },
      { type: 'kong', value: 5, suit: 'match', jokerAllowed: true }
    ]
  },
  {
    id: '2025-2',
    name: '2025 #2',
    category: '2025',
    value: 25,
    concealed: false,
    description: '2222 0000 2222 55',
    pattern: [
      { type: 'kong', value: 2, suit: 'any', jokerAllowed: true },
      { type: 'kong', value: 0, suit: 'match', jokerAllowed: true },
      { type: 'kong', value: 2, suit: 'different', jokerAllowed: true },
      { type: 'pair', value: 5, suit: 'any', jokerAllowed: false }
    ]
  },
  {
    id: '2025-3',
    name: '2025 #3',
    category: '2025',
    value: 25,
    concealed: false,
    description: '22 00 222 000 2555',
    pattern: [
      { type: 'pair', value: 2, suit: 'any', jokerAllowed: false },
      { type: 'pair', value: 0, suit: 'match', jokerAllowed: false },
      { type: 'pung', value: 2, suit: 'different', jokerAllowed: true },
      { type: 'pung', value: 0, suit: 'match', jokerAllowed: true },
      { type: 'kong', value: [2, 5, 5, 5], suit: 'third', jokerAllowed: true }
    ]
  },
  {
    id: '2025-4',
    name: '2025 #4',
    category: '2025',
    value: 30,
    concealed: true,
    description: '20 20 25 25 (concealed)',
    pattern: [
      { type: 'pair', value: [2, 0], suit: 'any', jokerAllowed: false },
      { type: 'pair', value: [2, 0], suit: 'different', jokerAllowed: false },
      { type: 'pair', value: [2, 5], suit: 'any', jokerAllowed: false },
      { type: 'pair', value: [2, 5], suit: 'different', jokerAllowed: false }
    ]
  },

  // ========== 2468 Category ==========
  {
    id: '2468-1',
    name: '2468 #1',
    category: '2468',
    value: 25,
    concealed: false,
    description: 'FF 2222 4444 66',
    pattern: [
      { type: 'flower', count: 2 },
      { type: 'kong', value: 2, suit: 'any', jokerAllowed: true },
      { type: 'kong', value: 4, suit: 'match', jokerAllowed: true },
      { type: 'pair', value: 6, suit: 'match', jokerAllowed: false }
    ]
  },
  {
    id: '2468-2',
    name: '2468 #2',
    category: '2468',
    value: 25,
    concealed: false,
    description: 'FF 4444 6666 88',
    pattern: [
      { type: 'flower', count: 2 },
      { type: 'kong', value: 4, suit: 'any', jokerAllowed: true },
      { type: 'kong', value: 6, suit: 'match', jokerAllowed: true },
      { type: 'pair', value: 8, suit: 'match', jokerAllowed: false }
    ]
  },
  {
    id: '2468-3',
    name: '2468 #3',
    category: '2468',
    value: 25,
    concealed: false,
    description: '22 444 6666 8888',
    pattern: [
      { type: 'pair', value: 2, suit: 'any', jokerAllowed: false },
      { type: 'pung', value: 4, suit: 'match', jokerAllowed: true },
      { type: 'kong', value: 6, suit: 'match', jokerAllowed: true },
      { type: 'kong', value: 8, suit: 'match', jokerAllowed: true }
    ]
  },
  {
    id: '2468-4',
    name: '2468 #4',
    category: '2468',
    value: 25,
    concealed: false,
    description: '2222 46 46 8888',
    pattern: [
      { type: 'kong', value: 2, suit: 'any', jokerAllowed: true },
      { type: 'pair', value: [4, 6], suit: 'any', jokerAllowed: false },
      { type: 'pair', value: [4, 6], suit: 'different', jokerAllowed: false },
      { type: 'kong', value: 8, suit: 'any', jokerAllowed: true }
    ]
  },
  {
    id: '2468-5',
    name: '2468 #5',
    category: '2468',
    value: 30,
    concealed: true,
    description: '22 44 66 88 DD (any dragon, concealed)',
    pattern: [
      { type: 'pair', value: 2, suit: 'any', jokerAllowed: false },
      { type: 'pair', value: 4, suit: 'match', jokerAllowed: false },
      { type: 'pair', value: 6, suit: 'match', jokerAllowed: false },
      { type: 'pair', value: 8, suit: 'match', jokerAllowed: false },
      { type: 'pair', value: 'dragon', suit: 'any', jokerAllowed: false }
    ]
  },

  // ========== Any Like Numbers ==========
  {
    id: 'like-1',
    name: 'Like Numbers #1',
    category: 'Any Like Numbers',
    value: 25,
    concealed: false,
    description: 'FFFF XXXX XXXX (same number, 2 suits)',
    pattern: [
      { type: 'flower', count: 4 },
      { type: 'kong', value: 'X', suit: 'any', jokerAllowed: true },
      { type: 'kong', value: 'X', suit: 'different', jokerAllowed: true }
    ]
  },
  {
    id: 'like-2',
    name: 'Like Numbers #2',
    category: 'Any Like Numbers',
    value: 25,
    concealed: false,
    description: 'FF XXXX XXXX XXXX (same number, 3 suits)',
    pattern: [
      { type: 'flower', count: 2 },
      { type: 'kong', value: 'X', suit: 'any', jokerAllowed: true },
      { type: 'kong', value: 'X', suit: 'different', jokerAllowed: true },
      { type: 'kong', value: 'X', suit: 'third', jokerAllowed: true }
    ]
  },
  {
    id: 'like-3',
    name: 'Like Numbers #3',
    category: 'Any Like Numbers',
    value: 25,
    concealed: false,
    description: 'XXXX XXXX DD XXXX (same number 3 suits + matching dragon)',
    pattern: [
      { type: 'kong', value: 'X', suit: 'any', jokerAllowed: true },
      { type: 'kong', value: 'X', suit: 'different', jokerAllowed: true },
      { type: 'pair', value: 'dragon', suit: 'match', jokerAllowed: false },
      { type: 'kong', value: 'X', suit: 'third', jokerAllowed: true }
    ]
  },

  // ========== Quints ==========
  {
    id: 'quint-1',
    name: 'Quints #1',
    category: 'Quints',
    value: 35,
    concealed: false,
    description: 'XXXXX XX XXXXX (same num diff suits + pair)',
    pattern: [
      { type: 'quint', value: 'X', suit: 'any', jokerAllowed: true },
      { type: 'pair', value: 'X', suit: 'different', jokerAllowed: false },
      { type: 'quint', value: 'X', suit: 'third', jokerAllowed: true }
    ]
  },
  {
    id: 'quint-2',
    name: 'Quints #2',
    category: 'Quints',
    value: 45,
    concealed: false,
    description: 'XXXXX XXXXX DDDD (same num 2 suits + dragon kong)',
    pattern: [
      { type: 'quint', value: 'X', suit: 'any', jokerAllowed: true },
      { type: 'quint', value: 'X', suit: 'different', jokerAllowed: true },
      { type: 'kong', value: 'dragon', suit: 'any', jokerAllowed: true }
    ]
  },
  {
    id: 'quint-3',
    name: 'Quints #3',
    category: 'Quints',
    value: 55,
    concealed: false,
    description: 'XXXXXX XXXXXX DD (sextet sextet pair dragon)',
    pattern: [
      { type: 'sextet', value: 'X', suit: 'any', jokerAllowed: true },
      { type: 'sextet', value: 'X', suit: 'different', jokerAllowed: true },
      { type: 'pair', value: 'dragon', suit: 'any', jokerAllowed: false }
    ]
  },

  // ========== Consecutive Run ==========
  {
    id: 'run-1',
    name: 'Consecutive Run #1',
    category: 'Consecutive Run',
    value: 25,
    concealed: false,
    description: 'FF 1111 2222 3333',
    pattern: [
      { type: 'flower', count: 2 },
      { type: 'kong', value: 1, suit: 'any', jokerAllowed: true },
      { type: 'kong', value: 2, suit: 'match', jokerAllowed: true },
      { type: 'kong', value: 3, suit: 'match', jokerAllowed: true }
    ]
  },
  {
    id: 'run-2',
    name: 'Consecutive Run #2',
    category: 'Consecutive Run',
    value: 25,
    concealed: false,
    description: 'FF 7777 8888 9999',
    pattern: [
      { type: 'flower', count: 2 },
      { type: 'kong', value: 7, suit: 'any', jokerAllowed: true },
      { type: 'kong', value: 8, suit: 'match', jokerAllowed: true },
      { type: 'kong', value: 9, suit: 'match', jokerAllowed: true }
    ]
  },
  {
    id: 'run-3',
    name: 'Consecutive Run #3',
    category: 'Consecutive Run',
    value: 25,
    concealed: false,
    description: '11 222 3333 4444',
    pattern: [
      { type: 'pair', value: 1, suit: 'any', jokerAllowed: false },
      { type: 'pung', value: 2, suit: 'match', jokerAllowed: true },
      { type: 'kong', value: 3, suit: 'match', jokerAllowed: true },
      { type: 'kong', value: 4, suit: 'match', jokerAllowed: true }
    ]
  },
  {
    id: 'run-4',
    name: 'Consecutive Run #4',
    category: 'Consecutive Run',
    value: 25,
    concealed: false,
    description: '6666 7777 888 99',
    pattern: [
      { type: 'kong', value: 6, suit: 'any', jokerAllowed: true },
      { type: 'kong', value: 7, suit: 'match', jokerAllowed: true },
      { type: 'pung', value: 8, suit: 'match', jokerAllowed: true },
      { type: 'pair', value: 9, suit: 'match', jokerAllowed: false }
    ]
  },
  {
    id: 'run-5',
    name: 'Consecutive Run #5',
    category: 'Consecutive Run',
    value: 30,
    concealed: true,
    description: '11 22 33 44 55 66 (concealed)',
    pattern: [
      { type: 'pair', value: 1, suit: 'any', jokerAllowed: false },
      { type: 'pair', value: 2, suit: 'match', jokerAllowed: false },
      { type: 'pair', value: 3, suit: 'match', jokerAllowed: false },
      { type: 'pair', value: 4, suit: 'match', jokerAllowed: false },
      { type: 'pair', value: 5, suit: 'match', jokerAllowed: false },
      { type: 'pair', value: 6, suit: 'match', jokerAllowed: false }
    ]
  },
  {
    id: 'run-6',
    name: 'Consecutive Run #6',
    category: 'Consecutive Run',
    value: 30,
    concealed: true,
    description: '44 55 66 77 88 99 (concealed)',
    pattern: [
      { type: 'pair', value: 4, suit: 'any', jokerAllowed: false },
      { type: 'pair', value: 5, suit: 'match', jokerAllowed: false },
      { type: 'pair', value: 6, suit: 'match', jokerAllowed: false },
      { type: 'pair', value: 7, suit: 'match', jokerAllowed: false },
      { type: 'pair', value: 8, suit: 'match', jokerAllowed: false },
      { type: 'pair', value: 9, suit: 'match', jokerAllowed: false }
    ]
  },

  // ========== 13579 ==========
  {
    id: '13579-1',
    name: '13579 #1',
    category: '13579',
    value: 25,
    concealed: false,
    description: 'FF 1111 3333 55',
    pattern: [
      { type: 'flower', count: 2 },
      { type: 'kong', value: 1, suit: 'any', jokerAllowed: true },
      { type: 'kong', value: 3, suit: 'match', jokerAllowed: true },
      { type: 'pair', value: 5, suit: 'match', jokerAllowed: false }
    ]
  },
  {
    id: '13579-2',
    name: '13579 #2',
    category: '13579',
    value: 25,
    concealed: false,
    description: 'FF 5555 7777 99',
    pattern: [
      { type: 'flower', count: 2 },
      { type: 'kong', value: 5, suit: 'any', jokerAllowed: true },
      { type: 'kong', value: 7, suit: 'match', jokerAllowed: true },
      { type: 'pair', value: 9, suit: 'match', jokerAllowed: false }
    ]
  },
  {
    id: '13579-3',
    name: '13579 #3',
    category: '13579',
    value: 25,
    concealed: false,
    description: '11 333 5555 7777',
    pattern: [
      { type: 'pair', value: 1, suit: 'any', jokerAllowed: false },
      { type: 'pung', value: 3, suit: 'match', jokerAllowed: true },
      { type: 'kong', value: 5, suit: 'match', jokerAllowed: true },
      { type: 'kong', value: 7, suit: 'match', jokerAllowed: true }
    ]
  },
  {
    id: '13579-4',
    name: '13579 #4',
    category: '13579',
    value: 25,
    concealed: false,
    description: '3333 5555 777 99',
    pattern: [
      { type: 'kong', value: 3, suit: 'any', jokerAllowed: true },
      { type: 'kong', value: 5, suit: 'match', jokerAllowed: true },
      { type: 'pung', value: 7, suit: 'match', jokerAllowed: true },
      { type: 'pair', value: 9, suit: 'match', jokerAllowed: false }
    ]
  },
  {
    id: '13579-5',
    name: '13579 #5',
    category: '13579',
    value: 30,
    concealed: true,
    description: '11 33 55 77 99 DD (concealed)',
    pattern: [
      { type: 'pair', value: 1, suit: 'any', jokerAllowed: false },
      { type: 'pair', value: 3, suit: 'match', jokerAllowed: false },
      { type: 'pair', value: 5, suit: 'match', jokerAllowed: false },
      { type: 'pair', value: 7, suit: 'match', jokerAllowed: false },
      { type: 'pair', value: 9, suit: 'match', jokerAllowed: false },
      { type: 'pair', value: 'dragon', suit: 'match', jokerAllowed: false }
    ]
  },

  // ========== Winds - Dragons ==========
  {
    id: 'wd-1',
    name: 'Winds-Dragons #1',
    category: 'Winds-Dragons',
    value: 25,
    concealed: false,
    description: 'NN EE WW SS DDDD (NEWS + dragon kong)',
    pattern: [
      { type: 'pair', value: 'north', suit: 'wind', jokerAllowed: false },
      { type: 'pair', value: 'east', suit: 'wind', jokerAllowed: false },
      { type: 'pair', value: 'west', suit: 'wind', jokerAllowed: false },
      { type: 'pair', value: 'south', suit: 'wind', jokerAllowed: false },
      { type: 'kong', value: 'dragon', suit: 'any', jokerAllowed: true }
    ]
  },
  {
    id: 'wd-2',
    name: 'Winds-Dragons #2',
    category: 'Winds-Dragons',
    value: 25,
    concealed: false,
    description: 'NNNN SSSS EW EW (N/S kongs + E/W pairs)',
    pattern: [
      { type: 'kong', value: 'north', suit: 'wind', jokerAllowed: true },
      { type: 'kong', value: 'south', suit: 'wind', jokerAllowed: true },
      { type: 'pair', value: ['east', 'west'], suit: 'wind', jokerAllowed: false },
      { type: 'pair', value: ['east', 'west'], suit: 'wind', jokerAllowed: false }
    ]
  },
  {
    id: 'wd-3',
    name: 'Winds-Dragons #3',
    category: 'Winds-Dragons',
    value: 25,
    concealed: false,
    description: 'WWWW 1111 EEEE (W kong + 1s + E kong, any suit)',
    pattern: [
      { type: 'kong', value: 'west', suit: 'wind', jokerAllowed: true },
      { type: 'kong', value: 1, suit: 'any', jokerAllowed: true },
      { type: 'kong', value: 'east', suit: 'wind', jokerAllowed: true }
    ]
  },
  {
    id: 'wd-4',
    name: 'Winds-Dragons #4',
    category: 'Winds-Dragons',
    value: 30,
    concealed: true,
    description: 'RR GG 11 11 11 (dragons + 1s three suits, concealed)',
    pattern: [
      { type: 'pair', value: 'red', suit: 'dragon', jokerAllowed: false },
      { type: 'pair', value: 'green', suit: 'dragon', jokerAllowed: false },
      { type: 'pair', value: 1, suit: 'any', jokerAllowed: false },
      { type: 'pair', value: 1, suit: 'different', jokerAllowed: false },
      { type: 'pair', value: 1, suit: 'third', jokerAllowed: false }
    ]
  },

  // ========== 369 ==========
  {
    id: '369-1',
    name: '369 #1',
    category: '369',
    value: 25,
    concealed: false,
    description: 'FF 3333 6666 99',
    pattern: [
      { type: 'flower', count: 2 },
      { type: 'kong', value: 3, suit: 'any', jokerAllowed: true },
      { type: 'kong', value: 6, suit: 'match', jokerAllowed: true },
      { type: 'pair', value: 9, suit: 'match', jokerAllowed: false }
    ]
  },
  {
    id: '369-2',
    name: '369 #2',
    category: '369',
    value: 25,
    concealed: false,
    description: '33 666 6666 9999',
    pattern: [
      { type: 'pair', value: 3, suit: 'any', jokerAllowed: false },
      { type: 'pung', value: 6, suit: 'match', jokerAllowed: true },
      { type: 'kong', value: 6, suit: 'different', jokerAllowed: true },
      { type: 'kong', value: 9, suit: 'any', jokerAllowed: true }
    ]
  },
  {
    id: '369-3',
    name: '369 #3',
    category: '369',
    value: 25,
    concealed: false,
    description: '3333 66 66 9999',
    pattern: [
      { type: 'kong', value: 3, suit: 'any', jokerAllowed: true },
      { type: 'pair', value: 6, suit: 'any', jokerAllowed: false },
      { type: 'pair', value: 6, suit: 'different', jokerAllowed: false },
      { type: 'kong', value: 9, suit: 'any', jokerAllowed: true }
    ]
  },
  {
    id: '369-4',
    name: '369 #4',
    category: '369',
    value: 30,
    concealed: true,
    description: '33 66 99 33 66 99 (two suits, concealed)',
    pattern: [
      { type: 'pair', value: 3, suit: 'any', jokerAllowed: false },
      { type: 'pair', value: 6, suit: 'match', jokerAllowed: false },
      { type: 'pair', value: 9, suit: 'match', jokerAllowed: false },
      { type: 'pair', value: 3, suit: 'different', jokerAllowed: false },
      { type: 'pair', value: 6, suit: 'match', jokerAllowed: false },
      { type: 'pair', value: 9, suit: 'match', jokerAllowed: false }
    ]
  },

  // ========== Singles and Pairs ==========
  {
    id: 'sp-1',
    name: 'Singles & Pairs #1',
    category: 'Singles and Pairs',
    value: 30,
    concealed: true,
    description: 'FF 1 2 3 4 5 6 7 8 9 (one suit, concealed)',
    pattern: [
      { type: 'flower', count: 2 },
      { type: 'single', value: 1, suit: 'any', jokerAllowed: false },
      { type: 'single', value: 2, suit: 'match', jokerAllowed: false },
      { type: 'single', value: 3, suit: 'match', jokerAllowed: false },
      { type: 'single', value: 4, suit: 'match', jokerAllowed: false },
      { type: 'single', value: 5, suit: 'match', jokerAllowed: false },
      { type: 'single', value: 6, suit: 'match', jokerAllowed: false },
      { type: 'single', value: 7, suit: 'match', jokerAllowed: false },
      { type: 'single', value: 8, suit: 'match', jokerAllowed: false },
      { type: 'single', value: 9, suit: 'match', jokerAllowed: false }
    ]
  },
  {
    id: 'sp-2',
    name: 'Singles & Pairs #2',
    category: 'Singles and Pairs',
    value: 30,
    concealed: true,
    description: 'N E W S 11 22 33 (winds + 3 consecutive pairs, concealed)',
    pattern: [
      { type: 'single', value: 'north', suit: 'wind', jokerAllowed: false },
      { type: 'single', value: 'east', suit: 'wind', jokerAllowed: false },
      { type: 'single', value: 'west', suit: 'wind', jokerAllowed: false },
      { type: 'single', value: 'south', suit: 'wind', jokerAllowed: false },
      { type: 'pair', value: 1, suit: 'any', jokerAllowed: false },
      { type: 'pair', value: 2, suit: 'match', jokerAllowed: false },
      { type: 'pair', value: 3, suit: 'match', jokerAllowed: false }
    ]
  },
  {
    id: 'sp-3',
    name: 'Singles & Pairs #3',
    category: 'Singles and Pairs',
    value: 30,
    concealed: true,
    description: 'N E W S 77 88 99 (winds + 3 consecutive pairs, concealed)',
    pattern: [
      { type: 'single', value: 'north', suit: 'wind', jokerAllowed: false },
      { type: 'single', value: 'east', suit: 'wind', jokerAllowed: false },
      { type: 'single', value: 'west', suit: 'wind', jokerAllowed: false },
      { type: 'single', value: 'south', suit: 'wind', jokerAllowed: false },
      { type: 'pair', value: 7, suit: 'any', jokerAllowed: false },
      { type: 'pair', value: 8, suit: 'match', jokerAllowed: false },
      { type: 'pair', value: 9, suit: 'match', jokerAllowed: false }
    ]
  },
  {
    id: 'sp-4',
    name: 'Singles & Pairs #4',
    category: 'Singles and Pairs',
    value: 35,
    concealed: true,
    description: '1 2 3 4 5 6 7 8 9 DDDD (one suit + dragon kong, concealed)',
    pattern: [
      { type: 'single', value: 1, suit: 'any', jokerAllowed: false },
      { type: 'single', value: 2, suit: 'match', jokerAllowed: false },
      { type: 'single', value: 3, suit: 'match', jokerAllowed: false },
      { type: 'single', value: 4, suit: 'match', jokerAllowed: false },
      { type: 'single', value: 5, suit: 'match', jokerAllowed: false },
      { type: 'single', value: 6, suit: 'match', jokerAllowed: false },
      { type: 'single', value: 7, suit: 'match', jokerAllowed: false },
      { type: 'single', value: 8, suit: 'match', jokerAllowed: false },
      { type: 'single', value: 9, suit: 'match', jokerAllowed: false },
      { type: 'kong', value: 'dragon', suit: 'match', jokerAllowed: true }
    ]
  }
];

module.exports = {
  CARD_YEAR,
  PATTERNS
};
