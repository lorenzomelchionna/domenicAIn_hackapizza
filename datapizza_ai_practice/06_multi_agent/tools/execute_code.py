"""Safe code execution utility for agent tool use."""
import contextlib
import io

def execute_code(code: str, state: dict) -> str:
    output_buffer = io.StringIO()
    
    with contextlib.redirect_stdout(output_buffer), \
         contextlib.redirect_stderr(output_buffer):
        try:
            exec(code, state)
        except Exception as e:
            return f"Error: {e}"

    output = output_buffer.getvalue()
    return output
