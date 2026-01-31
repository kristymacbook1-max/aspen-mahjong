import React, { useState, useRef, useEffect } from 'react';
import { useSocket } from '../context/SocketContext';
import './ChatBox.css';

function ChatBox() {
  const { chatMessages, sendChatMessage, gameState, socketId } = useSocket();
  const [message, setMessage] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Scroll to bottom when new messages arrive
  useEffect(() => {
    if (isOpen && messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [chatMessages, isOpen]);

  // Track unread messages when chat is closed
  useEffect(() => {
    if (!isOpen && chatMessages.length > 0) {
      setUnreadCount(prev => prev + 1);
    }
  }, [chatMessages.length, isOpen]);

  // Clear unread when opening chat
  useEffect(() => {
    if (isOpen) {
      setUnreadCount(0);
      inputRef.current?.focus();
    }
  }, [isOpen]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (message.trim()) {
      sendChatMessage(message.trim());
      setMessage('');
    }
  };

  const getPlayerName = (playerId) => {
    if (!gameState) return 'Unknown';
    const player = gameState.players.find(p => p.id === playerId);
    return player?.name || 'Unknown';
  };

  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className={`chat-box ${isOpen ? 'open' : ''}`}>
      <button
        className="chat-toggle"
        onClick={() => setIsOpen(!isOpen)}
        title={isOpen ? 'Close chat' : 'Open chat'}
      >
        <span className="chat-icon">💬</span>
        {!isOpen && unreadCount > 0 && (
          <span className="unread-badge">{unreadCount}</span>
        )}
      </button>

      {isOpen && (
        <div className="chat-container">
          <div className="chat-header">
            <h4>Game Chat</h4>
            <button className="chat-close" onClick={() => setIsOpen(false)}>✕</button>
          </div>

          <div className="chat-messages">
            {chatMessages.length === 0 ? (
              <div className="chat-empty">
                <p>No messages yet. Say hello!</p>
              </div>
            ) : (
              chatMessages.map((msg, index) => (
                <div
                  key={index}
                  className={`chat-message ${msg.playerId === socketId ? 'own' : ''}`}
                >
                  <span className="message-sender">
                    {msg.playerId === socketId ? 'You' : getPlayerName(msg.playerId)}
                  </span>
                  <span className="message-text">{msg.message}</span>
                  <span className="message-time">{formatTime(msg.timestamp)}</span>
                </div>
              ))
            )}
            <div ref={messagesEndRef} />
          </div>

          <form className="chat-input-form" onSubmit={handleSubmit}>
            <input
              ref={inputRef}
              type="text"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Type a message..."
              maxLength={200}
            />
            <button type="submit" disabled={!message.trim()}>
              Send
            </button>
          </form>
        </div>
      )}
    </div>
  );
}

export default ChatBox;
