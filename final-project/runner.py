#!/usr/bin/env python
import sys
import time
import tracemalloc
from collections import defaultdict
from tokenizer import tokenize
from parser import parse
from evaluator import evaluate

class Profiler:
    def __init__(self):
        self.statement_times = []
        self.function_calls = defaultdict(int)
        self.function_times = defaultdict(float)
        self.line_metrics = defaultdict(lambda: {'time': 0.0, 'count': 0})
        self.memory_snapshots = []
        self.enabled = False
        self.current_function = None
        self.start_time = None

    def start(self):
        """Start profiling"""
        self.enabled = True
        self.start_time = time.time()
        tracemalloc.start()

    def stop(self):
        """Stop profiling and return summary"""
        self.enabled = False
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        return {
            'total_time': time.time() - self.start_time,
            'peak_memory': peak / 1024,  # Convert to KB
            'statement_count': len(self.statement_times),
            'function_stats': dict(self.function_calls),
            'function_times': dict(self.function_times),
            'line_stats': dict(self.line_metrics),
            'slowest_statements': sorted(self.statement_times, key=lambda x: x[1], reverse=True)[:5]
        }

    def record_statement(self, ast_tag, line_num, duration):
        """Record execution time for a statement"""
        if not self.enabled:
            return
        self.statement_times.append((ast_tag, line_num, duration))

    def record_function_call(self, func_name):
        """Record a function call"""
        if not self.enabled:
            return
        self.function_calls[func_name] += 1
        self.current_function = func_name

    def record_function_time(self, func_name, duration):
        """Record time spent in a function"""
        if not self.enabled:
            return
        self.function_times[func_name] += duration
        self.current_function = None

    def record_line(self, line_num, duration):
        """Record execution time for a line"""
        if not self.enabled:
            return
        if line_num in self.line_metrics:
            self.line_metrics[line_num]['time'] += duration
            self.line_metrics[line_num]['count'] += 1
        else:
            self.line_metrics[line_num] = {'time': duration, 'count': 1}

def main():
    environment = {}
    # Parse command line arguments
    watch_identifiers = []
    enable_profile = False
    profile_output = None
    args_to_process = sys.argv[1:]
    files_to_run = []

    # Extract arguments
    i = 0
    while i < len(args_to_process):
        arg = args_to_process[i]
        if arg.startswith("watch="):
            watch_identifiers.append(arg.split("=", 1)[1])
            args_to_process.pop(i)
        elif arg == "--profile":
            enable_profile = True
            args_to_process.pop(i)
        elif arg.startswith("--profile="):
            enable_profile = True
            profile_output = arg.split("=", 1)[1]
            args_to_process.pop(i)
        else:
            files_to_run.append(arg)
            i += 1

    if watch_identifiers:
        print(f"Watching identifiers: {', '.join(watch_identifiers)}")

    # Initialize profiler
    profiler = Profiler()
    if enable_profile:
        profiler.start()
        print("Profiling enabled...")

    # Store the original evaluate function
    import evaluator
    original_evaluate = evaluator.evaluate

    # Create a wrapper function that adds profiling
    def evaluate_with_profiling_and_watch(ast, env, line_num=None):
        start_time = time.time()
    
        # Track function calls
        if ast["tag"] == "call":
            func_name = "anonymous"
            if ast["function"]["tag"] == "identifier":
                func_name = ast["function"]["value"]
            profiler.record_function_call(func_name)

        # Evaluate with timing
        result = original_evaluate(ast, env)
    
        # Handle tuple unpack if original_evaluate returns 2 items
        if isinstance(result, tuple) and len(result) == 2:
            result_val, status = result
        else:
            result_val, status = result, None

        duration = time.time() - start_time
        profiler.record_statement(ast["tag"], line_num, duration)
        if line_num:
            profiler.record_line(line_num, duration)

        return result_val, status


    # Replace the evaluate function
    evaluator.evaluate = evaluate_with_profiling_and_watch

    # Execute files if provided
    if files_to_run:
        for filename in files_to_run:
            with open(filename, 'r') as f:
                source_code = f.read()
            try:
                tokens = tokenize(source_code)
                ast = parse(tokens)
                result, status = evaluator.evaluate(ast, environment)
                print(f"Result: {result}, Status: {status}")
            except Exception as e:
                print(f"Error: {e}")

if __name__ == "__main__":
    main()
