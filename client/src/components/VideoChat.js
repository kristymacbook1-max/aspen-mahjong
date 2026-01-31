import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useSocket } from '../context/SocketContext';
import './VideoChat.css';

function VideoChat() {
  const { gameState, socketId, sendSignal, remotePeers } = useSocket();
  const [isOpen, setIsOpen] = useState(false);
  const [audioEnabled, setAudioEnabled] = useState(true);
  const [videoEnabled, setVideoEnabled] = useState(false);
  const [mode, setMode] = useState(null); // 'audio' or 'video'
  const [error, setError] = useState(null);

  const localVideoRef = useRef(null);
  const localStreamRef = useRef(null);
  const peerConnectionsRef = useRef({});
  const remoteStreamsRef = useRef({});

  // ICE servers for WebRTC - defined as useMemo to avoid dependency issues
  const iceServers = React.useMemo(() => ({
    iceServers: [
      { urls: 'stun:stun.l.google.com:19302' },
      { urls: 'stun:stun1.l.google.com:19302' },
    ]
  }), []);

  // Get human players (not bots)
  const humanPlayers = React.useMemo(() =>
    gameState?.players.filter(p => !p.isBot && p.id !== socketId) || [],
    [gameState?.players, socketId]
  );

  // Create peer connection for a player
  const createPeerConnection = useCallback((peerId) => {
    if (peerConnectionsRef.current[peerId]) return;

    const pc = new RTCPeerConnection(iceServers);
    peerConnectionsRef.current[peerId] = pc;

    // Add local stream tracks
    if (localStreamRef.current) {
      localStreamRef.current.getTracks().forEach(track => {
        pc.addTrack(track, localStreamRef.current);
      });
    }

    // Handle ICE candidates
    pc.onicecandidate = (event) => {
      if (event.candidate) {
        sendSignal(peerId, { type: 'ice-candidate', candidate: event.candidate });
      }
    };

    // Handle remote stream
    pc.ontrack = (event) => {
      remoteStreamsRef.current[peerId] = event.streams[0];
      // Force re-render
      setAudioEnabled(prev => prev);
    };

    // Create and send offer
    pc.createOffer()
      .then(offer => pc.setLocalDescription(offer))
      .then(() => {
        sendSignal(peerId, { type: 'offer', sdp: pc.localDescription });
      })
      .catch(err => console.error('Error creating offer:', err));

    return pc;
  }, [sendSignal, iceServers]);

  // Start media stream
  const startMedia = useCallback(async (withVideo) => {
    try {
      setError(null);
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: true,
        video: withVideo
      });

      localStreamRef.current = stream;
      if (localVideoRef.current) {
        localVideoRef.current.srcObject = stream;
      }

      setMode(withVideo ? 'video' : 'audio');
      setAudioEnabled(true);
      setVideoEnabled(withVideo);

      // Connect to other players
      humanPlayers.forEach(player => {
        createPeerConnection(player.id);
      });
    } catch (err) {
      console.error('Error accessing media devices:', err);
      setError('Could not access camera/microphone. Please check permissions.');
    }
  }, [humanPlayers, createPeerConnection]);

  // Handle incoming signals
  useEffect(() => {
    remotePeers.forEach(peer => {
      if (!peer.signal) return;

      const { type, sdp, candidate } = peer.signal;
      let pc = peerConnectionsRef.current[peer.id];

      if (type === 'offer') {
        if (!pc) {
          pc = new RTCPeerConnection(iceServers);
          peerConnectionsRef.current[peer.id] = pc;

          if (localStreamRef.current) {
            localStreamRef.current.getTracks().forEach(track => {
              pc.addTrack(track, localStreamRef.current);
            });
          }

          pc.onicecandidate = (event) => {
            if (event.candidate) {
              sendSignal(peer.id, { type: 'ice-candidate', candidate: event.candidate });
            }
          };

          pc.ontrack = (event) => {
            remoteStreamsRef.current[peer.id] = event.streams[0];
            setAudioEnabled(prev => prev);
          };
        }

        pc.setRemoteDescription(new RTCSessionDescription(sdp))
          .then(() => pc.createAnswer())
          .then(answer => pc.setLocalDescription(answer))
          .then(() => {
            sendSignal(peer.id, { type: 'answer', sdp: pc.localDescription });
          })
          .catch(err => console.error('Error handling offer:', err));

      } else if (type === 'answer' && pc) {
        pc.setRemoteDescription(new RTCSessionDescription(sdp))
          .catch(err => console.error('Error setting remote description:', err));

      } else if (type === 'ice-candidate' && pc) {
        pc.addIceCandidate(new RTCIceCandidate(candidate))
          .catch(err => console.error('Error adding ICE candidate:', err));
      }
    });
  }, [remotePeers, sendSignal, iceServers]);

  // Stop media
  const stopMedia = useCallback(() => {
    if (localStreamRef.current) {
      localStreamRef.current.getTracks().forEach(track => track.stop());
      localStreamRef.current = null;
    }

    Object.values(peerConnectionsRef.current).forEach(pc => pc.close());
    peerConnectionsRef.current = {};
    remoteStreamsRef.current = {};

    setMode(null);
    setIsOpen(false);
  }, []);

  // Toggle audio
  const toggleAudio = () => {
    if (localStreamRef.current) {
      const audioTrack = localStreamRef.current.getAudioTracks()[0];
      if (audioTrack) {
        audioTrack.enabled = !audioTrack.enabled;
        setAudioEnabled(audioTrack.enabled);
      }
    }
  };

  // Toggle video
  const toggleVideo = () => {
    if (localStreamRef.current) {
      const videoTrack = localStreamRef.current.getVideoTracks()[0];
      if (videoTrack) {
        videoTrack.enabled = !videoTrack.enabled;
        setVideoEnabled(videoTrack.enabled);
      }
    }
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopMedia();
    };
  }, [stopMedia]);

  // Don't show if no human players to chat with
  if (humanPlayers.length === 0 && !mode) {
    return null;
  }

  return (
    <div className={`video-chat ${isOpen ? 'open' : ''}`}>
      {!mode ? (
        <div className="video-chat-buttons">
          <button
            className="vc-toggle voice"
            onClick={() => { setIsOpen(true); startMedia(false); }}
            title="Start voice chat"
          >
            🎤
          </button>
          <button
            className="vc-toggle video"
            onClick={() => { setIsOpen(true); startMedia(true); }}
            title="Start video chat"
          >
            📹
          </button>
        </div>
      ) : (
        <div className="video-chat-container">
          <div className="vc-header">
            <h4>{mode === 'video' ? 'Video' : 'Voice'} Chat</h4>
            <button className="vc-close" onClick={stopMedia}>✕</button>
          </div>

          {error && (
            <div className="vc-error">{error}</div>
          )}

          <div className="vc-participants">
            {/* Local video */}
            {mode === 'video' && (
              <div className="vc-participant local">
                <video
                  ref={localVideoRef}
                  autoPlay
                  muted
                  playsInline
                />
                <span className="vc-name">You</span>
              </div>
            )}

            {/* Remote participants */}
            {humanPlayers.map(player => {
              const stream = remoteStreamsRef.current[player.id];
              return (
                <div key={player.id} className="vc-participant">
                  {mode === 'video' && stream ? (
                    <video
                      autoPlay
                      playsInline
                      ref={el => {
                        if (el && stream) el.srcObject = stream;
                      }}
                    />
                  ) : (
                    <div className="vc-avatar">
                      {player.name?.charAt(0).toUpperCase() || '?'}
                    </div>
                  )}
                  <span className="vc-name">{player.name}</span>
                  {stream && (
                    <span className="vc-connected">Connected</span>
                  )}
                </div>
              );
            })}
          </div>

          <div className="vc-controls">
            <button
              className={`vc-control ${!audioEnabled ? 'off' : ''}`}
              onClick={toggleAudio}
              title={audioEnabled ? 'Mute' : 'Unmute'}
            >
              {audioEnabled ? '🎤' : '🔇'}
            </button>
            {mode === 'video' && (
              <button
                className={`vc-control ${!videoEnabled ? 'off' : ''}`}
                onClick={toggleVideo}
                title={videoEnabled ? 'Turn off camera' : 'Turn on camera'}
              >
                {videoEnabled ? '📹' : '📷'}
              </button>
            )}
            <button
              className="vc-control end"
              onClick={stopMedia}
              title="End call"
            >
              📞
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default VideoChat;
