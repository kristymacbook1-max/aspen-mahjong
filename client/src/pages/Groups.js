import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import './Groups.css';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000/api';

function Groups() {
  const { token } = useAuth();
  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newGroupName, setNewGroupName] = useState('');
  const [newGroupDescription, setNewGroupDescription] = useState('');

  useEffect(() => {
    fetchGroups();
  }, []);

  const fetchGroups = async () => {
    try {
      const response = await fetch(`${API_URL}/groups`, {
        headers: {
          Authorization: `Bearer ${token}`
        }
      });
      const data = await response.json();
      setGroups(data.groups || []);
    } catch (error) {
      console.error('Error fetching groups:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateGroup = async (e) => {
    e.preventDefault();
    if (!newGroupName.trim()) return;

    try {
      const response = await fetch(`${API_URL}/groups`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          name: newGroupName,
          description: newGroupDescription
        })
      });

      if (response.ok) {
        setShowCreateModal(false);
        setNewGroupName('');
        setNewGroupDescription('');
        fetchGroups();
      }
    } catch (error) {
      console.error('Error creating group:', error);
    }
  };

  if (loading) {
    return (
      <div className="groups-page">
        <div className="loading-spinner"></div>
      </div>
    );
  }

  return (
    <div className="groups-page">
      <div className="groups-header">
        <h1>My Groups</h1>
        <button
          className="btn btn-primary"
          onClick={() => setShowCreateModal(true)}
        >
          Create Group
        </button>
      </div>

      {groups.length === 0 ? (
        <div className="empty-groups">
          <div className="empty-icon">👥</div>
          <h3>No Groups Yet</h3>
          <p>Create a group to organize games with your friends</p>
          <button
            className="btn btn-primary"
            onClick={() => setShowCreateModal(true)}
          >
            Create Your First Group
          </button>
        </div>
      ) : (
        <div className="groups-grid">
          {groups.map((group) => (
            <div key={group.id} className="group-card">
              <h3>{group.name}</h3>
              {group.description && (
                <p className="group-description">{group.description}</p>
              )}
              <div className="group-meta">
                <span>{group.member_count} members</span>
                <span className="group-role">{group.role}</span>
              </div>
              <button className="btn btn-secondary btn-small">
                View Group
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Create Group Modal */}
      {showCreateModal && (
        <div className="modal-overlay" onClick={() => setShowCreateModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Create Group</h2>
              <button
                className="modal-close"
                onClick={() => setShowCreateModal(false)}
              >
                ×
              </button>
            </div>

            <form onSubmit={handleCreateGroup}>
              <div className="input-group">
                <label>Group Name *</label>
                <input
                  type="text"
                  value={newGroupName}
                  onChange={(e) => setNewGroupName(e.target.value)}
                  placeholder="e.g., Friday Night Mahjong"
                  required
                />
              </div>

              <div className="input-group">
                <label>Description</label>
                <textarea
                  value={newGroupDescription}
                  onChange={(e) => setNewGroupDescription(e.target.value)}
                  placeholder="Tell members about this group..."
                  rows={3}
                />
              </div>

              <button type="submit" className="btn btn-primary btn-full">
                Create Group
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default Groups;
