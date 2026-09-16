import React, { useState, useMemo } from 'react';
import { Session } from '../lib/api';

interface SidebarProps {
  sessions: Session[];
  activeSessionId: string | null;
  onSelectSession: (id: string) => void;
  onNewChat: () => void;
  onRenameSession: (id: string, newTitle: string) => void;
  onDeleteSession: (id: string) => void;
  provider: string;
}

export const Sidebar: React.FC<SidebarProps> = ({
  sessions,
  activeSessionId,
  onSelectSession,
  onNewChat,
  onRenameSession,
  onDeleteSession,
  provider,
}) => {
  const isLocal = provider.toLowerCase().includes('ollama');
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [searchQuery, setSearchQuery] = useState('');

  const startEditing = (s: Session) => {
    setEditingSessionId(s.id);
    setEditTitle(s.title);
  };

  const handleRenameSubmit = (e: React.FormEvent, id: string) => {
    e.preventDefault();
    if (editTitle.trim()) {
      onRenameSession(id, editTitle.trim());
    }
    setEditingSessionId(null);
  };

  const formatTime = (isoString: string) => {
    try {
      const d = new Date(isoString);
      return d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
    } catch {
      return '';
    }
  };

  const formatDateLabel = (isoString: string) => {
    try {
      const d = new Date(isoString);
      return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
    } catch {
      return '';
    }
  };

  const groupedSessions = useMemo(() => {
    const groups: { [key: string]: Session[] } = {
      'Today': [],
      'Yesterday': [],
      'Previous 7 Days': [],
      'Older': []
    };

    const now = new Date();
    const todayStr = now.toDateString();
    const yesterday = new Date(now);
    yesterday.setDate(yesterday.getDate() - 1);
    const yesterdayStr = yesterday.toDateString();

    const filtered = sessions.filter(s => s.title.toLowerCase().includes(searchQuery.toLowerCase()));

    filtered.forEach(s => {
      if (!s.created_at) {
        groups['Older'].push(s);
        return;
      }
      const d = new Date(s.created_at);
      const dStr = d.toDateString();
      if (dStr === todayStr) {
        groups['Today'].push(s);
      } else if (dStr === yesterdayStr) {
        groups['Yesterday'].push(s);
      } else {
        const diffTime = Math.abs(now.getTime() - d.getTime());
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24)); 
        if (diffDays <= 7) {
          groups['Previous 7 Days'].push(s);
        } else {
          groups['Older'].push(s);
        }
      }
    });
    return groups;
  }, [sessions, searchQuery]);

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-logo">
          <div className="sidebar-logo-icon">✨</div>
          <div>
            <div className="sidebar-logo-text">Lenny Growth</div>
            <div className="sidebar-logo-sub">Assistant</div>
          </div>
        </div>
        <button className="btn-new-chat" onClick={onNewChat}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="12" y1="5" x2="12" y2="19"></line>
            <line x1="5" y1="12" x2="19" y2="12"></line>
          </svg>
          New Chat
        </button>
        
        <div className="sidebar-search">
          <svg className="search-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
          </svg>
          <input 
            type="text" 
            placeholder="Search conversations..." 
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          <svg className="settings-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="4" y1="21" x2="4" y2="14"></line><line x1="4" y1="10" x2="4" y2="3"></line>
            <line x1="12" y1="21" x2="12" y2="12"></line><line x1="12" y1="8" x2="12" y2="3"></line>
            <line x1="20" y1="21" x2="20" y2="16"></line><line x1="20" y1="12" x2="20" y2="3"></line>
            <line x1="1" y1="14" x2="7" y2="14"></line><line x1="9" y1="8" x2="15" y2="8"></line><line x1="17" y1="16" x2="23" y2="16"></line>
          </svg>
        </div>
      </div>

      <div className="sidebar-sessions">
        {['Today', 'Yesterday', 'Previous 7 Days', 'Older'].map(group => {
          const groupSessions = groupedSessions[group];
          if (groupSessions.length === 0) return null;
          
          return (
            <div key={group} className="session-group">
              <div className="session-group-title">{group}</div>
              {groupSessions.map(s => (
                <div
                  key={s.id}
                  className={`session-item ${s.id === activeSessionId ? 'active' : ''}`}
                  onClick={() => {
                      if (editingSessionId !== s.id) {
                          onSelectSession(s.id);
                      }
                  }}
                >
                  {editingSessionId === s.id ? (
                    <form onSubmit={(e) => handleRenameSubmit(e, s.id)} className="session-edit-form">
                      <input
                        type="text"
                        autoFocus
                        value={editTitle}
                        onChange={(e) => setEditTitle(e.target.value)}
                        onBlur={() => setEditingSessionId(null)}
                        className="session-edit-input"
                      />
                    </form>
                  ) : (
                    <>
                      <div className="session-item-icon">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>
                      </div>
                      <div className="session-item-title">{s.title}</div>
                      <div className="session-item-time">{group === 'Today' ? formatTime(s.created_at) : formatDateLabel(s.created_at)}</div>
                      
                      {s.id === activeSessionId && (
                        <div className="session-actions">
                          <button className="btn-icon" onClick={(e) => { e.stopPropagation(); startEditing(s); }} title="Rename">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path></svg>
                          </button>
                          <button className="btn-icon delete-icon" onClick={(e) => { e.stopPropagation(); onDeleteSession(s.id); }} title="Delete">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>
                          </button>
                        </div>
                      )}
                    </>
                  )}
                </div>
              ))}
            </div>
          );
        })}
      </div>

      <div className="sidebar-footer">
        <div className="provider-badge" title={`Active LLM Provider: ${provider}`}>
          <div className={`provider-dot ${isLocal ? 'local' : ''}`}></div>
          <div className="provider-text">Ollama<br/><span>Model ready · Local</span></div>
        </div>
      </div>
    </aside>
  );
};
