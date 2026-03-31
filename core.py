import json
from google import genai
from config import GEMINI_API_KEY, GEMINI_MODEL, MAX_AGENT_STEPS
from prompts import SYSTEM_PROMPT
from tools_registry import get_tool_descriptions, run_tool

# Initialize Gemini once at module load
_client = genai.Client(api_key=GEMINI_API_KEY)


def _parse_agent_response(raw: str) -> dict | None:
    """
    Extract JSON from Gemini's response.
    Gemini sometimes wraps JSON in markdown code blocks — handle both.
    """
    text = raw.strip()

    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def run_agent(repo_url: str, on_step=None) -> dict:
    """
    Run the full ReAct loop for a given repo URL.

    Args:
        repo_url:  Full GitHub URL, e.g. "https://github.com/owner/repo"
        on_step:   Optional callback(step_info: dict) for streaming updates to UI.
                   Called after every tool execution so frontend can show progress.

    Returns:
        {
            "success": bool,
            "report":  str,   # the final markdown report
            "steps":   list,  # log of every tool call + result
            "error":   str,   # only if success=False
        }
    """
    system = SYSTEM_PROMPT.format(tool_descriptions=get_tool_descriptions())
    history = []
    steps_log = []

    for step_num in range(MAX_AGENT_STEPS):

        # ── REASON: ask the LLM what to do next ──────────────────────
        if not history:
            user_msg = f"Analyze this GitHub repository: {repo_url}"
        else:
            user_msg = "Continue. Call the next tool or respond with DONE if you have enough information."

        history.append({"role": "user", "parts": [user_msg]})

        prompt = system + "\n\n" + "\n".join(f"{m['role']}: {m['parts'][0]}" for m in history)
        raw_response = _client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )
        agent_text = raw_response.text
        history.append({"role": "model", "parts": [agent_text]})

        # ── PARSE the agent's JSON decision ──────────────────────────
        decision = _parse_agent_response(agent_text)

        if decision is None:
            # Gemini gave us non-JSON — skip this step and retry
            step_info = {"step": step_num + 1, "type": "parse_error", "raw": agent_text}
            steps_log.append(step_info)
            if on_step:
                on_step(step_info)
            continue

        tool_name = decision.get("tool")

        # ── CHECK if agent is done ────────────────────────────────────
        if tool_name == "DONE":
            return {
                "success": True,
                "report": decision.get("report", ""),
                "steps": steps_log,
            }

        # ── ACT: execute the tool the agent chose ────────────────────
        tool_args = decision.get("args", {})
        step_info = {
            "step": step_num + 1,
            "type": "tool_call",
            "tool": tool_name,
            "args": tool_args,
        }

        tool_result = run_tool(tool_name, tool_args)
        step_info["result_preview"] = str(tool_result)[:200]
        steps_log.append(step_info)

        if on_step:
            on_step(step_info)

        # ── OBSERVE: feed result back to agent ───────────────────────
        result_json = json.dumps(tool_result, indent=2, default=str)
        history.append({
            "role": "user",
            "parts": [f"Tool '{tool_name}' result:\n{result_json}"]
        })

    return {
        "success": False,
        "error": f"Agent did not finish within {MAX_AGENT_STEPS} steps.",
        "steps": steps_log,
        "report": "",
    }