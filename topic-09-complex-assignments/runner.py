#!/usr/bin/env python

import sys
from tokenizer import tokenize
from parser import parse
from evaluator import evaluate

class WatchDict(dict):
    """
    dict wrapper that prints a message when the watched identifier is created or modified.
    The evaluator should (optionally) set env._assignment_loc = <location_info> immediately
    before performing an assignment like env[name] = value. The location_info can be any
    printable object (e.g., "line 3, col 14" or a (line,col) tuple or AST node with .location).
    """
    def __init__(self, *args, watch_name=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._watch_name = watch_name
        # temporary storage that evaluator can use (see evaluator change below)
        self._assignment_loc = None

    def __setitem__(self, key, value):
        # fallback: attempt to preserve normal dict behavior
        # but if key matches watch, print value + assignment location (if available)
        prev_exists = key in self
        super().__setitem__(key, value)

        if self._watch_name is None:
            return

        if key == self._watch_name:
            loc = getattr(self, "_assignment_loc", None)
            # format location into a friendly string if possible
            if loc is None:
                loc_str = "<location unknown>"
            else:
                # common cases: a tuple (line, col) or object with .line/.col/.location
                if isinstance(loc, tuple) and len(loc) >= 2:
                    loc_str = f"line {loc[0]}, col {loc[1]}"
                else:
                    # try to access attributes commonly used
                    line = getattr(loc, "line", None) or getattr(loc, "lineno", None)
                    col = getattr(loc, "col", None) or getattr(loc, "colno", None) or getattr(loc, "column", None)
                    if line is not None:
                        if col is not None:
                            loc_str = f"line {line}, col {col}"
                        else:
                            loc_str = f"line {line}"
                    else:
                        # fallback to string of loc
                        loc_str = str(loc)

            # indicate whether it is new or modified
            action = "created" if not prev_exists else "modified"
            # Print to stdout immediately so watching is visible
            print(f"[watch] {key} {action}: {value} @ {loc_str}")

            # clear the assignment location (so it doesn't leak to other assignments)
            try:
                del self._assignment_loc
            except Exception:
                self._assignment_loc = None


def parse_watch_arg(argv):
    """
    Search argv for an argument of the form 'watch=<identifier>'.
    Return (watch_name, argv_without_watch_arg).
    """
    watch_name = None
    new_argv = []
    for arg in argv:
        if arg.startswith("watch=") and len(arg) > len("watch="):
            # take everything after '=' as the identifier (no quotes required)
            watch_name = arg.split("=", 1)[1]
        else:
            new_argv.append(arg)
    return watch_name, new_argv


def main():
    # Retrieve watch argument (if any) and strip it out so remaining args are unchanged.
    # Note: sys.argv[0] is the program name, so parse the rest.
    program_argv = sys.argv[1:]  # exclude program name
    watch_name, remaining_args = parse_watch_arg(program_argv)

    # If a filename was provided, it will be the first remaining argument
    filename = remaining_args[0] if remaining_args else None

    # create a watching environment
    environment = WatchDict(watch_name=watch_name)

    if filename:
        # File mode
        with open(filename, 'r') as f:
            source_code = f.read()
        try:
            tokens = tokenize(source_code)
            ast = parse(tokens)
            # Pass the environment (WatchDict) directly to evaluator.
            # The evaluator should set env._assignment_loc before assignments (see suggestions below).
            final_value, exit_status = evaluate(ast, environment)
            if exit_status == "exit":
                sys.exit(final_value if isinstance(final_value, int) else 0)
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
    else:
        # REPL loop
        while True:
            try:
                source_code = input('>> ')
                if source_code.strip() in ['exit', 'quit']:
                    break

                tokens = tokenize(source_code)
                ast = parse(tokens)
                final_value, exit_status = evaluate(ast, environment)
                if exit_status == "exit":
                    print(f"Exiting with code: {final_value}")
                    sys.exit(final_value if isinstance(final_value, int) else 0)
                elif final_value is not None:
                    print(final_value)
            except Exception as e:
                print(f"Error: {e}")


if __name__ == "__main__":
    main()
