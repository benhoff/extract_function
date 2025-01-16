#!/usr/bin/env python3
import sys
import ast
import curses

def extract_function(file_path, function_name):
    # Read the source file
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
    except IOError as e:
        print(f"Error reading {file_path}: {e}")
        sys.exit(1)

    # Parse the AST
    try:
        tree = ast.parse(source, filename=file_path)
    except SyntaxError as e:
        print(f"Syntax error in {file_path}: {e}")
        sys.exit(1)

    # Traverse the AST to find the function definition by name
    target_node = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            target_node = node
            break

    if not target_node:
        print(f"Function '{function_name}' not found in {file_path}.")
        sys.exit(1)

    # Check for the required attribute: end_lineno (Python 3.8+)
    if not hasattr(target_node, "end_lineno"):
        print("Your Python version does not support 'end_lineno'. Please use Python 3.8 or above.")
        sys.exit(1)

    # Determine the starting line: include decorators if present
    start_lineno = target_node.lineno
    if target_node.decorator_list:
        # Decorators might start on a line before the function definition
        decorator_lines = [dec.lineno for dec in target_node.decorator_list if hasattr(dec, 'lineno')]
        if decorator_lines:
            start_lineno = min(start_lineno, min(decorator_lines))

    # Extract the source lines
    source_lines = source.splitlines()
    extracted_lines = source_lines[start_lineno - 1 : target_node.end_lineno]

    # Join and print the extracted function code
    extracted_code = "\n".join(extracted_lines)
    print(extracted_code)


def get_function_names(file_path):
    """Return a list of all function names defined in file_path."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
    except IOError as e:
        print(f"Error reading {file_path}: {e}")
        sys.exit(1)

    # Parse the AST to find all function definitions
    try:
        tree = ast.parse(source, filename=file_path)
    except SyntaxError as e:
        print(f"Syntax error in {file_path}: {e}")
        sys.exit(1)

    function_names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            function_names.append(node.name)
    return function_names


def curses_select_function(function_names):
    """
    Launch a simple TUI with curses to let the user select a function name
    from the given list using up/down arrows. Press Enter to confirm choice.
    Returns the chosen function name.
    """
    def main(stdscr):
        curses.curs_set(0)  # Hide the cursor
        current_row = 0

        curses.start_color()
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)

        def print_menu(stdscr, current_idx):
            stdscr.clear()
            h, w = stdscr.getmaxyx()
            # Calculate a vertical start so the list is somewhat centered
            start_y = max((h - len(function_names)) // 2, 0)

            for idx, fn_name in enumerate(function_names):
                # Center each function name horizontally
                x = w // 2 - len(fn_name) // 2
                y = start_y + idx

                if idx == current_idx:
                    # Highlight the current selection
                    stdscr.attron(curses.color_pair(1))
                    stdscr.addstr(y, x, fn_name)
                    stdscr.attroff(curses.color_pair(1))
                else:
                    stdscr.addstr(y, x, fn_name)
            stdscr.refresh()

        print_menu(stdscr, current_row)

        while True:
            key = stdscr.getch()

            if key == curses.KEY_UP and current_row > 0:
                current_row -= 1
            elif key == curses.KEY_DOWN and current_row < len(function_names) - 1:
                current_row += 1
            # ENTER keys can vary: 10, 13, KEY_ENTER
            elif key in [curses.KEY_ENTER, 10, 13]:
                # Return the selected function name
                return function_names[current_row]

            print_menu(stdscr, current_row)

    return curses.wrapper(main)


def choose_function_from_file(file_path):
    """Prompt the user to select a function from the given file using a TUI."""
    function_names = get_function_names(file_path)

    if not function_names:
        print(f"No functions found in {file_path}.")
        sys.exit(1)

    chosen_function = curses_select_function(function_names)
    return chosen_function


if __name__ == '__main__':
    # If no arguments given or just `python extract_function.py`, show usage
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python extract_function.py <python_file> [function_name]")
        sys.exit(1)

    file_path = sys.argv[1]

    if len(sys.argv) == 2:
        # Only file path given -> open TUI to choose function
        function_name = choose_function_from_file(file_path)
    else:
        # Both file path and function name given -> extract directly
        function_name = sys.argv[2]

    extract_function(file_path, function_name)

