import json
import io
import traceback
from contextlib import redirect_stdout, redirect_stderr
import math
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


ALLOWED_MODULES = {
    "math",
    "json",
    "datetime",
    "random",
    "statistics",
    "re",
    "collections",
    "itertools",
    "string",
    "decimal",
    "fractions",
    "uuid",
    "hashlib",
    "base64",
    "textwrap",
}


def safe_import(name, *args, **kwargs):
    if name in ALLOWED_MODULES:
        return __import__(name, *args, **kwargs)
    raise ImportError(f"Module '{name}' is not allowed")


SAFE_BUILTINS = {
    "__import__": safe_import,
    "print": print,
    "len": len,
    "range": range,
    "str": str,
    "int": int,
    "float": float,
    "list": list,
    "dict": dict,
    "set": set,
    "tuple": tuple,
    "sum": sum,
    "max": max,
    "min": min,
    "abs": abs,
    "round": round,
    "sorted": sorted,
    "enumerate": enumerate,
    "zip": zip,
    "map": map,
    "filter": filter,
    "any": any,
    "all": all,
    "bool": bool,
    "bytes": bytes,
    "chr": chr,
    "ord": ord,
    "hex": hex,
    "oct": oct,
    "bin": bin,
    "pow": pow,
    "divmod": divmod,
    "isinstance": isinstance,
    "issubclass": issubclass,
    "type": type,
}


SAFE_GLOBALS = {
    "__builtins__": SAFE_BUILTINS,
    "math": math,
    "json": json,
    "datetime": datetime,
    "random": random,
    "statistics": statistics,
    "re": re,
    "collections": collections,
    "itertools": itertools,
    "string": string,
    "decimal": decimal,
    "fractions": fractions,
    "uuid": uuid,
    "hashlib": hashlib,
    "base64": base64,
    "textwrap": textwrap,
}


def lambda_handler(event, context):
    code = event.get("code", "")
    timeout = event.get("timeout", 20)
    if not code:
        return {"statusCode": 400, "body": json.dumps({"error": "No code provided"})}

    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()

    try:
        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            exec(code, SAFE_GLOBALS)

        return {
            "statusCode": 200,
            "body": json.dumps(
                {"output": stdout_capture.getvalue(), "errors": stderr_capture.getvalue() or None, "success": True}
            ),
        }
    except Exception as exc:  # pylint: disable=broad-except
        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "output": stdout_capture.getvalue(),
                    "errors": f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}",
                    "success": False,
                }
            ),
        }
