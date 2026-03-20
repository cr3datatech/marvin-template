import subprocess
import sys

TOOL_DEFINITIONS = [
    {
        "name": "run_tourno_error_log",
        "description": "Runs the tourno_error_log.py script from the environment and returns its output.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
]

def execute(tool_name: str, tool_input: dict, context: dict) -> str:
    if tool_name == "run_tourno_error_log":
        return _run_error_log(context)
    return f"Unknown tool: {tool_name}"

def _run_error_log(context: dict) -> str:
    try:
        result = subprocess.run(
            [sys.executable, "tourno_error_log.py"],
            capture_output=True,
            text=True,
            timeout=60
        )
        output = result.stdout.strip()
        errors = result.stderr.strip()

        response = ""
        if output:
            response += f"📋 *Output:*\n```\n{output}\n```"
        if errors:
            response += f"\n⚠️ *Stderr:*\n```\n{errors}\n```"
        if not output and not errors:
            response = "✅ Script ran successfully with no output."
        if result.returncode != 0:
            response += f"\n❌ Exit code: {result.returncode}"

        return response
    except subprocess.TimeoutExpired:
        return "❌ Script timed out after 60 seconds."
    except FileNotFoundError:
        return "❌ tourno_error_log.py not found in the current working directory."
    except Exception as e:
        return f"❌ Error running script: {str(e)}"
