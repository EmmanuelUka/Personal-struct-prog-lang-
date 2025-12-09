#!/usr/bin/env python

import sys

from tokenizer import tokenize
from parser import parse
from evaluator import evaluate

def main():
    environment = {}
    
    watch_identifiers = []
    args_to_process = sys.argv[1:]
    files_to_run = []
    
    i = 0
    while i < len(args_to_process):
        arg = args_to_process[i]
        if arg.startswith("watch="):
            watch_identifiers.append(arg.split("=", 1)[1])
            args_to_process.pop(i)
        else:
            files_to_run.append(arg)
            i += 1
    
    if watch_identifiers:
        print(f"Watching identifiers: {', '.join(watch_identifiers)}")
    
    import evaluator
    original_evaluate = evaluator.evaluate
    
    assignment_line_numbers = {}
    
    def get_location_info():
        """Get location information for the current assignment"""
        return "<location unknown>"
    
    def parse_with_watch(tokens):
        """Parse tokens and track line numbers for assignments"""
        ast = parse(tokens)
        
        def track_assignment_lines(node, tokens):
            """Recursively track line numbers for assignment statements"""
            if node["tag"] == "assign" and "target" in node:
    
                assignment_pos = None
                for i, token in enumerate(tokens):
                    if token["tag"] == "=":
                        
                        assignment_pos = i
                        break
                
                if assignment_pos is not None and assignment_pos < len(tokens):
                    node["_watch_line"] = tokens[assignment_pos].get("line", "unknown")
            
            if node["tag"] in ["+", "-", "*", "/", "%", "<", ">", "<=", ">=", "==", "!=", "&&", "||"]:
                if "left" in node:
                    track_assignment_lines(node["left"], tokens)
                if "right" in node:
                    track_assignment_lines(node["right"], tokens)
            elif node["tag"] in ["negate", "not", "!"] and "value" in node:
                track_assignment_lines(node["value"], tokens)
            elif node["tag"] == "if":
                track_assignment_lines(node["condition"], tokens)
                track_assignment_lines(node["then"], tokens)
                if "else" in node:
                    track_assignment_lines(node["else"], tokens)
            elif node["tag"] == "while":
                track_assignment_lines(node["condition"], tokens)
                track_assignment_lines(node["do"], tokens)
            elif node["tag"] in ["print", "return", "exit"] and "value" in node and node["value"] is not None:
                track_assignment_lines(node["value"], tokens)
            elif node["tag"] == "assert":
                track_assignment_lines(node["condition"], tokens)
                if "explanation" in node:
                    track_assignment_lines(node["explanation"], tokens)
            elif node["tag"] == "assign":
                track_assignment_lines(node["target"], tokens)
                track_assignment_lines(node["value"], tokens)
            elif node["tag"] == "call":
                track_assignment_lines(node["function"], tokens)
                for arg in node.get("arguments", []):
                    track_assignment_lines(arg, tokens)
            elif node["tag"] == "complex":
                track_assignment_lines(node["base"], tokens)
                track_assignment_lines(node["index"], tokens)
            elif node["tag"] in ["list", "object"]:
                for item in node.get("items", []):
                    if isinstance(item, dict):
                        if "key" in item:
                            track_assignment_lines(item["key"], tokens)
                        if "value" in item:
                            track_assignment_lines(item["value"], tokens)
                    else:
                        track_assignment_lines(item, tokens)
            elif node["tag"] == "function":
                for param in node.get("parameters", []):
                    track_assignment_lines(param, tokens)
                track_assignment_lines(node["body"], tokens)
            elif node["tag"] in ["statement_list", "program"]:
                for stmt in node.get("statements", []):
                    track_assignment_lines(stmt, tokens)
            elif node["tag"] == "import" and "value" in node:
                track_assignment_lines(node["value"], tokens)
        
        track_assignment_lines(ast, tokens)
        return ast
    
    def evaluate_with_watch(ast, env):
        if ast["tag"] == "assign":
            target = ast["target"]
            
            identifier_name = None
            if target["tag"] == "identifier":
                identifier_name = target["value"]
            elif target["tag"] == "complex" and target["base"]["tag"] == "identifier":
                identifier_name = target["base"]["value"]
            
            value, value_status = original_evaluate(ast["value"], env)
            if value_status == "exit":
                return value, "exit"
            
            if identifier_name and identifier_name in watch_identifiers:
                line_num = ast.get("_watch_line", "unknown")
                location = f"line {line_num}" if line_num != "unknown" else "<location unknown>"
                
                is_new = identifier_name not in env
                
                action = "created" if is_new else "modified"
                print(f"[watch] {identifier_name} {action}: {repr(value)} @ {location}")
            
            if target["tag"] == "identifier":
                name = target["value"]
                
                if target.get("extern"):
                    scope = env
                    while scope is not None and name not in scope:
                        scope = scope.get("$parent")
                    assert scope is not None, f"Extern assignment: '{name}' not found in any outer scope"
                    target_base = scope
                else:
                    target_base = env
                
                target_base[name] = value
                return value, None
            
            elif target["tag"] == "complex":
                base, base_status = original_evaluate(target["base"], env)
                if base_status == "exit":
                    return base, "exit"
                
                index_ast = target["index"]
                if index_ast["tag"] == "string":
                    index = index_ast["value"]
                else:
                    index, index_status = original_evaluate(index_ast, env)
                    if index_status == "exit":
                        return index, "exit"
                
                if index is None:
                    raise Exception("Cannot use 'null' as index for assignment.")
                assert type(index) in [int, float, str], f"Unknown index type [{index}]"
                
                if isinstance(base, list):
                    assert isinstance(index, int), "List index must be integer"
                    assert 0 <= index < len(base), "List index out of range"
                    base[index] = value
                elif isinstance(base, dict):
                    base[index] = value
                else:
                    assert False, f"Cannot assign to base of type {type(base)}"
                
                return value, None
            
            return value, None
        
        return original_evaluate(ast, env)
    
    evaluator.evaluate = evaluate_with_watch
    
    if files_to_run:
        for filename in files_to_run:
            with open(filename, 'r') as f:
                source_code = f.read()
            try:
                tokens = tokenize(source_code)
                ast = parse_with_watch(tokens)
                final_value, exit_status = evaluate_with_watch(ast, environment)
                if exit_status == "exit":
                    sys.exit(final_value if isinstance(final_value, int) else 0)
            except Exception as e:
                print(f"Error: {e}")
                sys.exit(1)
    else:
        current_line = 1
        while True:
            try:
                prompt = f"{current_line:3d} >> " if current_line > 1 else "   >> "
                source_code = input(prompt)
                
                if source_code.strip() in ['exit', 'quit']:
                    break
                
                tokens = tokenize(source_code)
                for token in tokens:
                    if token["tag"] is not None:
                        token["line"] = current_line
                
                ast = parse_with_watch(tokens)
                final_value, exit_status = evaluate_with_watch(ast, environment)
                
                if exit_status == "exit":
                    print(f"Exiting with code: {final_value}")
                    sys.exit(final_value if isinstance(final_value, int) else 0)
                elif final_value is not None:
                    print(final_value)
                
                current_line += 1
            except Exception as e:
                print(f"Error: {e}")

if __name__ == "__main__":
    main()