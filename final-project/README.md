Final Project: Simple Benchmark Harness

Goal
----
Provide a small, focused benchmarking harness that runs an existing topic runner repeatedly and reports wall-clock timings.

What it does
-----------
- Uses an existing `runner.py` (default: `topic-06-grammar-verification/runner.py`) to execute a language program.
- Runs a configurable number of warmup runs and timed runs, collecting per-run elapsed time.
- Prints mean, standard deviation, fastest and slowest run times and shows sample output.

How to run
----------
From the repository root:

```powershell
python final-project\bench.py --runner topic-06-grammar-verification\runner.py --source topic-06-grammar-verification\example.t --warmup 1 --runs 5
```

Notes
-----
- This harness does not change the language implementation; it measures the user-level runner's wall time.
- If you want to benchmark another topic, point `--runner` and `--source` to the desired files.
