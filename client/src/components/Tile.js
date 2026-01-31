import React from 'react';
import './Tile.css';

// Tile display mappings
const TILE_SYMBOLS = {
  // Dots (circles)
  dot: {
    1: '🀙', 2: '🀚', 3: '🀛', 4: '🀜', 5: '🀝',
    6: '🀞', 7: '🀟', 8: '🀠', 9: '🀡'
  },
  // Bams (bamboo)
  bam: {
    1: '🀐', 2: '🀑', 3: '🀒', 4: '🀓', 5: '🀔',
    6: '🀕', 7: '🀖', 8: '🀗', 9: '🀘'
  },
  // Craks (characters)
  crak: {
    1: '🀇', 2: '🀈', 3: '🀉', 4: '🀊', 5: '🀋',
    6: '🀌', 7: '🀍', 8: '🀎', 9: '🀏'
  },
  // Winds
  wind: {
    east: '🀀', south: '🀁', west: '🀂', north: '🀃'
  },
  // Dragons
  dragon: {
    red: '🀄', green: '🀅', white: '🀆'
  },
  // Flowers (using generic flower symbol)
  flower: {
    1: '🌸', 2: '🌼', 3: '🌺', 4: '🌻',
    5: '🌷', 6: '🌹', 7: '💐', 8: '🌿'
  },
  // Joker
  joker: {
    joker: '🃏'
  },
  // Blank (wild exchange tile)
  blank: {
    blank: '⬜'
  }
};

// Text labels for tiles
const TILE_LABELS = {
  dot: (v) => `${v} DOT`,
  bam: (v) => `${v} BAM`,
  crak: (v) => `${v} CRAK`,
  wind: (v) => v.toUpperCase(),
  dragon: (v) => v === 'white' ? 'SOAP' : v.toUpperCase(),
  flower: (v) => `FLOWER ${v}`,
  joker: () => 'JOKER',
  blank: () => 'BLANK'
};

// Short labels for smaller tiles
const TILE_SHORT_LABELS = {
  dot: (v) => `${v}D`,
  bam: (v) => `${v}B`,
  crak: (v) => `${v}C`,
  wind: (v) => v.charAt(0).toUpperCase(),
  dragon: (v) => v === 'white' ? 'Wh' : v.charAt(0).toUpperCase(),
  flower: (v) => `F${v}`,
  joker: () => 'J',
  blank: () => 'BL'
};

function Tile({
  tile,
  hidden = false,
  selected = false,
  disabled = false,
  small = false,
  onClick,
  onDoubleClick,
  className = '',
  draggable = false,
  onDragStart,
  onDragOver,
  onDrop,
  onDragEnd,
  index
}) {
  if (!tile) return null;

  const handleClick = (e) => {
    // Don't trigger click if this was a drag operation
    if (e.defaultPrevented) return;
    if (!disabled && onClick) {
      onClick(tile);
    }
  };

  const handleDoubleClick = () => {
    if (!disabled && onDoubleClick) {
      onDoubleClick(tile);
    }
  };

  const handleMouseDown = (e) => {
    // Allow drag to start - don't prevent default
    if (draggable) {
      console.log('Mouse down on draggable tile', index);
    }
  };

  const handleDragStart = (e) => {
    console.log('Tile handleDragStart called', { draggable, hasOnDragStart: !!onDragStart, index });
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', index.toString());
    e.target.style.opacity = '0.5';
    if (onDragStart) {
      onDragStart(e, index);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    if (onDragOver) {
      onDragOver(e, index);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    if (onDrop) {
      onDrop(e, index);
    }
  };

  const handleDragEnd = (e) => {
    e.target.style.opacity = '1';
    if (onDragEnd) {
      onDragEnd();
    }
  };

  // Hidden tile (back of tile)
  if (hidden || tile.hidden) {
    return (
      <div className={`tile tile-hidden ${small ? 'tile-small' : ''} ${className}`}>
        <div className="tile-back">
          <div className="tile-back-pattern"></div>
        </div>
      </div>
    );
  }

  const { type, value } = tile;
  const symbol = TILE_SYMBOLS[type]?.[value];
  const label = TILE_LABELS[type]?.(value);
  const shortLabel = TILE_SHORT_LABELS[type]?.(value);

  const tileClasses = [
    'tile',
    `tile-${type}`,
    selected && 'tile-selected',
    disabled && 'tile-disabled',
    small && 'tile-small',
    onClick && 'tile-clickable',
    draggable && 'tile-draggable',
    className
  ].filter(Boolean).join(' ');

  return (
    <div
      className={tileClasses}
      onClick={handleClick}
      onDoubleClick={handleDoubleClick}
      onMouseDown={handleMouseDown}
      title={label}
      draggable={draggable}
      onDragStart={handleDragStart}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
      onDragEnd={handleDragEnd}
      data-type={type}
      data-value={value}
    >
      {/* Number badge for suited tiles */}
      {(type === 'dot' || type === 'bam' || type === 'crak') && (
        <div className="tile-number">{value}</div>
      )}

      <div className="tile-face">
        {symbol ? (
          <span className="tile-symbol">{symbol}</span>
        ) : (
          <span className="tile-text">{shortLabel}</span>
        )}
      </div>

      {/* Label at bottom */}
      <div className="tile-label">{small ? shortLabel : label}</div>
    </div>
  );
}

export default Tile;
