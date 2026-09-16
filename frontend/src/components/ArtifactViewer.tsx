import React, { useEffect, useRef, useState, useMemo } from 'react';
import { Artifact } from '../lib/api';
import { renderMarkdown, sanitizeHtml } from '../lib/sanitize';

interface ArtifactViewerProps {
  artifact: Artifact | null;
  onClose: () => void;
}

export const ArtifactViewer: React.FC<ArtifactViewerProps> = ({ artifact, onClose }) => {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [activeTab, setActiveTab] = useState<'document' | 'notes'>('document');

  // When HTML artifact updates, inject it into the sandboxed iframe
  useEffect(() => {
    if (artifact?.type === 'html' && iframeRef.current) {
      const iframe = iframeRef.current;
      const cleanHtml = sanitizeHtml(artifact.content);
      
      // Inject the sanitized HTML into the iframe document
      const doc = iframe.contentDocument || iframe.contentWindow?.document;
      if (doc) {
        doc.open();
        // Add a default style to make it look decent inside the iframe
        doc.write(`
          <!DOCTYPE html>
          <html>
            <head>
              <style>
                body { font-family: -apple-system, sans-serif; line-height: 1.6; padding: 20px; color: #f8fafc; background: #0B0E14; }
                h1, h2, h3 { color: #f8fafc; }
                a { color: #60a5fa; }
              </style>
            </head>
            <body>
              ${cleanHtml}
            </body>
          </html>
        `);
        doc.close();
      }
    }
  }, [artifact]);

  const toc = useMemo(() => {
    if (artifact?.type === 'markdown' && artifact.content) {
      return artifact.content
        .split('\n')
        .filter(line => line.trim().startsWith('## ') || line.trim().startsWith('### '))
        .map(h => h.replace(/#/g, '').trim());
    }
    return [];
  }, [artifact]);

  if (!artifact) {
    return (
      <div className="artifact-panel">
        <div className="artifact-panel-header">
          <div className="artifact-panel-title">Artifacts</div>
        </div>
        <div className="artifact-empty">
          <div className="artifact-empty-icon">📄</div>
          <p>No artifact generated yet.<br/>Ask the assistant to write an essay or draft content.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="artifact-panel">
      <div className="artifact-panel-header">
        <div className="artifact-panel-title" title={artifact.title}>
          {artifact.title}
        </div>
        <div className="artifact-type-tabs">
          <button 
            className={`artifact-tab ${activeTab === 'document' ? 'active' : ''}`}
            onClick={() => setActiveTab('document')}
          >
            Document
          </button>
          <button 
            className={`artifact-tab ${activeTab === 'notes' ? 'active' : ''}`}
            onClick={() => setActiveTab('notes')}
          >
            Notes
          </button>
        </div>
        <button className="btn-close-artifact" onClick={onClose} title="Close Artifact">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
        </button>
      </div>
      
      <div className="artifact-content-layout">
        <div className="artifact-main-content">
          {activeTab === 'notes' ? (
            <div className="artifact-notes">
              <p>Notes functionality coming soon.</p>
            </div>
          ) : artifact.type === 'markdown' ? (
            <div 
              className="artifact-markdown"
              dangerouslySetInnerHTML={{ __html: renderMarkdown(artifact.content) }}
            />
          ) : (
            <iframe
              ref={iframeRef}
              className="artifact-iframe"
              sandbox="" // Empty string = maximum restrictions
              title={artifact.title}
            />
          )}
        </div>
        
        {activeTab === 'document' && toc.length > 0 && (
          <div className="artifact-toc">
            <div className="toc-title">ON THIS PAGE</div>
            <ul className="toc-list">
              {toc.map((heading, idx) => (
                <li key={idx} className="toc-item">
                  <div className="toc-dot"></div>
                  <span>{heading}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
};
