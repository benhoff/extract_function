#!/usr/bin/env python3
"""
Usage:
    extract_function <cpp_file> <function_name> [<function_name2> ...]

Description:
    - Uses `ctags` to locate all function definitions in <cpp_file>.
    - For each <function_name> given, attempts to extract and print its body.
    - If multiple definitions (e.g. overloads) exist for the same name, it prints each one.
    - If a function name is not found, an error is printed.

Example:
    extract_function file.cpp my_function_name anotherFunction
"""

import sys
import subprocess
import os

def usage():
    print(__doc__.strip())
    sys.exit(1)

def get_function_positions(cpp_file):
    """
    Use ctags to find the line numbers of *all* function definitions in a file.
    Returns a dictionary of {function_name: [line_number, line_number, ...]}.
    """
    try:
        # ctags output format with -x might look like:
        #   myFunction       function    42  file.cpp
        output = subprocess.check_output(
            ["ctags", "-x", "--c++-kinds=f", cpp_file],
            universal_newlines=True
        )
    except subprocess.CalledProcessError as e:
        print(f"[Error] ctags failed on {cpp_file}:\n{e}")
        return {}
    except FileNotFoundError:
        print("[Error] ctags not found. Please install ctags.")
        return {}

    function_positions = {}
    for line in output.splitlines():
        parts = line.split()
        # Expected format: <name> <kind> <line_number> <filename>
        if len(parts) < 4:
            continue

        name, kind, line_num_str, filename = parts[0], parts[1], parts[2], parts[3]

        if kind == 'function':
            try:
                line_num = int(line_num_str)
                if name not in function_positions:
                    function_positions[name] = []
                function_positions[name].append(line_num)
            except ValueError:
                pass

    return function_positions

def extract_function_body(cpp_file, start_line):
    """
    Reads from 'start_line' in 'cpp_file' and attempts to capture 
    the entire function body by counting curly braces.
    Returns a list of lines representing the function's body.
    """
    with open(cpp_file, 'r') as f:
        file_content = f.readlines()

    # Convert to zero-based index
    start_idx = start_line - 1
    if start_idx < 0 or start_idx >= len(file_content):
        return []

    lines = []
    brace_count = 0
    in_function = False

    # Start from the line where function signature is found,
    # and read until we close all braces.
    for idx in range(start_idx, len(file_content)):
        line = file_content[idx]
        lines.append(line)

        if '{' in line:
            brace_count += line.count('{')
            in_function = True
        if '}' in line:
            brace_count -= line.count('}')

        # When in_function is True and brace_count goes back to 0,
        # we've reached the end of the function body.
        if in_function and brace_count == 0:
            break

    return lines

def main():
    if len(sys.argv) < 3:
        usage()

    cpp_file = sys.argv[1]
    function_names = sys.argv[2:]  # one or more function names

    if not os.path.isfile(cpp_file):
        print(f"[Error] File not found: {cpp_file}")
        sys.exit(1)

    # Get all function positions in the file
    function_positions = get_function_positions(cpp_file)
    if not function_positions:
        print(f"[Error] Could not retrieve any functions from '{cpp_file}'.")
        sys.exit(1)

    # For each function name specified, extract and print all matches
    for fname in function_names:
        line_numbers = function_positions.get(fname, [])
        if not line_numbers:
            print(f"[Error] Could not find function '{fname}' in {cpp_file}.")
            continue

        for idx, ln in enumerate(line_numbers, start=1):
            func_body = extract_function_body(cpp_file, ln)
            if not func_body:
                print(f"[Error] Could not extract the body of '{fname}' at line {ln}.")
                continue

            # Print a header if there are multiple matches
            if len(line_numbers) > 1:
                print(f"--- {fname} (match {idx} at line {ln}) ---")
            else:
                print(f"--- {fname} (line {ln}) ---")

            for line in func_body:
                print(line, end='')

            print("\n" + "-"*40 + "\n")  # delimiter between multiple functions

if __name__ == "__main__":
    main()
