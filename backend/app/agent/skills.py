"""
Agent skills — two distinct, bounded behaviors.

Skill 1: grounded_qa
  - Retrieves relevant chunks from the knowledge base
  - Answers strictly from retrieved context, cites sources
  - Admits "I don't know" when retrieval is empty or insufficient

Skill 2: ship30_essay
  - Retrieves grounding material
  - Generates a ~1,250-word essay following Ship 30 for 30 writing principles:
    * Compelling headline
    * Strong hook (2-3 sentences, personal/relatable)
    * Narrative body: problem → insight → evidence → implication
    * Skimmable H2 headers, short paragraphs (≤3 sentences)
    * All claims grounded in retrieved transcript excerpts (cited inline)
    * Single specific takeaway at the end
  - Invokes generate_artifact to persist and render the essay
"""
from dataclasses import dataclass, field
from typing import Optional

# ─────────────────────────────────────────────────────────────────────────────
# Skill definitions
# ─────────────────────────────────────────────────────────────────────────────

GROUNDED_QA_SYSTEM = """You are the Lenny Growth Assistant — an AI assistant with deep knowledge of Lenny Rachitsky's podcast episodes and newsletter posts.

## Your Rules
1. **Ground every answer in the provided source material.** Only draw on the transcript excerpts given to you in the [SOURCES] block.
2. **Cite your sources inline.** When you make a claim, end the sentence or paragraph with a source tag like: `[Source: "Episode Title", chunk N]`
3. **Admit when you don't know.** If the retrieved sources do not contain enough information to answer the question, say:
   > "I couldn't find clear coverage of this topic in the knowledge base. Based on general product-management principles (not from Lenny's content): [brief general answer]."
   Never fabricate episode titles, quotes, or frameworks.
4. **Be specific and actionable.** Lenny's content is rich in concrete examples — reference them.
5. **Preserve session context.** Consider prior messages in this session when answering follow-up questions.

## Format
- Use markdown formatting (headers, bullet points) for readability.
- Keep answers focused: 2–5 paragraphs unless the question warrants more.
- Always end with 1–2 relevant follow-up questions the user might want to explore.
"""

SHIP30_ESSAY_SYSTEM = """You are a content strategist trained in Ship 30 for 30 writing principles. Your task is to write a ~1,250-word essay that is:

## Ship 30 for 30 Writing Principles (apply all of these)
1. **Compelling headline** — stops the scroll; specific, curiosity-driven, or counterintuitive
2. **Strong hook** — first 2-3 sentences draw the reader in with a story, surprising stat, or relatable scenario
3. **Narrative progression** — move through: Problem → Insight → Evidence → Implication
4. **Skimmable structure** — use H2 section headers, short paragraphs (≤3 sentences), and bold key phrases
5. **Grounded claims** — every major assertion must cite a specific Lenny episode or newsletter post using: `[Source: "Episode Title"]`
6. **Single specific takeaway** — end with one clear, memorable action the reader can take tomorrow
7. **~1,250 words** — aim for 1,150–1,350 words; do not pad with filler

## Your Rules
- ONLY make claims supported by the [SOURCES] provided below.
- If sources are insufficient, write what you can and clearly flag: "[Note: Limited source material available for this section]"
- Output must be valid Markdown that renders well in a web viewer.
- Do not write a generic essay. Make it feel like Lenny wrote it — data-driven, opinionated, practitioner-focused.
"""

TARGET_WORD_COUNT = 1250


@dataclass
class SkillResult:
    """Structured output from a skill execution."""
    content: str
    sources: list[dict] = field(default_factory=list)
    artifact_content: Optional[str] = None  # if skill generates an artifact
    artifact_type: Optional[str] = None     # "markdown" | "html"
    artifact_title: Optional[str] = None
    skill_name: str = "grounded_qa"


def build_grounded_qa_messages(
    user_message: str,
    history: list[dict],
    sources: list[dict],
) -> tuple[str, list[dict]]:
    """
    Build the message array for the grounded Q&A skill.
    Returns (system_prompt, messages_list).
    """
    sources_block = _format_sources_block(sources)

    messages = list(history)  # preserve session context
    messages.append({
        "role": "user",
        "content": f"{user_message}\n\n{sources_block}",
    })
    return GROUNDED_QA_SYSTEM, messages


def build_ship30_messages(
    user_message: str,
    history: list[dict],
    sources: list[dict],
) -> tuple[str, list[dict]]:
    """
    Build the message array for the Ship 30 essay skill.
    Returns (system_prompt, messages_list).
    """
    sources_block = _format_sources_block(sources)
    topic_instruction = (
        f"Write a Ship 30 for 30 essay (~{TARGET_WORD_COUNT} words) about the following topic:\n\n"
        f"{user_message}\n\n"
        f"Use the sources below as your grounding material.\n\n"
        f"{sources_block}"
    )

    messages = [{"role": "user", "content": topic_instruction}]
    return SHIP30_ESSAY_SYSTEM, messages


def _format_sources_block(sources: list[dict]) -> str:
    """Format retrieved chunks into a [SOURCES] block for the LLM."""
    if not sources:
        return "[SOURCES]\nNo relevant sources found in the knowledge base."

    lines = ["[SOURCES]"]
    for i, s in enumerate(sources, 1):
        lines.append(
            f"\n--- Source {i}: \"{s['episode_title']}\" (chunk {s['chunk_index']}) ---\n"
            f"{s['content']}"
        )
    return "\n".join(lines)
