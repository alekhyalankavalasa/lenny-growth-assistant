/**
 * API client for the Lenny Growth Assistant backend.
 * All endpoints, type definitions, and SSE streaming logic.
 */

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface Session {
  id: string;
  title: string;
  provider_used: string | null;
  created_at: string;
  updated_at: string;
}

export interface Source {
  episode_title: string;
  source_file: string;
  source_type: string;
  chunk_index: number;
  excerpt: string;
}

export interface Message {
  id: string;
  session_id: string;
  role: 'user' | 'assistant';
  content: string;
  skill_used: string | null;
  sources: Source[] | null;
  artifact_id: string | null;
  created_at: string;
}

export interface Artifact {
  id: string;
  session_id: string;
  type: 'markdown' | 'html';
  title: string;
  content: string;
  created_at: string;
}

export interface HealthStatus {
  status: string;
  provider: string;
  model: string;
  db?: { status: string };
  provider_reachable?: boolean;
}

export type SSEEventType = 'delta' | 'sources' | 'artifact' | 'done' | 'error';

export interface SSEChunk {
  type: SSEEventType;
  delta?: string;
  sources?: Source[];
  artifact_id?: string;
  artifact_title?: string;
  skill_used?: string;
  provider?: string;
  error?: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// Sessions
// ─────────────────────────────────────────────────────────────────────────────

export async function createSession(title = 'New Chat'): Promise<Session> {
  const res = await fetch(`${BASE_URL}/api/sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title }),
  });
  if (!res.ok) throw new Error(`Failed to create session: ${res.statusText}`);
  return res.json();
}

export async function listSessions(): Promise<Session[]> {
  const res = await fetch(`${BASE_URL}/api/sessions`);
  if (!res.ok) throw new Error(`Failed to list sessions: ${res.statusText}`);
  return res.json();
}

export async function getMessages(sessionId: string): Promise<Message[]> {
  const res = await fetch(`${BASE_URL}/api/sessions/${sessionId}/messages`);
  if (!res.ok) throw new Error(`Failed to get messages: ${res.statusText}`);
  return res.json();
}

export async function deleteSession(sessionId: string): Promise<void> {
  await fetch(`${BASE_URL}/api/sessions/${sessionId}`, { method: 'DELETE' });
}

export async function updateSession(sessionId: string, title: string): Promise<Session> {
  const res = await fetch(`${BASE_URL}/api/sessions/${sessionId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title }),
  });
  if (!res.ok) throw new Error(`Failed to update session: ${res.statusText}`);
  return res.json();
}

// ─────────────────────────────────────────────────────────────────────────────
// Artifacts
// ─────────────────────────────────────────────────────────────────────────────

export async function getArtifact(artifactId: string): Promise<Artifact> {
  const res = await fetch(`${BASE_URL}/api/artifacts/${artifactId}`);
  if (!res.ok) throw new Error(`Failed to get artifact: ${res.statusText}`);
  return res.json();
}

// ─────────────────────────────────────────────────────────────────────────────
// Health
// ─────────────────────────────────────────────────────────────────────────────

export async function getHealth(): Promise<HealthStatus> {
  const res = await fetch(`${BASE_URL}/health/ready`);
  return res.json();
}

// ─────────────────────────────────────────────────────────────────────────────
// Chat — SSE streaming
// ─────────────────────────────────────────────────────────────────────────────

export async function* streamChat(
  sessionId: string,
  message: string,
  skillOverride: string | null = null,
  signal?: AbortSignal,
): AsyncGenerator<SSEChunk> {
  const res = await fetch(`${BASE_URL}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      message,
      skill_override: skillOverride,
    }),
    signal,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(body.error || `HTTP ${res.status}`);
  }

  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() ?? '';

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const jsonStr = line.slice(6).trim();
        if (!jsonStr) continue;
        try {
          const chunk: SSEChunk = JSON.parse(jsonStr);
          yield chunk;
        } catch {
          // skip malformed line
        }
      }
    }
  }
}
