import io
import contextlib
import traceback


def python_repl(code: str) -> dict:
    """
    Execute Python code in a restricted local namespace.
    Pre-imports: pandas as pd, numpy as np, math.
    Captures stdout. Returns {output, error, success}.
    """
    namespace = {
        "pd": __import__("pandas"),
        "np": __import__("numpy"),
        "math": __import__("math"),
    }
    stdout_capture = io.StringIO()
    try:
        with contextlib.redirect_stdout(stdout_capture):
            exec(code, namespace)
        return {
            "output": stdout_capture.getvalue(),
            "error": None,
            "success": True,
        }
    except Exception:
        return {
            "output": stdout_capture.getvalue(),
            "error": traceback.format_exc(),
            "success": False,
        }
