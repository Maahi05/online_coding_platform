"""
Secure isolated Python code execution sandbox.
Enforces:
1. Static AST analysis to block unsafe imports, builtins, and system calls.
2. Isolated subprocess execution with strict timeouts.
3. Clean standard input/output redirection and comparison.
"""

import ast
import os
import subprocess
import sys
import tempfile
from typing import Dict, Any, List

FORBIDDEN_MODULES = {
    'os', 'subprocess', 'socket', 'shutil', 'importlib', 'pathlib',
    'pty', 'threading', 'multiprocessing', 'ctypes', 'builtins', 'posix',
    'nt', 'resource', 'signal', 'webbrowser', 'urllib', 'http', 'ftplib',
    'smtp', 'requests', 'asyncio', 'concurrent', 'inspect', 'gc', 'code',
    'codeop', 'zipfile', 'tarfile', 'pickle', 'shelve', 'dbm', 'sqlite3'
}

FORBIDDEN_CALLS = {
    'eval', 'exec', 'compile', 'open', '__import__', 'globals', 'locals',
    'getattr', 'setattr', 'delattr'
}

class SecurityViolationError(Exception):
    pass

class CodeSecurityValidator(ast.NodeVisitor):
    def __init__(self):
        self.errors: List[str] = []

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            base_module = alias.name.split('.')[0]
            if base_module in FORBIDDEN_MODULES:
                self.errors.append(f"Security Warning: Import of module '{base_module}' is strictly disallowed in test environments.")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            base_module = node.module.split('.')[0]
            if base_module in FORBIDDEN_MODULES:
                self.errors.append(f"Security Warning: Import from module '{base_module}' is strictly disallowed in test environments.")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Name):
            if node.func.id in FORBIDDEN_CALLS:
                self.errors.append(f"Security Warning: Calling '{node.func.id}()' is prohibited.")
        elif isinstance(node.func, ast.Attribute):
            if node.func.attr in ('system', 'popen', 'spawn', 'execv', 'remove', 'unlink', 'rmdir', 'mkdir'):
                self.errors.append(f"Security Warning: System method '{node.func.attr}' is prohibited.")
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute):
        # Block access to dunder attributes like __subclasses__, __class__, __dict__, etc.
        if node.attr.startswith('__') and node.attr.endswith('__') and node.attr not in ('__name__', '__doc__'):
            self.errors.append(f"Security Warning: Access to dunder attribute '{node.attr}' is prohibited.")
        self.generic_visit(node)


def validate_python_code(code_str: str) -> List[str]:
    """Parse and inspect code AST for security vulnerabilities."""
    try:
        tree = ast.parse(code_str)
    except SyntaxError as e:
        return [f"Syntax Error on line {e.lineno}: {e.msg}"]

    validator = CodeSecurityValidator()
    validator.visit(tree)
    return validator.errors


def execute_test_case(code_str: str, input_data: str, expected_output: str, timeout_seconds: float = 3.0) -> Dict[str, Any]:
    """
    Executes Python code against single input/output pair inside an isolated subprocess.
    """
    # 1. AST Validation
    security_errors = validate_python_code(code_str)
    if security_errors:
        return {
            'passed': False,
            'status': 'SECURITY_ERROR',
            'error_message': "\n".join(security_errors),
            'actual_output': '',
            'expected_output': expected_output.strip()
        }

    # 2. Run inside temporary sandbox directory
    with tempfile.TemporaryDirectory() as sandbox_dir:
        script_path = os.path.join(sandbox_dir, 'solution.py')
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(code_str)

        try:
            # -I: Run in isolated mode (disables current dir on sys.path, user site-packages, PYTHON* env vars)
            cmd = [sys.executable, "-I", "-B", script_path]
            
            process = subprocess.run(
                cmd,
                input=input_data if input_data else "",
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                cwd=sandbox_dir
            )

            stdout = process.stdout
            stderr = process.stderr

            if process.returncode != 0:
                return {
                    'passed': False,
                    'status': 'RUNTIME_ERROR',
                    'error_message': stderr.strip() or f"Process exited with code {process.returncode}",
                    'actual_output': stdout.strip(),
                    'expected_output': expected_output.strip()
                }

            # Normalize comparison (ignore trailing whitespace/line differences)
            clean_actual = "\n".join(line.rstrip() for line in stdout.strip().splitlines())
            clean_expected = "\n".join(line.rstrip() for line in expected_output.strip().splitlines())
            passed = (clean_actual == clean_expected)

            return {
                'passed': passed,
                'status': 'PASSED' if passed else 'WRONG_ANSWER',
                'error_message': '' if passed else 'Output mismatch',
                'actual_output': clean_actual,
                'expected_output': clean_expected
            }

        except subprocess.TimeoutExpired:
            return {
                'passed': False,
                'status': 'TIMEOUT',
                'error_message': f'Time Limit Exceeded ({timeout_seconds}s). Ensure your solution has no infinite loops.',
                'actual_output': '',
                'expected_output': expected_output.strip()
            }
        except Exception as ex:
            return {
                'passed': False,
                'status': 'EXECUTION_FAILED',
                'error_message': str(ex),
                'actual_output': '',
                'expected_output': expected_output.strip()
            }


def evaluate_coding_question(code_str: str, test_cases_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Evaluates student code against multiple test cases.
    Returns score fraction, detailed test case results, and summary.
    """
    results = []
    passed_count = 0
    total_count = len(test_cases_list)

    if total_count == 0:
        # If no test cases are defined, do a dry syntax run
        res = execute_test_case(code_str, "", "")
        return {
            'passed_count': 1 if res['status'] in ('PASSED', 'WRONG_ANSWER') else 0,
            'total_count': 1,
            'score_ratio': 1.0 if res['status'] in ('PASSED', 'WRONG_ANSWER') else 0.0,
            'test_results': [res],
            'overall_status': 'PASSED' if res['status'] in ('PASSED', 'WRONG_ANSWER') else res['status']
        }

    for idx, tc in enumerate(test_cases_list, start=1):
        input_val = tc.get('input_data', '')
        expected_val = tc.get('expected_output', '')
        is_sample = tc.get('is_sample', False)

        tc_res = execute_test_case(code_str, input_val, expected_val)
        tc_res['test_case_number'] = idx
        tc_res['is_sample'] = is_sample

        # If it's a hidden test case and failed, mask exact output for security & academic honesty
        if not is_sample and not tc_res['passed']:
            tc_res['actual_output'] = '[Hidden Test Case Output Masked]'
            tc_res['expected_output'] = '[Hidden Test Case Expected Output Masked]'

        if tc_res['passed']:
            passed_count += 1
        results.append(tc_res)

    score_ratio = passed_count / total_count if total_count > 0 else 0.0
    overall_status = 'PASSED' if passed_count == total_count else ('PARTIAL' if passed_count > 0 else 'FAILED')

    return {
        'passed_count': passed_count,
        'total_count': total_count,
        'score_ratio': score_ratio,
        'test_results': results,
        'overall_status': overall_status
    }
