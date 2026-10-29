import io
import sys
import traceback
from pathlib import Path
from config import STORAGE_DIR

CODE_FILES_DIR = STORAGE_DIR / "generated_code"
CODE_FILES_DIR.mkdir(parents=True, exist_ok=True)

class CodeExecutor:
    """
    Executes safe Python analytical routines and saves generated scripts.
    Matches the 'Code Generation Engine' and 'Code Executor' components.
    """
    @staticmethod
    def execute_analytics_code(code_str: str, context: dict = None) -> dict:
        if context is None:
            context = {}

        # Save generated code file for auditability
        filename = f"analytics_{abs(hash(code_str)) % 100000}.py"
        filepath = CODE_FILES_DIR / filename
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(code_str)

        old_stdout = sys.stdout
        redirected_output = io.StringIO()
        sys.stdout = redirected_output

        execution_success = False
        error_msg = ""
        result_vars = {}

        try:
            scope = {"__builtins__": __builtins__, "math": __import__("math"), "np": __import__("numpy")}
            scope.update(context)
            exec(code_str, scope)
            execution_success = True
            result_vars = {k: v for k, v in scope.items() if not k.startswith("__") and k not in ("math", "np")}
        except Exception as e:
            error_msg = traceback.format_exc()
        finally:
            sys.stdout = old_stdout

        return {
            "success": execution_success,
            "stdout": redirected_output.getvalue(),
            "error": error_msg,
            "saved_file": filename,
            "variables": str(result_vars)
        }
