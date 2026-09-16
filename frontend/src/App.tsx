import React, { useState, useEffect, useRef } from 'react';
import { Sidebar } from './components/Sidebar';
import { ChatArea } from './components/ChatArea';
import { ArtifactViewer } from './components/ArtifactViewer';
import * as api from './lib/api';

function App() {
  // State
  const [sessions, setSessions] = useState<api.Session[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<api.Message[]>([]);
  const [activeArtifact, setActiveArtifact] = useState<api.Artifact | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [health, setHealth] = useState<api.HealthStatus | null>(null);

  // Abort controller for cancelling streams
  const abortControllerRef = useRef<AbortController | null>(null);

  // Initial load
  useEffect(() => {
    loadHealth();
    loadSessions();
  }, []);

  // When active session changes, load its messages
  useEffect(() => {
    if (activeSessionId) {
      loadMessages(activeSessionId);
      // Close artifact panel on session switch
      setActiveArtifact(null);
    } else {
      setMessages([]);
    }
  }, [activeSessionId]);

  const loadHealth = async () => {
    try {
      const data = await api.getHealth();
      setHealth(data);
    } catch (err) {
      console.error("Health check failed", err);
    }
  };

  const loadSessions = async () => {
    try {
      const data = await api.listSessions();
      setSessions(data);
      if (data.length > 0 && !activeSessionId) {
        setActiveSessionId(data[0].id);
      }
    } catch (err) {
      setError("Failed to load sessions.");
    }
  };

  const loadMessages = async (sessionId: string) => {
    try {
      const data = await api.getMessages(sessionId);
      setMessages(data);
    } catch (err) {
      setError("Failed to load messages.");
    }
  };

  const handleNewChat = async () => {
    try {
      const newSession = await api.createSession('New Chat');
      setSessions([newSession, ...sessions]);
      setActiveSessionId(newSession.id);
    } catch (err) {
      setError("Failed to create new chat.");
    }
  };

  const handleSendMessage = async (content: string, skillOverride: string | null) => {
    setError(null);
    let currentSessionId = activeSessionId;

    // Create session if none exists
    if (!currentSessionId) {
      try {
        const newSession = await api.createSession(content.slice(0, 40) + '...');
        setSessions([newSession, ...sessions]);
        setActiveSessionId(newSession.id);
        currentSessionId = newSession.id;
      } catch (err) {
        setError("Failed to create session.");
        return;
      }
    }

    // Optimistically add user message and empty assistant message
    const userMsg: api.Message = {
      id: `temp-u-${Date.now()}`,
      session_id: currentSessionId,
      role: 'user',
      content: content,
      skill_used: null,
      sources: null,
      artifact_id: null,
      created_at: new Date().toISOString(),
    };
    
    const asstMsg: api.Message = {
      id: `temp-a-${Date.now()}`,
      session_id: currentSessionId,
      role: 'assistant',
      content: '',
      skill_used: null,
      sources: null,
      artifact_id: null,
      created_at: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMsg, asstMsg]);
    setIsStreaming(true);

    // Setup abort controller
    abortControllerRef.current = new AbortController();

    try {
      const stream = api.streamChat(currentSessionId, content, skillOverride, abortControllerRef.current.signal);
      
      for await (const chunk of stream) {
        setMessages(prev => {
          const newMsgs = [...prev];
          const lastMsg = newMsgs[newMsgs.length - 1];
          
          if (chunk.type === 'delta' && chunk.delta) {
            lastMsg.content += chunk.delta;
          } else if (chunk.type === 'sources' && chunk.sources) {
            lastMsg.sources = chunk.sources;
          } else if (chunk.type === 'artifact' && chunk.artifact_id) {
            lastMsg.artifact_id = chunk.artifact_id;
            lastMsg.skill_used = chunk.skill_used || lastMsg.skill_used;
            // Optionally auto-open the artifact here:
            // handleOpenArtifact(chunk.artifact_id);
          } else if (chunk.type === 'done') {
            lastMsg.skill_used = chunk.skill_used || lastMsg.skill_used;
            if (chunk.provider && health?.provider !== chunk.provider) {
                // refresh health if provider changed
                loadHealth();
            }
          } else if (chunk.type === 'error' && chunk.error) {
            throw new Error(chunk.error);
          }
          
          return newMsgs;
        });
      }
      
      // Reload sessions to get updated title
      loadSessions();
      
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        console.error("Streaming error:", err);
        setError(err.message || "An error occurred during chat.");
      }
    } finally {
      setIsStreaming(false);
      abortControllerRef.current = null;
    }
  };

  const handleOpenArtifact = async (artifactId: string) => {
    try {
      const artifact = await api.getArtifact(artifactId);
      setActiveArtifact(artifact);
    } catch (err) {
      setError("Failed to load artifact.");
    }
  };

  const handleRenameSession = async (sessionId: string, newTitle: string) => {
    try {
      await api.updateSession(sessionId, newTitle);
      setSessions(prev => prev.map(s => s.id === sessionId ? { ...s, title: newTitle } : s));
    } catch (err) {
      setError("Failed to rename session.");
    }
  };

  const handleDeleteSession = async (sessionId: string) => {
    try {
      await api.deleteSession(sessionId);
      setSessions(prev => prev.filter(s => s.id !== sessionId));
      if (activeSessionId === sessionId) {
        setActiveSessionId(null);
      }
    } catch (err) {
      setError("Failed to delete session.");
    }
  };

  return (
    <div className={`app ${!activeArtifact ? 'artifact-closed' : ''}`}>
      <Sidebar 
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelectSession={setActiveSessionId}
        onNewChat={handleNewChat}
        onRenameSession={handleRenameSession}
        onDeleteSession={handleDeleteSession}
        provider={health?.provider || 'Unknown'}
      />
      
      <main className="main-content" style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {error && (
          <div className="error-banner">
            <div>⚠️ {error}</div>
            <button onClick={() => setError(null)}>✕</button>
          </div>
        )}
        
        <ChatArea 
          messages={messages}
          isStreaming={isStreaming}
          onSendMessage={handleSendMessage}
          onOpenArtifact={handleOpenArtifact}
        />
      </main>

      {activeArtifact && (
        <ArtifactViewer 
          artifact={activeArtifact}
          onClose={() => setActiveArtifact(null)}
        />
      )}
    </div>
  );
}

export default App;
