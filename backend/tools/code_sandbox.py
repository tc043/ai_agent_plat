"""
Code Sandbox Tool Adapter.
Safe Python code execution in a restricted environment.
"""

import io
import sys
import traceback
import signal
from contextlib import redirect_stdout, redirect_stderr
from backend.tools import registry


class SandboxTimeout(Exception):
    pass


def _timeout_handler(signum, frame):
    raise SandboxTimeout("Timed out (5s)")


SAFE_BUILTINS = {
    "abs": abs, "all": all, "any": any, "bin": bin, "bool": bool,
    "chr": chr, "dict": dict, "divmod": divmod, "enumerate": enumerate,
    "filter": filter, "float": float, "format": format, "frozenset": frozenset,
    "hash": hash, "hex": hex, "int": int, "isinstance": isinstance,
    "iter": iter, "len": len, "list": list, "map": map, "max": max,
    "min": min, "next": next, "oct": oct, "ord": ord, "pow": pow,
    "print": print, "range": range, "repr": repr, "reversed": reversed,
    "round": round, "set": set, "sorted": sorted, "str": str,
    "sum": sum, "tuple": tuple, "type": type, "zip": zip,
    "True": True, "False": False, "None": None,
}

SAFE_MODULES = {"math", "random", "statistics", "collections", "itertools",
                "functools", "json", "datetime", "decimal", "re", "hashlib", "base64"}

BLOCKED = ["import os", "import sys", "import subprocess", "import socket",
           "__import__", "exec(", "eval(", "open(", "globals(", "locals(",
           "getattr(", "__builtins__", "exit(", "quit("]


def execute_code(code: str = "") -> str:
    """Execute Python code in a sandboxed environment."""
    if not code.strip():
        return "Error: No code provided."

    code_check = code.lower().replace(" ", "")
    for pat in BLOCKED:
        if pat.replace(" ", "") in code_check:
            return f"🔒 Security: '{pat.strip()}' is blocked in sandbox."

    stdout_cap = io.StringIO()
    has_signal = False
    try:
        old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(5)
        has_signal = True
    except ValueError:
        # signal only works in main thread of the main interpreter
        pass

    try:
        import math, random, statistics, collections, itertools
        import functools, json as json_mod, datetime, decimal, re, hashlib, base64
        safe_globals = {"__builtins__": SAFE_BUILTINS, "math": math, "random": random,
                        "statistics": statistics, "collections": collections,
                        "itertools": itertools, "functools": functools, "json": json_mod,
                        "datetime": datetime, "decimal": decimal, "re": re,
                        "hashlib": hashlib, "base64": base64}

        with redirect_stdout(stdout_cap):
            exec(code, safe_globals)

        out = stdout_cap.getvalue()
        return f"Output:\n{out.rstrip()}" if out else "Code executed successfully (no output)."
    except SandboxTimeout:
        return "⏰ Execution timed out after 5 seconds."
    except Exception as e:
        return f"Error: {type(e).__name__}: {e}"
    finally:
        if has_signal:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)


registry.register(
    name="execute_code",
    description="Execute Python code in a secure sandbox with 5s timeout. Supports math, statistics, collections, json, datetime, regex, and more.",
    category="code",
    parameters=[{"name": "code", "type": "string", "description": "Python code to execute"}],
    examples=["Run: print('hello')", "Calculate fibonacci in Python"],
    handler=execute_code,
)
