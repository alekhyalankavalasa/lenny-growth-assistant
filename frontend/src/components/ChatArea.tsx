import React, { useState, useRef, useEffect } from 'react';
import { Message, Source } from '../lib/api';
import { renderMarkdown } from '../lib/sanitize';

interface ChatAreaProps {
  messages: Message[];
  isStreaming: boolean;
  onSendMessage: (content: string, skill: string | null) => void;
  onOpenArtifact: (artifactId: string) => void;
}

export const ChatArea: React.FC<ChatAreaProps> = ({
  messages,
  isStreaming,
  onSendMessage,
  onOpenArtifact,
}) => {
  const [input, setInput] = useState('');
  const [selectedSkill, setSelectedSkill] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom when messages change or streaming happens
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isStreaming]);

  // Focus input on load
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSubmit = () => {
    const trimmed = input.trim();
    if (!trimmed || isStreaming) return;
    
    onSendMessage(trimmed, selectedSkill);
    setInput('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const renderSources = (sources: Source[] | null) => {
    if (!sources || sources.length === 0) return null;
    return (
      <div className="message-sources">
        {sources.map((src, i) => (
          <div key={i} className="source-chip" title={src.excerpt}>
            📚 {src.episode_title}
          </div>
        ))}
      </div>
    );
  };

  const formatTime = (isoString: string) => {
    try {
      const d = new Date(isoString);
      return d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
    } catch {
      return '';
    }
  };

  return (
    <div className="chat-area">
      <div className="chat-header">
        <div className="chat-header-title">
          Chat Session
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="6 9 12 15 18 9"></polyline></svg>
        </div>
        <div className="chat-header-subtitle">Lenny Growth Assistant</div>
      </div>

      <div className="chat-messages">
        {messages.length === 0 ? (
          <div className="chat-empty">
            <div className="chat-empty-icon">✨</div>
            <h2>What do you want to learn?</h2>
            <p>I'm trained on Lenny's podcast and newsletters. Ask me a question or ask me to write a new essay.</p>
            <div className="chat-empty-suggestions">
              <button className="suggestion-btn" onClick={() => onSendMessage("What is the difference between PLG and sales-led growth?", "grounded_qa")}>
                What is the difference between PLG and sales-led growth?
              </button>
              <button className="suggestion-btn" onClick={() => onSendMessage("Write a Ship 30 essay about why retention is more important than acquisition.", "ship30_essay")}>
                Write a Ship 30 essay about retention vs acquisition.
              </button>
            </div>
          </div>
        ) : (
          messages.map((msg, index) => {
            const isLast = index === messages.length - 1;
            const showCursor = isLast && isStreaming && msg.role === 'assistant';
            
            return (
              <div key={msg.id || index} className={`message ${msg.role}`}>
                <div className="message-avatar">
                  {msg.role === 'user' ? 'U' : '✨'}
                </div>
                <div className="message-body">
                  <div className="message-header">
                    <span className="message-role">
                      {msg.role === 'user' ? 'You' : 'Assistant'}
                    </span>
                    {msg.skill_used && (
                      <span className={`skill-badge ${msg.skill_used === 'ship30_essay' ? 'ship30' : 'grounded-qa'}`}>
                        {msg.skill_used === 'ship30_essay' ? 'Ship 30 Essay' : 'Q&A'}
                      </span>
                    )}
                    <span className="message-time">
                      {formatTime(msg.created_at)}
                    </span>
                  </div>
                  
                  <div className="message-content">
                    {msg.role === 'assistant' ? (
                      <>
                        {msg.content ? (
                          <div dangerouslySetInnerHTML={{ __html: renderMarkdown(msg.content) }} />
                        ) : (
                          isStreaming && isLast ? (
                            <div className="thinking-animation">
                              <span className="dot"></span>
                              <span className="dot"></span>
                              <span className="dot"></span>
                            </div>
                          ) : null
                        )}
                        {showCursor && msg.content && <span className="streaming-cursor" />}
                      </>
                    ) : (
                      <div>{msg.content}</div>
                    )}
                  </div>

                  {msg.role === 'assistant' && renderSources(msg.sources)}

                  {msg.artifact_id && (
                    <button 
                      className="artifact-link-btn"
                      onClick={() => onOpenArtifact(msg.artifact_id!)}
                    >
                      📄 Open Generated Essay
                    </button>
                  )}
                </div>
              </div>
            );
          })
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="input-area">
        <div className="input-wrapper">
          <div className="input-top">
            <button className="btn-attachment">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"></path></svg>
            </button>
            <textarea
              ref={inputRef}
              className="chat-input"
              placeholder="Message Lenny..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isStreaming}
              rows={1}
            />
            <button 
              className="btn-send"
              onClick={handleSubmit}
              disabled={!input.trim() || isStreaming}
              title="Send (Enter)"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="22" y1="2" x2="11" y2="13"></line>
                <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
              </svg>
            </button>
          </div>
          <div className="input-bottom">
            <div className="skill-selector">
              <select 
                className="skill-select"
                value={selectedSkill || ''}
                onChange={(e) => setSelectedSkill(e.target.value || null)}
                disabled={isStreaming}
              >
                <option value="">✨ Auto-detect</option>
                <option value="grounded_qa">📚 Q&A</option>
                <option value="ship30_essay">📝 Ship 30 Essay</option>
              </select>
            </div>
            <div className="input-hint">Shift+Enter for newline</div>
          </div>
        </div>
      </div>
    </div>
  );
};
