"""
Auto-load skills when user message matches trigger_patterns from SKILL.md frontmatter.

Runs before _65_include_loaded_skills.py so auto-loaded skills appear in the
agent's context on the same turn the user asks.  Matching is deterministic
(substring check, no LLM) — the agent cannot bypass this.

Also injects a directive telling the agent the skill is already loaded
so it skips the manual skills_tool:load call and proceeds directly.
"""

from python.helpers.extension import Extension
from python.helpers import skills as skills_helper
from python.tools.skills_tool import DATA_NAME_LOADED_SKILLS
from agent import LoopData


class AutoLoadTriggeredSkills(Extension):
    async def execute(self, loop_data: LoopData = LoopData(), **kwargs):
        # Only run on the first iteration (when user message just arrived)
        if loop_data.iteration != 0:
            return

        # Get the latest user message text
        msg = _get_last_user_text(loop_data)
        if not msg:
            return

        msg_lower = msg.lower()

        # Discover all skills that have trigger patterns
        all_skills = skills_helper.list_skills(agent=self.agent, include_content=False)

        auto_loaded = []
        for skill in all_skills:
            if not skill.triggers:
                continue

            # Check if any trigger pattern appears in the user message
            matched = any(
                trigger.lower() in msg_lower
                for trigger in skill.triggers
            )
            if not matched:
                continue

            # Auto-load this skill (same logic as skills_tool._load)
            loaded = self.agent.data.get(DATA_NAME_LOADED_SKILLS) or []
            if skill.name in loaded:
                continue  # already loaded, skip

            loaded.append(skill.name)
            self.agent.data[DATA_NAME_LOADED_SKILLS] = loaded[-5:]
            auto_loaded.append(skill.name)

        # Inject directive so the agent knows the skill is loaded and should proceed
        if auto_loaded:
            names = ", ".join(auto_loaded)
            directive = (
                f"SYSTEM: The following skill(s) were AUTO-LOADED based on your request: {names}. "
                f"The full skill instructions are in your context below. "
                f"Do NOT call skills_tool:load — the skill is already loaded. "
                f"Proceed IMMEDIATELY with the skill's mandatory sequence. "
                f"Execute ALL steps end-to-end without stopping — do not just describe what you will do, actually do it."
            )
            loop_data.extras_temporary["auto_loaded_skills_directive"] = directive


def _get_last_user_text(loop_data: LoopData) -> str:
    """Extract plain text from the most recent user message."""
    if loop_data.user_message and loop_data.user_message.content:
        content = loop_data.user_message.content
        if isinstance(content, str):
            return content
        # Handle list-of-dicts format (multimodal messages)
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    parts.append(item.get("text", ""))
                elif isinstance(item, str):
                    parts.append(item)
            return " ".join(parts)
    return ""
