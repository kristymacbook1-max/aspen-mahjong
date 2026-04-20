import React from 'react';
import './Resources.css';

const podcasts = [
  {
    title: 'The AI Daily Brief: Artificial Intelligence News',
    description:
      'A daily podcast covering the latest news, analysis, and discussions on artificial intelligence and how it is reshaping the world.',
    url: 'https://podcasts.apple.com/us/podcast/the-ai-daily-brief-artificial-intelligence-news/id1680633614?i=1000762057092',
    icon: '🎙️'
  }
];

function Resources() {
  return (
    <div className="resources-page">
      <section className="resources-header">
        <h1>Resources</h1>
        <p className="resources-subtitle">
          Recommended listens and reads for our community
        </p>
      </section>

      <section className="resources-section">
        <h2>Podcasts</h2>
        <div className="resources-grid">
          {podcasts.map((item) => (
            <a
              key={item.url}
              href={item.url}
              target="_blank"
              rel="noopener noreferrer"
              className="resource-card"
            >
              <div className="resource-icon">{item.icon}</div>
              <h3>{item.title}</h3>
              <p>{item.description}</p>
              <span className="resource-link">Listen on Apple Podcasts →</span>
            </a>
          ))}
        </div>
      </section>
    </div>
  );
}

export default Resources;
