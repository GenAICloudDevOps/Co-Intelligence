import json
import sys
import io
import traceback
from contextlib import redirect_stdout, redirect_stderr

def lambda_handler(event, context):
    """Execute Python code safely and return output"""
    
    code = event.get('code', '')
    timeout = event.get('timeout', 30)
    
    if not code:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'No code provided'})
        }
    
    # Capture stdout and stderr
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()
    
    try:
        # Create restricted globals (no dangerous imports)
        safe_globals = {
            '__builtins__': {
                'print': print,
                'len': len,
                'range': range,
                'str': str,
                'int': int,
                'float': float,
                'list': list,
                'dict': dict,
                'set': set,
                'tuple': tuple,
                'sum': sum,
                'max': max,
                'min': min,
                'abs': abs,
                'round': round,
                'sorted': sorted,
                'enumerate': enumerate,
                'zip': zip,
                'map': map,
                'filter': filter,
                'any': any,
                'all': all,
            }
        }
        
        # Execute code with captured output
        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            exec(code, safe_globals)
        
        output = stdout_capture.getvalue()
        errors = stderr_capture.getvalue()
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'output': output,
                'errors': errors if errors else None,
                'success': True
            })
        }
        
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'output': stdout_capture.getvalue(),
                'errors': error_msg,
                'success': False
            })
        }
