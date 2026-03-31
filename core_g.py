import json
from google import genai
from config import GEMINI_API_KEY, GEMINI_MODEL, MAX_AGENT_STEPS
from prompts import SYSTEM_PROMPT
from tools_registry import get_tool_descriptions, run_tool
from memory import build_memory_context

_client = genai.Client(api_key=GEMINI_API_KEY)


def _parse_agent_response(raw: str) -> dict | None:
    text = raw.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _build_system(repo_url: str) -> str:
    """Build system prompt with repo_url, memory context, and tool descriptions injected."""
    memory_context = build_memory_context(repo_url)
    # Replace REPO_URL_HERE placeholder in examples with the actual URL
    prompt = SYSTEM_PROMPT.format(
        tool_descriptions=get_tool_descriptions(),
        memory_context=memory_context,
        repo_url_placeholder=repo_url,
    )
    # Replace the example placeholder with real URL so Gemini copies it correctly
    prompt = prompt.replace("REPO_URL_HERE", repo_url)
    return prompt


def run_agent(repo_url: str, on_step=None) -> dict:
    system = _build_system(repo_url)
    history = []
    steps_log = []

    for step_num in range(MAX_AGENT_STEPS):

        if not history:
            user_msg = f"Analyze this GitHub repository: {repo_url}"
        else:
            user_msg = "Continue. Call the next tool or respond with DONE if you have enough information."

        history.append({"role": "user", "parts": [user_msg]})

        prompt = system + "\n\n" + "\n".join(
            f"{m['role']}: {m['parts'][0]}" for m in history
        )
        raw_response = _client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )
        agent_text = raw_response.text
        history.append({"role": "model", "parts": [agent_text]})

        decision = _parse_agent_response(agent_text)

        if decision is None:
            step_info = {"step": step_num + 1, "type": "parse_error", "raw": agent_text}
            steps_log.append(step_info)
            if on_step:
                on_step(step_info)
            continue

        tool_name = decision.get("tool")

        if tool_name == "DONE":
            return {
                "success": True,
                "report": decision.get("report", ""),
                "steps": steps_log,
            }

        tool_args = decision.get("args", {})

        # Safety net — if agent forgot repo_url, inject it
        if "repo_url" not in tool_args and tool_name != "DONE":
            tool_args["repo_url"] = repo_url

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


def run_agent_streaming(repo_url: str, on_step=None):
    system = _build_system(repo_url)
    history = []
    steps_log = []

    for step_num in range(MAX_AGENT_STEPS):

        if not history:
            user_msg = f"Analyze this GitHub repository: {repo_url}"
        else:
            user_msg = "Continue. Call the next tool or respond with DONE if you have enough information."

        history.append({"role": "user", "parts": [user_msg]})

        prompt = system + "\n\n" + "\n".join(
            f"{m['role']}: {m['parts'][0]}" for m in history
        )

        raw_response = _client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )
        agent_text = raw_response.text
        history.append({"role": "model", "parts": [agent_text]})

        decision = _parse_agent_response(agent_text)

        if decision is None:
            step_info = {"step": step_num + 1, "type": "parse_error", "raw": agent_text}
            steps_log.append(step_info)
            if on_step:
                on_step(step_info)
            continue

        tool_name = decision.get("tool")

        if tool_name == "DONE":
            report_prompt = (
                system + "\n\n"
                + "\n".join(f"{m['role']}: {m['parts'][0]}" for m in history)
                + "\n\nNow write the full structured report based on everything you gathered. "
                "Use the exact section headings specified. Write in markdown."
            )
            try:
                stream = _client.models.generate_content_stream(
                    model=GEMINI_MODEL,
                    contents=report_prompt
                )
                full_report = ""
                for chunk in stream:
                    if chunk.text:
                        full_report += chunk.text
                        yield {"type": "token", "text": chunk.text}
                yield {"type": "done", "report": full_report, "steps": steps_log}
                return
            except Exception as e:
                yield {"type": "error", "error": str(e)}
                return

        tool_args = decision.get("args", {})

        # Safety net — if agent forgot repo_url, inject it
        if "repo_url" not in tool_args and tool_name != "DONE":
            tool_args["repo_url"] = repo_url

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

        result_json = json.dumps(tool_result, indent=2, default=str)
        history.append({
            "role": "user",
            "parts": [f"Tool '{tool_name}' result:\n{result_json}"]
        })

    yield {"type": "error", "error": f"Agent did not finish within {MAX_AGENT_STEPS} steps."}