#!/usr/bin/env python3
"""
Usage:
    extract_function <cpp_file> [<function_name> [<function_name2> ...]]

Description:
    - Uses `ctags` to locate all function definitions in <cpp_file>.
    - If one or more function names are provided, attempts to extract each one.
    - If no function name is provided, opens a TUI to let you pick one function.
    - If multiple definitions (e.g., overloads) exist for the same name, it prints each one.
    - If a function name is not found, an error is printed.

Example:
    extract_function file.cpp my_function_name anotherFunction
"""

import sys
import subprocess
import os
import curses  # for the TUI

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

    # Start from the line where the function signature is found,
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

def curses_select_function(function_names):
    """
    Launch a simple TUI with curses to let the user select a single function name
    from the given list using the up/down arrows. Press Enter to confirm choice.
    Returns the chosen function name.
    """
    def main(stdscr):
        curses.curs_set(0)  # Hide the cursor
        current_row = 0

        # Initialize color pair (foreground on background)
        curses.start_color()
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)

        def print_menu(stdscr, selected_idx):
            stdscr.clear()
            h, w = stdscr.getmaxyx()

            # Center the list in the window
            start_y = max((h - len(function_names)) // 2, 0)

            for idx, fname in enumerate(function_names):
                x = w // 2 - len(fname) // 2
                y = start_y + idx

                if idx == selected_idx:
                    stdscr.attron(curses.color_pair(1))
                    stdscr.addstr(y, x, fname)
                    stdscr.attroff(curses.color_pair(1))
                else:
                    stdscr.addstr(y, x, fname)

            stdscr.refresh()

        print_menu(stdscr, current_row)

        while True:
            key = stdscr.getch()

            if key == curses.KEY_UP and current_row > 0:
                current_row -= 1
            elif key == curses.KEY_DOWN and current_row < len(function_names) - 1:
                current_row += 1
            # ENTER can be curses.KEY_ENTER (on some terminals) or 10 or 13
            elif key in [curses.KEY_ENTER, 10, 13]:
                return function_names[current_row]

            print_menu(stdscr, current_row)

    return curses.wrapper(main)

def choose_function_interactively(cpp_file, function_positions):
    """
    If the user didn't provide a function name, we open a TUI to
    let them pick from all functions found in the file.
    """
    # Sort them alphabetically (you could also keep them in ctags order)
    all_func_names = sorted(function_positions.keys())
    if not all_func_names:
        print(f"[Error] No functions found in '{cpp_file}'.")
        sys.exit(1)

    chosen_function = curses_select_function(all_func_names)
    return [chosen_function]  # return list for consistency

def process_functions(cpp_file, function_positions, function_names):
    """
    For each function name, extract and print all positions (overloads).
    """
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

def main():
    # If at least <cpp_file> is not provided, show usage
    if len(sys.argv) < 2:
        usage()

    cpp_file = sys.argv[1]

    if not os.path.isfile(cpp_file):
        print(f"[Error] File not found: {cpp_file}")
        sys.exit(1)

    # Gather all function positions from ctags
    function_positions = get_function_positions(cpp_file)
    if not function_positions:
        print(f"[Error] Could not retrieve any functions from '{cpp_file}'.")
        sys.exit(1)

    # If only the file is provided, open the TUI to pick exactly one function
    if len(sys.argv) == 2:
        function_names = choose_function_interactively(cpp_file, function_positions)
    else:
        # Use the function names passed on the command line
        function_names = sys.argv[2:]

    # Extract and print the functions
    process_functions(cpp_file, function_positions, function_names)

if __name__ == "__main__":
    main()
