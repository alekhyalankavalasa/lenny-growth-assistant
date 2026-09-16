"""
Explicit skill router — routes a user message to the correct skill.
Routing is keyword-based + intent-check. Fully logged and inspectable.
"""
import re
import structlog

logger = structlog.get_logger(__name__)

# Keywords that trigger the Ship 30 essay skill
SHIP30_TRIGGERS = [
    r"\bship\s*30\b",
    r"\bwrite\s+(an?\s+)?essay\b",
    r"\bwrite\s+(an?\s+)?post\b",
    r"\blong[-\s]?form\b",
    r"\bdraft\s+(an?\s+)?article\b",
    r"\bwrite\s+(an?\s+)?newsletter\b",
    r"\bwrite\s+(an?\s+)?piece\b",
    r"\bcontent\s+generation\b",
    r"\bgenerate\s+(an?\s+)?essay\b",
    r"\bgenerate\s+(an?\s+)?article\b",
]

SHIP30_PATTERN = re.compile("|".join(SHIP30_TRIGGERS), re.IGNORECASE)


def route_message(message: str, skill_override: str | None = None) -> str:
    """
    Determine which skill to use for the given user message.

    Args:
        message: The user's input text
        skill_override: Optional explicit override ('grounded_qa' | 'ship30_essay')

    Returns:
        Skill name: 'grounded_qa' | 'ship30_essay'
    """
    # Respect explicit override from UI
    if skill_override in ("grounded_qa", "ship30_essay"):
        logger.info(
            "router.skill_selected",
            skill=skill_override,
            reason="explicit_override",
            message_preview=message[:80],
        )
        return skill_override

    # Keyword-based routing
    if SHIP30_PATTERN.search(message):
        logger.info(
            "router.skill_selected",
            skill="ship30_essay",
            reason="keyword_match",
            message_preview=message[:80],
        )
        return "ship30_essay"

    # Default: grounded Q&A
    logger.info(
        "router.skill_selected",
        skill="grounded_qa",
        reason="default",
        message_preview=message[:80],
    )
    return "grounded_qa"
