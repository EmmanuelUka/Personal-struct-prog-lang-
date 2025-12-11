#!/usr/bin/env python

import copy
import os
import time
import atexit
import json
import csv

# Micro-benchmark hooks (enabled via env vars)
MICRO_BENCH_ENABLED = os.getenv("MICRO_BENCH", "0") in ("1", "true", "True")
MICRO_BENCH_TARGETS = os.getenv("MICRO_BENCH_TARGETS")
if MICRO_BENCH_TARGETS:
    MICRO_BENCH_TARGETS = [t.strip() for t in MICRO_BENCH_TARGETS.split(",") if t.strip()]
else:
    MICRO_BENCH_TARGETS = []
MICRO_BENCH_OUTPUT = os.getenv("MICRO_BENCH_OUTPUT")

_bench_stats = {}

def _bench_record(name, duration):
    if name is None:
        name = "<anonymous>"
    s = _bench_stats.get(name)
    if not s:
        s = {"count": 0, "total": 0.0, "min": duration, "max": duration}
        _bench_stats[name] = s
    s["count"] += 1
    s["total"] += duration
    if duration < s["min"]:
        s["min"] = duration
    if duration > s["max"]:
        s["max"] = duration

def _bench_dump_if_enabled(output_base=None):
    if not _bench_stats:
        return
    base = output_base or MICRO_BENCH_OUTPUT
    if not base:
        return
    try:
        with open(base + ".json", "w", encoding="utf-8") as f:
            json.dump(_bench_stats, f, indent=2)
    except Exception:
        pass
    try:
        with open(base + ".csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["function", "count", "total", "min", "max", "avg"])
            for name, s in _bench_stats.items():
                avg = s["total"] / s["count"] if s["count"] else 0.0
                writer.writerow([name, s["count"], s["total"], s["min"], s["max"], avg])
    except Exception:
        pass

if MICRO_BENCH_ENABLED and MICRO_BENCH_OUTPUT:
    atexit.register(lambda: _bench_dump_if_enabled(MICRO_BENCH_OUTPUT))

def type_of(*args):
    def single_type(x):
        if isinstance(x, bool):
            return "boolean"
        if isinstance(x, (int, float)):
            return "number"
        if isinstance(x, str):
            return "string"
        if isinstance(x, list):
            return "array"
        if isinstance(x, dict):
            return "object"
        if x is None:
            return "null"
        assert False, f"Unknown type for value: {x}"
    return "-".join(single_type(arg) for arg in args)
    
# Minimal builtin function set and helpers
__builtin_functions = set(["len", "str", "int", "float", "print"])

def evaluate_builtin_function(name, args):
    if name == "len":
        return len(args[0]) if args else 0
    if name == "str":
        return str(args[0]) if args else ""
    if name == "int":
        return int(args[0]) if args else 0
    if name == "float":
        return float(args[0]) if args else 0.0
    if name == "print":
        print(*args)
        return None
    raise Exception(f"Unknown builtin function: {name}")

def is_truthy(x):
    if x is None:
        return False
    if isinstance(x, bool):
        return x
    if isinstance(x, (int, float)):
        return x != 0
    if isinstance(x, str):
        return len(x) != 0
    if isinstance(x, (list, dict)):
        return len(x) != 0
    return True

def evaluate(ast, environment):
    # Identifier
    if ast["tag"] == "identifier":
        identifier = ast["value"]

        # Check local environment
        if identifier in environment:
            return environment[identifier], None

        # Walk parent chain to find identifier
        scope = environment.get("$parent") if isinstance(environment, dict) else None
        while scope is not None:
            if identifier in scope:
                return scope[identifier], None
            scope = scope.get("$parent") if isinstance(scope, dict) else None

        # Check builtin functions
        if identifier in __builtin_functions:
            return {"tag": "builtin", "name": identifier}, None

        raise Exception(f"Unknown identifier: '{identifier}'")
    
    # Primitive literals
    if ast.get("tag") == "number":
        return ast.get("value"), None
    if ast.get("tag") == "string":
        return ast.get("value"), None
    if ast.get("tag") == "boolean":
        # boolean node may store value or use tag name semantics
        return ast.get("value") if "value" in ast else True, None
    if ast.get("tag") == "null":
        return None, None
    
    # Data structures
    elif ast["tag"] == "list":
        items = []
        for item in ast["items"]:
            value, status = evaluate(item, environment)
            if status == "exit":
                return value, "exit"
            items.append(value)
        return items, None
    
    elif ast["tag"] == "object":
        obj = {}
        for item in ast["items"]:
            key, key_status = evaluate(item["key"], environment)
            if key_status == "exit":
                return key, "exit"
            assert isinstance(key, str), "Object key must be a string"
            value, value_status = evaluate(item["value"], environment)
            if value_status == "exit":
                return value, "exit"
            obj[key] = value
        return obj, None
    
    # Arithmetic operations
    elif ast["tag"] == "+":
        left, left_status = evaluate(ast["left"], environment)
        if left_status == "exit":
            return left, "exit"
        right, right_status = evaluate(ast["right"], environment)
        if right_status == "exit":
            return right, "exit"
        
        types = type_of(left, right)
        if types == "number-number":
            return left + right, None
        elif types == "string-string":
            return left + right, None
        elif types == "array-array":
            return copy.deepcopy(left) + copy.deepcopy(right), None
        elif types == "object-object":
            return {**copy.deepcopy(left), **copy.deepcopy(right)}, None
        raise Exception(f"Cannot add {types}")
    
    elif ast["tag"] == "-":
        left, left_status = evaluate(ast["left"], environment)
        if left_status == "exit":
            return left, "exit"
        right, right_status = evaluate(ast["right"], environment)
        if right_status == "exit":
            return right, "exit"
        
        if type_of(left, right) == "number-number":
            return left - right, None
        raise Exception("Subtraction requires numbers")
    
    elif ast["tag"] == "*":
        left, left_status = evaluate(ast["left"], environment)
        if left_status == "exit":
            return left, "exit"
        right, right_status = evaluate(ast["right"], environment)
        if right_status == "exit":
            return right, "exit"
        
        types = type_of(left, right)
        if types == "number-number":
            return left * right, None
        elif types == "string-number":
            return left * int(right), None
        elif types == "number-string":
            return int(left) * right, None
        raise Exception(f"Cannot multiply {types}")
    
    elif ast["tag"] == "/":
        left, left_status = evaluate(ast["left"], environment)
        if left_status == "exit":
            return left, "exit"
        right, right_status = evaluate(ast["right"], environment)
        if right_status == "exit":
            return right, "exit"
        
        if type_of(left, right) == "number-number":
            if right == 0:
                raise Exception("Division by zero")
            return left / right, None
        raise Exception("Division requires numbers")
    
    elif ast["tag"] == "%":
        left, left_status = evaluate(ast["left"], environment)
        if left_status == "exit":
            return left, "exit"
        right, right_status = evaluate(ast["right"], environment)
        if right_status == "exit":
            return right, "exit"
        
        if type_of(left, right) == "number-number":
            if right == 0:
                raise Exception("Modulo by zero")
            return left % right, None
        raise Exception("Modulo requires numbers")
    
    elif ast["tag"] == "negate":
        value, status = evaluate(ast["value"], environment)
        if status == "exit":
            return value, "exit"
        
        if type_of(value) == "number":
            return -value, None
        raise Exception("Negation requires a number")
    
    # Comparison operations
    elif ast["tag"] in ["<", ">", "<=", ">="]:
        left, left_status = evaluate(ast["left"], environment)
        if left_status == "exit":
            return left, "exit"
        right, right_status = evaluate(ast["right"], environment)
        if right_status == "exit":
            return right, "exit"
        
        types = type_of(left, right)
        if types not in ["number-number", "string-string"]:
            raise Exception(f"Cannot compare {types} with {ast['tag']}")
        
        if ast["tag"] == "<":
            return left < right, None
        elif ast["tag"] == ">":
            return left > right, None
        elif ast["tag"] == "<=":
            return left <= right, None
        elif ast["tag"] == ">=":
            return left >= right, None
    
    elif ast["tag"] == "==":
        left, left_status = evaluate(ast["left"], environment)
        if left_status == "exit":
            return left, "exit"
        right, right_status = evaluate(ast["right"], environment)
        if right_status == "exit":
            return right, "exit"
        return left == right, None
    
    elif ast["tag"] == "!=":
        left, left_status = evaluate(ast["left"], environment)
        if left_status == "exit":
            return left, "exit"
        right, right_status = evaluate(ast["right"], environment)
        if right_status == "exit":
            return right, "exit"
        return left != right, None
    
    # Logical operations
    elif ast["tag"] in ["not", "!"]:
        value, status = evaluate(ast["value"], environment)
        if status == "exit":
            return value, "exit"
        return not is_truthy(value), None
    
    elif ast["tag"] in ["&&", "and"]:
        left, left_status = evaluate(ast["left"], environment)
        if left_status == "exit":
            return left, "exit"
        if not is_truthy(left):
            return left, None
        
        right, right_status = evaluate(ast["right"], environment)
        if right_status == "exit":
            return right, "exit"
        return is_truthy(left) and is_truthy(right), None
    
    elif ast["tag"] in ["||", "or"]:
        left, left_status = evaluate(ast["left"], environment)
        if left_status == "exit":
            return left, "exit"
        if is_truthy(left):
            return left, None
        
        right, right_status = evaluate(ast["right"], environment)
        if right_status == "exit":
            return right, "exit"
        return is_truthy(left) or is_truthy(right), None
    
    # Complex expressions (indexing)
    elif ast["tag"] == "complex":
        base, base_status = evaluate(ast["base"], environment)
        if base_status == "exit":
            return base, "exit"
        index, index_status = evaluate(ast["index"], environment)
        if index_status == "exit":
            return index, "exit"
        
        if isinstance(index, (int, float)):
            index = int(index)
            if not isinstance(base, list):
                raise Exception("Can only index lists with numbers")
            if index < 0 or index >= len(base):
                raise IndexError(f"List index {index} out of range")
            return base[index], None
        elif isinstance(index, str):
            if not isinstance(base, dict):
                raise Exception("Can only index objects with strings")
            if index not in base:
                raise KeyError(f"Key '{index}' not found")
            return base[index], None
        else:
            raise Exception(f"Cannot index with {type(index).__name__}")
    
    # Assignment
    elif ast["tag"] == "assign":
        target = ast["target"]
        
        # Evaluate the value first
        value, value_status = evaluate(ast["value"], environment)
        if value_status == "exit":
            return value, "exit"
        
        # Handle identifier assignment
        if target["tag"] == "identifier":
            name = target["value"]
            
            # Handle extern keyword
            if target.get("extern"):
                # Find in parent scope
                scope = environment
                while scope is not None and name not in scope:
                    scope = scope.get("$parent")
                if scope is None:
                    raise Exception(f"Extern: '{name}' not found in any outer scope")
                target_env = scope
            else:
                target_env = environment
            
            target_env[name] = value
            return value, None
        
        # Handle complex assignment (x[0] = 5 or x.y = 10)
        elif target["tag"] == "complex":
            base, base_status = evaluate(target["base"], environment)
            if base_status == "exit":
                return base, "exit"
            
            # Get index
            index_ast = target["index"]
            if index_ast["tag"] == "string":
                index = index_ast["value"]
            else:
                index, index_status = evaluate(index_ast, environment)
                if index_status == "exit":
                    return index, "exit"
            
            if isinstance(base, list):
                if not isinstance(index, (int, float)):
                    raise Exception("List index must be a number")
                index = int(index)
                if index < 0 or index >= len(base):
                    raise IndexError(f"List index {index} out of range")
                base[index] = value
            elif isinstance(base, dict):
                if not isinstance(index, str):
                    raise Exception("Object key must be a string")
                base[index] = value
            else:
                raise Exception(f"Cannot assign to {type(base).__name__}")
            
            return value, None
        
        else:
            raise Exception(f"Cannot assign to {target['tag']}")
    
    # Function definition
    elif ast["tag"] == "function":
        return {
            "tag": "function",
            "parameters": ast["parameters"],
            "body": ast["body"],
            "environment": environment
        }, None
    
    # Function call
    elif ast["tag"] == "call":
        # Determine call name (if calling by identifier)
        call_name = None
        if isinstance(ast.get("function"), dict) and ast["function"].get("tag") == "identifier":
            call_name = ast["function"]["value"]

        # Evaluate function
        func, func_status = evaluate(ast["function"], environment)
        if func_status == "exit":
            return func, "exit"

        # Evaluate arguments
        args = []
        for arg in ast["arguments"]:
            arg_val, arg_status = evaluate(arg, environment)
            if arg_status == "exit":
                return arg_val, "exit"
            args.append(arg_val)

        # Handle builtin functions
        if isinstance(func, dict) and func.get("tag") == "builtin":
            return evaluate_builtin_function(func["name"], args)

        # Handle user functions
        elif isinstance(func, dict) and func.get("tag") == "function":
            # Create new environment
            local_env = {}

            # Bind parameters
            params = func["parameters"]
            for i, param in enumerate(params):
                param_name = param["value"]
                local_env[param_name] = args[i] if i < len(args) else None

            # Link to parent environment
            local_env["$parent"] = func["environment"]

            # Execute function body (optionally time it)
            should_bench = MICRO_BENCH_ENABLED and (not MICRO_BENCH_TARGETS or (call_name in MICRO_BENCH_TARGETS))
            if should_bench:
                t0 = time.perf_counter()
            result, status = evaluate(func["body"], local_env)
            if should_bench:
                dur = time.perf_counter() - t0
                _bench_record(call_name or "<anonymous>", dur)

            if status == "return":
                return result, None
            elif status == "exit":
                return result, "exit"
            else:
                return None, None

        else:
            raise Exception(f"'{func}' is not a function")
    
    # Control flow
    elif ast["tag"] == "if":
        condition, cond_status = evaluate(ast["condition"], environment)
        if cond_status == "exit":
            return condition, "exit"
        
        if is_truthy(condition):
            return evaluate(ast["then"], environment)
        elif "else" in ast:
            return evaluate(ast["else"], environment)
        
        return None, None
    
    elif ast["tag"] == "while":
        while True:
            condition, cond_status = evaluate(ast["condition"], environment)
            if cond_status == "exit":
                return condition, "exit"
            
            if not is_truthy(condition):
                break
            
            result, status = evaluate(ast["do"], environment)
            
            if status == "return" or status == "exit":
                return result, status
            elif status == "break":
                break
            elif status == "continue":
                continue
        
        return None, None
    
    # Statements
    elif ast["tag"] == "print":
        if ast["value"] is not None:
            value, status = evaluate(ast["value"], environment)
            if status == "exit":
                return value, "exit"
            print(value)
            return value, None
        else:
            print()
            return None, None
    
    elif ast["tag"] == "return":
        if "value" in ast and ast["value"] is not None:
            value, status = evaluate(ast["value"], environment)
            if status == "exit":
                return value, "exit"
            return value, "return"
        return None, "return"
    
    elif ast["tag"] == "exit":
        exit_code = 0
        if "value" in ast and ast["value"] is not None:
            exit_code, status = evaluate(ast["value"], environment)
            if status == "exit":
                return exit_code, "exit"
            if not isinstance(exit_code, int):
                raise Exception("Exit code must be an integer")
            return exit_code, "exit"
        return exit_code, "exit"
    
    elif ast["tag"] == "break":
        return None, "break"
    
    elif ast["tag"] == "continue":
        return None, "continue"
    
    elif ast["tag"] == "import":
        filename, status = evaluate(ast["value"], environment)
        if status == "exit":
            return filename, "exit"
        
        if not isinstance(filename, str):
            raise Exception("Import path must be a string")
        
        try:
            with open(filename, 'r') as f:
                source_code = f.read()
            from tokenizer import tokenize
            from parser import parse
            tokens = tokenize(source_code)
            imported_ast = parse(tokens)
            return evaluate(imported_ast, environment)
        except FileNotFoundError:
            raise Exception(f"Import error: File '{filename}' not found")
        except Exception as e:
            raise Exception(f"Import error: {e}")
    
    elif ast["tag"] == "assert":
        condition, cond_status = evaluate(ast["condition"], environment)
        if cond_status == "exit":
            return condition, "exit"
        
        if not is_truthy(condition):
            message = "Assertion failed"
            if "explanation" in ast and ast["explanation"] is not None:
                explanation, expl_status = evaluate(ast["explanation"], environment)
                if expl_status == "exit":
                    return explanation, "exit"
                message += f": {explanation}"
            raise Exception(message)
        
        return None, None
    
    # Compound statements
    elif ast["tag"] == "statement_list":
        result = None
        for statement in ast["statements"]:
            result, status = evaluate(statement, environment)
            if status in ["return", "exit", "break", "continue"]:
                return result, status
        return result, None
    
    elif ast["tag"] == "program":
        result = None
        for statement in ast["statements"]:
            result, status = evaluate(statement, environment)
            if status == "exit":
                return result, status
            elif status == "return":
                raise Exception("'return' statement outside of function")
            elif status == "break":
                raise Exception("'break' statement outside of loop")
            elif status == "continue":
                raise Exception("'continue' statement outside of loop")
        return result, None
    
    else:
        raise Exception(f"Unknown AST tag: {ast['tag']}")

def clean(e):
    """Helper function to clean environment for testing"""
    if isinstance(e, dict):
        return {k: clean(v) for k, v in e.items() if k != "environment"}
    if isinstance(e, list):
        return [clean(v) for v in e]
    return e

def equals(code, environment, expected_result, expected_environment=None):
    """Test helper function"""
    from tokenizer import tokenize
    from parser import parse
    
    result, status = evaluate(parse(tokenize(code)), environment)
    
    assert clean(result) == clean(expected_result), \
        f"Expected {expected_result}, got {result}"
    
    assert status is None or status == "exit", \
        f"Unexpected status: {status}"
    
    if expected_environment is not None:
        assert clean(environment) == clean(expected_environment), \
            f"Expected env {expected_environment}, got {environment}"

# Test function
def test_evaluator():
    """Run basic tests on the evaluator"""
    print("Testing evaluator...")
    
    # Test basic values
    env = {}
    equals("5", env, 5)
    equals('"hello"', env, "hello")
    equals("true", env, True)
    equals("false", env, False)
    equals("null", env, None)
    
    # Test arithmetic
    equals("1 + 2", env, 3)
    equals("5 - 2", env, 3)
    equals("3 * 4", env, 12)
    equals("10 / 2", env, 5.0)
    equals("10 % 3", env, 1)
    
    # Test comparisons
    equals("5 > 3", env, True)
    equals("5 < 3", env, False)
    equals("5 == 5", env, True)
    equals("5 != 3", env, True)
    
    # Test assignment
    equals("x = 10", env, 10)
    assert env["x"] == 10
    equals("x = x + 5", env, 15)
    assert env["x"] == 15
    
    # Test lists
    equals("[1, 2, 3]", env, [1, 2, 3])
    equals("x = [1, 2, 3]; x[1]", env, 2)
    
    # Test objects
    equals('{"a": 1, "b": 2}', env, {"a": 1, "b": 2})
    equals('x = {"a": 1}; x["a"]', env, 1)
    
    # Test if statement
    equals("if (true) { 5 }", env, 5)
    equals("if (false) { 5 } else { 10 }", env, 10)
    
    # Test while loop
    equals("x = 0; while (x < 3) { x = x + 1 }; x", env, 3)
    
    # Test print (just run it, don't check output)
    test_code = 'print "test"'
    from tokenizer import tokenize
    from parser import parse
    tokens = tokenize(test_code)
    ast = parse(tokens)
    result, status = evaluate(ast, {})
    
    # Test function
    env = {}
    equals("function add(x, y) { return x + y }; add(3, 4)", env, 7)
    
    print("All basic tests passed!")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        test_evaluator()
    else:
        # Quick demo
        print("Quick demo of evaluator...")
        env = {}
        code = 'x = 5; y = 10; print(x + y)'
        from tokenizer import tokenize
        from parser import parse
        tokens = tokenize(code)
        ast = parse(tokens)
        result, status = evaluate(ast, env)
        print(f"Result: {result}, Status: {status}, Env: {env}")