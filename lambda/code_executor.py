import json
import sys
import io
import traceback
from contextlib import redirect_stdout, redirect_stderr

# Import safe modules
import math
import json as json_module
import datetime
import random
import statistics
import re
import collections
import itertools
import string
import decimal
import fractions
import uuid
import hashlib
import base64
import textwrap

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
        # Create restricted globals with safe modules
        # Custom __import__ that only allows whitelisted modules
        allowed_modules = {
            'math', 'json', 'datetime', 'random', 'statistics',
            're', 'collections', 'itertools', 'string', 'decimal',
            'fractions', 'uuid', 'hashlib', 'base64', 'textwrap'
        }
        
        def safe_import(name, *args, **kwargs):
            if name in allowed_modules:
                return __import__(name, *args, **kwargs)
            raise ImportError(f"Module '{name}' is not allowed")
        
        safe_globals = {
            '__builtins__': {
                '__import__': safe_import,  # Custom import function
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
                'bool': bool,
                'bytes': bytes,
                'chr': chr,
                'ord': ord,
                'hex': hex,
                'oct': oct,
                'bin': bin,
                'pow': pow,
                'divmod': divmod,
                'isinstance': isinstance,
                'issubclass': issubclass,
                'type': type,
            },
            # Pre-imported safe modules (can be used directly without import)
            'math': math,
            'json': json_module,
            'datetime': datetime,
            'random': random,
            'statistics': statistics,
            're': re,
            'collections': collections,
            'itertools': itertools,
            'string': string,
            'decimal': decimal,
            'fractions': fractions,
            'uuid': uuid,
            'hashlib': hashlib,
            'base64': base64,
            'textwrap': textwrap,
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
