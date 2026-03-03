"""
Enforce terminal runtime for code_execution_tool when skill-specific
constraints require it.

When web-app-builder (or any skill declaring runtime constraints) is loaded,
the agent MUST use runtime: "terminal" for all bash/curl steps.  LLMs
sometimes hallucinate runtime: "python" and try to import non-existent
modules.  This hook catches that mechanically — no prompt can bypass it.

Only overrides "python" and "nodejs" runtimes.  Leaves "terminal", "output",
and "reset" untouched so utility operations still work.
"""

from python.helpers.extension import Extension
from python.tools.skills_tool import DATA_NAME_LOADED_SKILLS

# Skills that require terminal-only runtime for code_execution_tool.
# Add more skill names here as needed.
TERMINAL_ONLY_SKILLS = frozenset({"web-app-builder"})

# Runtimes that should be overridden to "terminal".
WRONG_RUNTIMES = frozenset({"python", "nodejs"})


class EnforceSkillRuntimes(Extension):

    async def execute(
        self,
        tool_name: str = "",
        tool_args: dict | None = None,
        **kwargs,
    ):
        if not tool_args or tool_name != "code_execution_tool":
            return

        runtime = (tool_args.get("runtime") or "").lower().strip()
        if runtime not in WRONG_RUNTIMES:
            return  # "terminal", "output", "reset" — all fine

        loaded = self.agent.data.get(DATA_NAME_LOADED_SKILLS) or []
        if not any(skill in TERMINAL_ONLY_SKILLS for skill in loaded):
            return  # no constrained skill active

        tool_args["runtime"] = "terminal"
