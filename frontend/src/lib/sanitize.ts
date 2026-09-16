/**
 * Client-side Markdown rendering with DOMPurify sanitization.
 * HTML artifacts are rendered in sandboxed iframes (see ArtifactViewer).
 *
 * What this sanitizer PERMITS:
 *   - All standard Markdown elements (headings, lists, code blocks, tables, links)
 *   - Bold, italic, inline code, blockquotes
 *   - HTML embedded in Markdown that passes DOMPurify allowlist
 *
 * What it BLOCKS:
 *   - <script> tags and all JS event handlers
 *   - <iframe>, <object>, <embed>, <form>
 *   - javascript: and data: URIs
 *   - Anything not in DOMPurify's default safe list
 *
 * For HTML artifacts, the iframe sandbox attribute blocks:
 *   - Script execution (no allow-scripts)
 *   - Navigation (no allow-top-navigation)
 *   - Popups (no allow-popups)
 *   - Form submission (no allow-forms)
 * See ArtifactViewer.tsx for the iframe implementation.
 */
import { marked } from 'marked';
import DOMPurify from 'dompurify';

// Configure marked for better output
marked.setOptions({
  gfm: true,
  breaks: true,
});

// DOMPurify config — strict allowlist
const PURIFY_CONFIG: DOMPurify.Config = {
  ALLOWED_TAGS: [
    'p', 'div', 'span', 'section', 'article', 'header', 'footer', 'main',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'ul', 'ol', 'li', 'dl', 'dt', 'dd',
    'strong', 'em', 'b', 'i', 'u', 's', 'del', 'ins', 'mark', 'small', 'sub', 'sup',
    'code', 'pre', 'kbd', 'samp',
    'a', 'blockquote', 'cite', 'q',
    'table', 'thead', 'tbody', 'tfoot', 'tr', 'th', 'td', 'caption',
    'br', 'hr',
  ],
  ALLOWED_ATTR: ['href', 'title', 'class', 'colspan', 'rowspan', 'scope'],
  FORBID_TAGS: ['script', 'style', 'iframe', 'object', 'embed', 'form', 'input', 'button'],
  FORBID_ATTR: ['onerror', 'onload', 'onclick', 'onmouseover', 'onfocus', 'onblur'],
  ALLOW_DATA_ATTR: false,
};

export function renderMarkdown(markdown: string): string {
  const rawHtml = marked.parse(markdown) as string;
  return DOMPurify.sanitize(rawHtml, PURIFY_CONFIG);
}

export function sanitizeHtml(html: string): string {
  return DOMPurify.sanitize(html, PURIFY_CONFIG);
}
