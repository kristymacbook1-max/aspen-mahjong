import React, { useState } from 'react';
import './NMJLCard.css';

// 2025 NMJL Card patterns organized by category
const CARD_PATTERNS = {
  '2025': [
    { name: '#1', description: 'FF 222 000 2222 5555', value: 25 },
    { name: '#2', description: '2222 0000 2222 55', value: 25 },
    { name: '#3', description: '22 00 222 000 2555', value: 25 },
    { name: '#4', description: '20 20 25 25', value: 30, concealed: true }
  ],
  '2468': [
    { name: '#1', description: 'FF 2222 4444 66', value: 25 },
    { name: '#2', description: 'FF 4444 6666 88', value: 25 },
    { name: '#3', description: '22 444 6666 8888', value: 25 },
    { name: '#4', description: '2222 46 46 8888', value: 25 },
    { name: '#5', description: '22 44 66 88 DD', value: 30, concealed: true }
  ],
  'Any Like Numbers': [
    { name: '#1', description: 'FFFF XXXX XXXX', value: 25 },
    { name: '#2', description: 'FF XXXX XXXX XXXX', value: 25 },
    { name: '#3', description: 'XXXX XXXX DD XXXX', value: 25 }
  ],
  'Quints': [
    { name: '#1', description: 'XXXXX XX XXXXX', value: 35 },
    { name: '#2', description: 'XXXXX XXXXX DDDD', value: 45 },
    { name: '#3', description: 'XXXXXX XXXXXX DD', value: 55 }
  ],
  'Consecutive Run': [
    { name: '#1', description: 'FF 1111 2222 3333', value: 25 },
    { name: '#2', description: 'FF 7777 8888 9999', value: 25 },
    { name: '#3', description: '11 222 3333 4444', value: 25 },
    { name: '#4', description: '6666 7777 888 99', value: 25 },
    { name: '#5', description: '11 22 33 44 55 66', value: 30, concealed: true },
    { name: '#6', description: '44 55 66 77 88 99', value: 30, concealed: true }
  ],
  '13579': [
    { name: '#1', description: 'FF 1111 3333 55', value: 25 },
    { name: '#2', description: 'FF 5555 7777 99', value: 25 },
    { name: '#3', description: '11 333 5555 7777', value: 25 },
    { name: '#4', description: '3333 5555 777 99', value: 25 },
    { name: '#5', description: '11 33 55 77 99 DD', value: 30, concealed: true }
  ],
  'Winds-Dragons': [
    { name: '#1', description: 'NN EE WW SS DDDD', value: 25 },
    { name: '#2', description: 'NNNN SSSS EW EW', value: 25 },
    { name: '#3', description: 'WWWW 1111 EEEE', value: 25 },
    { name: '#4', description: 'RR GG 11 11 11', value: 30, concealed: true }
  ],
  '369': [
    { name: '#1', description: 'FF 3333 6666 99', value: 25 },
    { name: '#2', description: '33 666 6666 9999', value: 25 },
    { name: '#3', description: '3333 66 66 9999', value: 25 },
    { name: '#4', description: '33 66 99 33 66 99', value: 30, concealed: true }
  ],
  'Singles and Pairs': [
    { name: '#1', description: 'FF 1 2 3 4 5 6 7 8 9', value: 30, concealed: true },
    { name: '#2', description: 'N E W S 11 22 33', value: 30, concealed: true },
    { name: '#3', description: 'N E W S 77 88 99', value: 30, concealed: true },
    { name: '#4', description: '1 2 3 4 5 6 7 8 9 DDDD', value: 35, concealed: true }
  ]
};

const CATEGORIES = Object.keys(CARD_PATTERNS);

function NMJLCard() {
  const [isOpen, setIsOpen] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState(null);

  const toggleCard = () => {
    setIsOpen(!isOpen);
    if (!isOpen) {
      setSelectedCategory(null);
    }
  };

  return (
    <div className={`nmjl-card-container ${isOpen ? 'open' : ''}`}>
      <button className="nmjl-card-toggle" onClick={toggleCard}>
        {isOpen ? '▼ Hide Card' : '▲ 2025 NMJL Card'}
      </button>

      {isOpen && (
        <div className="nmjl-card-content">
          <div className="nmjl-card-header">
            <h3>2025 NMJL Card</h3>
            <p className="nmjl-card-legend">
              <span className="legend-item">F = Flower</span>
              <span className="legend-item">D = Dragon</span>
              <span className="legend-item">X = Any #</span>
              <span className="legend-item concealed-legend">C = Concealed</span>
            </p>
          </div>

          <div className="nmjl-categories">
            {CATEGORIES.map(category => (
              <button
                key={category}
                className={`category-btn ${selectedCategory === category ? 'active' : ''}`}
                onClick={() => setSelectedCategory(selectedCategory === category ? null : category)}
              >
                {category}
              </button>
            ))}
          </div>

          {selectedCategory ? (
            <div className="nmjl-patterns">
              <h4>{selectedCategory}</h4>
              <div className="pattern-list">
                {CARD_PATTERNS[selectedCategory].map((pattern, index) => (
                  <div key={index} className={`pattern-row ${pattern.concealed ? 'concealed' : ''}`}>
                    <span className="pattern-name">{pattern.name}</span>
                    <span className="pattern-desc">{pattern.description}</span>
                    <span className="pattern-value">{pattern.value}</span>
                    {pattern.concealed && <span className="concealed-badge">C</span>}
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="nmjl-all-patterns">
              {CATEGORIES.map(category => (
                <div key={category} className="category-section">
                  <h4>{category}</h4>
                  <div className="pattern-list compact">
                    {CARD_PATTERNS[category].map((pattern, index) => (
                      <div key={index} className={`pattern-row ${pattern.concealed ? 'concealed' : ''}`}>
                        <span className="pattern-desc">{pattern.description}</span>
                        <span className="pattern-value">{pattern.value}</span>
                        {pattern.concealed && <span className="concealed-badge">C</span>}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default NMJLCard;
