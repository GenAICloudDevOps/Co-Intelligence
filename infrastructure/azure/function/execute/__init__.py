import azure.functions as func
import json
import sys
import io
import traceback
from contextlib import redirect_stdout, redirect_stderr
import math, datetime, random, statistics, re, collections, itertools
import string, decimal, fractions, uuid, hashlib, base64, textwrap

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json()
        code = body.get('code', '')
    except:
        return func.HttpResponse(json.dumps({'error': 'Invalid JSON'}), status_code=400)

    if not code:
        return func.HttpResponse(json.dumps({'error': 'No code provided'}), status_code=400)

    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()

    allowed_modules = {'math', 'json', 'datetime', 'random', 'statistics', 're', 
                       'collections', 'itertools', 'string', 'decimal', 'fractions', 
                       'uuid', 'hashlib', 'base64', 'textwrap'}

    def safe_import(name, *args, **kwargs):
        if name in allowed_modules:
            return __import__(name, *args, **kwargs)
        raise ImportError(f"Module '{name}' is not allowed")

    safe_globals = {
        '__builtins__': {
            '__import__': safe_import, 'print': print, 'len': len, 'range': range,
            'str': str, 'int': int, 'float': float, 'list': list, 'dict': dict,
            'set': set, 'tuple': tuple, 'sum': sum, 'max': max, 'min': min,
            'abs': abs, 'round': round, 'sorted': sorted, 'enumerate': enumerate,
            'zip': zip, 'map': map, 'filter': filter, 'any': any, 'all': all,
            'bool': bool, 'isinstance': isinstance, 'type': type,
        },
        'math': math, 'json': json, 'datetime': datetime, 'random': random,
        'statistics': statistics, 're': re, 'collections': collections,
        'itertools': itertools, 'string': string, 'decimal': decimal,
        'fractions': fractions, 'uuid': uuid, 'hashlib': hashlib,
        'base64': base64, 'textwrap': textwrap,
    }

    try:
        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            exec(code, safe_globals)
        return func.HttpResponse(json.dumps({
            'output': stdout_capture.getvalue(),
            'errors': stderr_capture.getvalue() or None,
            'success': True
        }))
    except Exception as e:
        return func.HttpResponse(json.dumps({
            'output': stdout_capture.getvalue(),
            'errors': f"{type(e).__name__}: {str(e)}",
            'success': False
        }))
