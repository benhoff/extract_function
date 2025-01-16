#!/usr/bin/env python3
import sys
import ast
import curses
import string

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
    Launch a simple TUI with curses to let the user:
      - See a list of all function_names
      - Use the Up/Down arrow keys to move through the list
      - Type alphanumerics (and underscores) to filter the list in real-time
      - Press Enter to confirm choice

    Returns the chosen function name (string) or None if no selection.
    """
    def main(stdscr):
        curses.curs_set(0)  # Hide the cursor
        current_row = 0
        search_query = ""  # the text the user typed to filter the list

        # Initialize curses color
        curses.start_color()
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)

        # Start with all function names in the "filtered list"
        filtered_functions = list(function_names)

        def filter_list(query):
            """Return all function names that contain 'query' (case-insensitive)."""
            q_lower = query.lower()
            return [fn for fn in function_names if q_lower in fn.lower()]

        def print_menu(stdscr, selected_idx, filtered, query):
            stdscr.clear()
            h, w = stdscr.getmaxyx()

            # Print a search prompt on the first line
            search_str = f"Search: {query}"
            stdscr.addstr(0, 0, search_str)

            # Decide where to start printing the list
            start_y = 2  # a couple lines down

            for idx, fn_name in enumerate(filtered):
                x = w // 2 - len(fn_name) // 2
                y = start_y + idx

                if idx == selected_idx:
                    stdscr.attron(curses.color_pair(1))
                    stdscr.addstr(y, x, fn_name)
                    stdscr.attroff(curses.color_pair(1))
                else:
                    stdscr.addstr(y, x, fn_name)

            stdscr.refresh()

        print_menu(stdscr, current_row, filtered_functions, search_query)

        while True:
            key = stdscr.getch()

            if key == curses.KEY_UP:
                if current_row > 0:
                    current_row -= 1
            elif key == curses.KEY_DOWN:
                if current_row < len(filtered_functions) - 1:
                    current_row += 1
            elif key in [curses.KEY_ENTER, 10, 13]:
                # If there's at least one function in the list, return that name
                if filtered_functions:
                    return filtered_functions[current_row]
                else:
                    return None

            # Handle Backspace (different terminals send different codes)
            elif key in [curses.KEY_BACKSPACE, 127, 8]:
                if search_query:
                    search_query = search_query[:-1]
                    filtered_functions = filter_list(search_query)
                    current_row = 0
                    if current_row >= len(filtered_functions):
                        current_row = max(0, len(filtered_functions) - 1)

            # You could optionally handle Esc to cancel:
            # elif key == 27:
            #     return None

            else:
                # If it's a printable character, handle it as part of the search
                # (We allow alphanumeric plus underscore in this example)
                if 0 <= key < 256:
                    ch = chr(key)
                    if ch.isalnum() or ch == '_':
                        search_query += ch
                        filtered_functions = filter_list(search_query)
                        current_row = 0
                        if current_row >= len(filtered_functions):
                            current_row = max(0, len(filtered_functions) - 1)

            print_menu(stdscr, current_row, filtered_functions, search_query)

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
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python extract_function.py <python_file> [function_name]")
        sys.exit(1)

    file_path = sys.argv[1]

    if len(sys.argv) == 2:
        # Only file path given -> open TUI with filtering
        function_name = choose_function_from_file(file_path)
    else:
        # Both file path and function name given -> extract directly
        function_name = sys.argv[2]

    extract_function(file_path, function_name)

