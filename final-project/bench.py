#!/usr/bin/env python

import subprocess
import time
import sys
import os
import json
import argparse

def run_benchmark(runner_path, source_path, warmup_runs=1, timed_runs=5, microbench=False, micro_targets=None, output_base=None, save_results=None):
    """
    Run a benchmark of the specified runner on the source file.
    
    Args:
        runner_path: Path to the runner script (e.g., "profiler/runner.py")
        source_path: Path to the source file (e.g., "profiler/profile_test.t")
        warmup_runs: Number of warmup runs (default 1)
        timed_runs: Number of runs to time (default 5)
        microbench: Enable micro-benchmark mode (default False)
        micro_targets: Comma-separated list of function names to micro-bench (default None)
        output_base: Base path for micro-benchmark output files (default None)
        save_results: Path to save aggregate results JSON (default None)
    """
    print(f"                                                                              ")
    print(f"==============================================================================")
    print(f"                                                                              ")
    print(f"Benchmark Configuration:")
    print(f"                                                                              ")
    print(f"==============================================================================")
    print(f"                                                                              ")

    print(f"  Runner: {runner_path}")
    print(f"  Source: {source_path}")
    print(f"  Warmup runs: {warmup_runs}")
    print(f"  Timed runs: {timed_runs}")
    print(f"  Micro-bench enabled: {microbench}")
    if microbench and micro_targets:
        print(f"  Micro-bench targets: {micro_targets}")
    print()
    
    timings = []
    run_outputs = []
    
    # Warmup runs
    print(f"Running {warmup_runs} warmup run(s)...")
    for i in range(warmup_runs):
        try:
            env = os.environ.copy()
            if microbench:
                env["MICRO_BENCH"] = "1"
                if micro_targets:
                    env["MICRO_BENCH_TARGETS"] = micro_targets
                if output_base:
                    env["MICRO_BENCH_OUTPUT"] = f"{output_base}_warmup_{i}"
            
            result = subprocess.run(
                [sys.executable, runner_path, source_path],
                capture_output=True,
                text=True,
                env=env
            )
            if result.returncode != 0:
                print(f"  Warmup run {i+1} stderr: {result.stderr[:200]}")
        except Exception as e:
            print(f"  Warmup run {i+1} failed: {e}")
    
    # Timed runs
    print(f"\nRunning {timed_runs} timed run(s)...")
    for i in range(timed_runs):
        try:
            env = os.environ.copy()
            if microbench:
                env["MICRO_BENCH"] = "1"
                if micro_targets:
                    env["MICRO_BENCH_TARGETS"] = micro_targets
                if output_base:
                    env["MICRO_BENCH_OUTPUT"] = f"{output_base}_run_{i}"
            
            start = time.perf_counter()
            result = subprocess.run(
                [sys.executable, runner_path, source_path],
                capture_output=True,
                text=True,
                env=env
            )
            elapsed = time.perf_counter() - start
            
            timings.append(elapsed)
            run_outputs.append({
                "run": i + 1,
                "time": elapsed,
                "return_code": result.returncode,
                "stdout": result.stdout[:500] if result.stdout else "",
                "stderr": result.stderr[:200] if result.stderr else ""
            })
            
            print(f"                                                                              ")
            print(f"  Run {i+1}: {elapsed:.4f}s (rc={result.returncode})")

            if result.stdout:
                print(f"    stdout: {result.stdout[:100]}")
            if result.stderr:
                print(f"    stderr: {result.stderr[:100]}")
        except Exception as e:
            print(f"  Run {i+1} failed: {e}")
    
    # Calculate statistics
    if timings:
        mean_time = sum(timings) / len(timings)
        min_time = min(timings)
        max_time = max(timings)
        
        # Standard deviation
        variance = sum((t - mean_time) ** 2 for t in timings) / len(timings)
        stdev = variance ** 0.5
        
        print(f"\n=== Results ===")
        print(f"Mean:   {mean_time:.4f}s")
        print(f"Stdev:  {stdev:.4f}s")
        print(f"Min:    {min_time:.4f}s (fastest)")
        print(f"Max:    {max_time:.4f}s (slowest)")
        
        # Aggregate results
        results = {
            "runner": runner_path,
            "source": source_path,
            "warmup_runs": warmup_runs,
            "timed_runs": timed_runs,
            "timings": timings,
            "mean": mean_time,
            "stdev": stdev,
            "min": min_time,
            "max": max_time,
            "run_details": run_outputs,
            "microbench_enabled": microbench,
            "microbench_targets": micro_targets
        }
        
        # Save results if requested
        if save_results:
            try:
                with open(save_results, "w", encoding="utf-8") as f:
                    json.dump(results, f, indent=2)
                print(f"\nResults saved to: {save_results}")
            except Exception as e:
                print(f"\nFailed to save results: {e}")
        
        # Combine micro-benchmark outputs if present
        if microbench and output_base:
            micro_outputs = {}
            for i in range(timed_runs):
                micro_file = f"{output_base}_run_{i}.json"
                try:
                    with open(micro_file, "r", encoding="utf-8") as f:
                        micro_data = json.load(f)
                        micro_outputs[f"run_{i}"] = micro_data
                except FileNotFoundError:
                    pass
                except Exception as e:
                    print(f"Failed to load micro output {micro_file}: {e}")
            
            if micro_outputs:
                combined_micro = {
                    "timestamp": time.time(),
                    "runs": micro_outputs,
                    "targets": micro_targets.split(",") if micro_targets else "all"
                }
                micro_combined_file = f"{save_results}.micro.json" if save_results else f"{output_base}.combined.json"
                try:
                    with open(micro_combined_file, "w", encoding="utf-8") as f:
                        json.dump(combined_micro, f, indent=2)
                    print(f"Micro-bench combined output saved to: {micro_combined_file}")
                except Exception as e:
                    print(f"Failed to save combined micro output: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark a language runner")
    parser.add_argument("--runner", default="topic-06-grammar-verification/runner.py", help="Path to runner script")
    parser.add_argument("--source", default="topic-06-grammar-verification/example.t", help="Path to source file")
    parser.add_argument("--warmup", type=int, default=1, help="Number of warmup runs")
    parser.add_argument("--runs", type=int, default=5, help="Number of timed runs")
    parser.add_argument("--microbench", action="store_true", help="Enable micro-benchmarking")
    parser.add_argument("--micro-targets", default=None, help="Comma-separated list of function names to micro-bench")
    parser.add_argument("--output-base", default=None, help="Base path for micro-benchmark output files")
    parser.add_argument("--save", default=None, help="Path to save results JSON")
    
    args = parser.parse_args()
    
    run_benchmark(
        runner_path=args.runner,
        source_path=args.source,
        warmup_runs=args.warmup,
        timed_runs=args.runs,
        microbench=args.microbench,
        micro_targets=args.micro_targets,
        output_base=args.output_base,
        save_results=args.save
    )
