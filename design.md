# Design & UI/UX Principles: The Lenny Growth Assistant

## 1. UI/UX Principles
- **Conversational Forward:** The chat interface is the primary mechanism for interaction. It needs to feel fast, responsive, and familiar to users of tools like ChatGPT or Claude.
- **Side-by-Side Artifacts:** Generating long-form content (like the Ship 30 essay) directly into the chat stream breaks the flow. The Artifact Viewer opens a dedicated side panel for rendering rich Markdown and HTML without losing the chat context.
- **Graceful Degradation:** If the local Ollama model fails, or if a retrieval yields no results, the UI must explain *why* rather than failing silently or returning a 500 error.
- **Grounded Transparency:** The user should immediately see *where* an answer came from. Source pills/citations are a critical part of the UI to build trust.

## 2. Information Architecture
- **Left Sidebar:** Session management. Allows users to start new chats, switch between historical contexts, and see the currently active LLM provider.
- **Main Chat Area:** The central column for the conversational flow. It supports markdown rendering, streaming text, and source citations.
- **Right Artifact Panel:** (Conditional) Appears when a specialized skill (like the Ship 30 content generator) produces a standalone document.

## 3. Key Interaction States
- **Empty State:** A welcoming screen with suggestions on what to ask, establishing the boundaries of the assistant's knowledge.
- **Streaming State:** Real-time text generation to reduce perceived latency, especially important when running local Ollama models on CPU.
- **Artifact Generation State:** A clear visual indicator that the agent is using a specific tool or skill, followed by the slide-in of the artifact panel.
- **Error State:** Dismissible, user-friendly banners for backend connectivity issues or LLM timeouts.

## 4. Responsive Behavior
- **Desktop (≥ 1024px):** Three-column layout possible (Sidebar, Chat, Artifact).
- **Tablet (768px - 1023px):** Artifact viewer overlays the chat or takes up the majority of the screen, pushing chat to a minimized view.
- **Mobile (< 768px):** Single column view. Sidebar is accessible via a hamburger menu. The Artifact viewer takes full screen when active, with a prominent "Back to chat" button.

## 5. Accessibility Considerations
- **Semantic HTML:** Proper use of `<main>`, `<aside>`, `<nav>`, and heading hierarchies.
- **Contrast:** High contrast ratios for text (exceeding WCAG AA standards) in both light and dark modes.
- **Keyboard Navigation:** All interactive elements (buttons, session links, artifact toggles) are focusable and triggerable via `Enter` or `Space`.
- **Screen Readers:** Use of `aria-live="polite"` for incoming chat streams to announce when the model finishes responding.

## 6. Security Design Decisions
- **Artifact Sanitization:** Generated HTML artifacts are treated as untrusted. They are sanitized on the backend using `bleach` and rendered on the frontend using `DOMPurify`. Furthermore, they are sandboxed inside an iframe with `allow-same-origin` to prevent script execution, fulfilling the strict security expectation.
