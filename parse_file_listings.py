import argparse
import codecs
import logging
import os
import sys
import time

# Try importing tqdm for progress indication (optional)
try:
    from tqdm import tqdm
except ImportError:
    tqdm = None


def parse_unicode_string(string: str) -> str:
    """
    Parse a string that might contain Unicode escape sequences.
    
    Handles both regular characters and Unicode escape sequences.
    """
    try:
        # Handle \u escape sequences (e.g., '\\u00A0')
        return codecs.decode(string, 'unicode_escape')
    except Exception as exception:
        logging.error(f"Error while decoding Unicode sequences: {exception}")
        return string


def find_file_or_directory_name_start_position(line: str, ignore_characters: str) -> int:
    """
    Returns the index where the actual file/directory name starts in a given line,
    ignoring any leading characters that are in 'ignore_characters'.
    """
    count = 0
    for char in line:
        if char in ignore_characters:
            count += 1
        else:
            return count
    return count


def process_file_listing(args):
    # --- Input File Validation and Error Handling ---
    if not os.path.isfile(args.input_file):
        logging.error(f"Input file '{args.input_file}' does not exist or is not a file.")
        sys.exit(1)

    try:
        with open(args.input_file, "r", encoding=args.encoding) as f:
            file_listing_lines = f.readlines()
    except Exception as e:
        logging.error(f"Failed to read input file '{args.input_file}': {e}")
        sys.exit(1)

    # --- Enhanced Unicode Support ---
    ignore_chars = parse_unicode_string(args.character_ignore_list)

    # Determine the correct path separator
    path_separator = "/" if args.unix_separators else "\\"

    path_stack = [args.path_prefix]
    output_lines = []

    # --- Progress Indicator ---
    disable_progress_bar = args.debug or (args.output_file is None)
    if tqdm is not None:
        iterator = tqdm(file_listing_lines, desc="Processing lines", disable=disable_progress_bar)
    else:
        iterator = file_listing_lines

    for line in iterator:
        # Skip empty lines
        if line.strip() == "":
            continue

        starting_position = find_file_or_directory_name_start_position(line, ignore_chars)
        file_or_directory_name = line[starting_position:].strip()
        current_directory_level = int(starting_position / args.indent_level)

        # --- Enhanced Logging and Debugging ---
        logging.debug(f"Line: {line.strip()}")
        logging.debug(f"Starting position: {starting_position}")
        if starting_position < len(line):
            logging.debug(f"Stop character: {line[starting_position]}")
        logging.debug(f"Extracted name: {file_or_directory_name}")
        logging.debug(f"Current directory level: {current_directory_level}")
        logging.debug(f"Current path stack: {path_separator.join(path_stack)}")

        # Adjust the path stack based on the current directory level
        while current_directory_level < len(path_stack) - 1:
            path_stack.pop()

        if current_directory_level == len(path_stack) - 1 and len(path_stack) - 1 != 0:
            path_stack.pop()

        path_stack.append(file_or_directory_name)
        output_lines.append(path_separator.join(path_stack))

        # --- Debug Delay ---
        if args.debug and getattr(args, "debug_delay", 0) > 0:
            time.sleep(args.debug_delay)

    # --- Dry-run Mode ---
    if args.dry_run or not args.output_file:
        print("\n".join(output_lines))
    else:
        try:
            with open(args.output_file, "w", encoding=args.encoding) as f_out:
                f_out.write("\n".join(output_lines))
            logging.info(f"Output written to '{args.output_file}'")
        except Exception as e:
            logging.error(f"Failed to write to output file '{args.output_file}': {e}")
            sys.exit(1)


def character_detection_mode(args):
    """
    Interactively step through each non-empty line in the input file,
    display the current stop character (the first character not in the ignore list),
    and allow the user to add that character to a blocklist.
    
    Key Bindings:
      s - step to the next line
      b - block (add) the current character to the blocklist
      r - run the file listing conversion with the current blocklist
      q - quit the character detection mode without running conversion
    """
    # --- Input File Validation and Error Handling ---
    if not os.path.isfile(args.input_file):
        logging.error(f"Input file '{args.input_file}' does not exist or is not a file.")
        sys.exit(1)
    try:
        with open(args.input_file, "r", encoding=args.encoding) as f:
            file_listing_lines = f.readlines()
    except Exception as e:
        logging.error(f"Failed to read input file '{args.input_file}': {e}")
        sys.exit(1)

    blocklist = []  # Characters the user wants to block
    base_ignore = parse_unicode_string(args.character_ignore_list)

    print("\n=== Entering Character Detection Mode ===")
    print("Key Bindings: [s]tep, [b]lock current char, [r]un conversion with current blocklist, [q]uit")
    
    for idx, line in enumerate(file_listing_lines):
        if line.strip() == "":
            continue

        # Allow multiple passes on the same line if the user keeps blocking characters
        while True:
            # Update ignore list by combining the base ignore characters and any blocked ones
            current_ignore = base_ignore + ''.join(blocklist)
            starting_position = find_file_or_directory_name_start_position(line, current_ignore)
            if starting_position < len(line):
                current_char = line[starting_position]
            else:
                current_char = None

            print(f"\nLine {idx+1}: {line.rstrip()}")
            print(f"Current ignore list: {repr(current_ignore)}")
            print(f"Blocklist: {blocklist}")
            print(f"Detected starting position: {starting_position}")
            if current_char is not None:
                print(f"Detected stop character: '{current_char}'")
            else:
                print("No non-ignored character found on this line.")

            key = input("Press [s] to step, [b] to block current char, [r] to run conversion, or [q] to quit: ").strip().lower()
            if key == 'b':
                if current_char is None:
                    print("Nothing to block on this line; stepping to the next line.")
                    break
                if current_char in blocklist:
                    print(f"Character '{current_char}' is already blocked.")
                else:
                    blocklist.append(current_char)
                    print(f"Added '{current_char}' to blocklist.")
                    # Recalculate the starting position for the same line with the updated ignore list.
                    continue
            elif key == 'r':
                # Update the args' ignore list with the current blocklist
                args.character_ignore_list = base_ignore + ''.join(blocklist)
                print("\nRunning file listing conversion with the current blocklist...")
                process_file_listing(args)
                return
            elif key == 's':
                break  # Move to next line.
            elif key == 'q':
                print("Quitting character detection mode.")
                print("Final blocklist:", blocklist)
                return
            else:
                print("Invalid input. Please try again.")
    print("\n=== Character Detection Mode Complete ===")
    print("Final blocklist:", blocklist)


def interactive_mode():
    """
    Interactive prompt for users when no command-line arguments are provided.
    Allows selection between normal processing and character detection mode.
    
    Note: The program now first asks whether you want to use character detection mode.
    """
    print("Entering interactive mode. Please provide the following information:")
    input_file = input("Input file path: ").strip()
    char_detect_input = input("Do you want to use character detection mode? (yes/no, default no): ").strip().lower()
    char_detect = True if char_detect_input in ['yes', 'y'] else False
    character_ignore_list = input("Characters to ignore (e.g., '\\u00A0'): ").strip()
    indent_level = input("Indent level (number of characters per level, e.g., 4): ").strip()
    path_prefix = input("Path prefix (default 'C:'): ").strip() or "C:"
    unix_separators_input = input("Use UNIX separators? (yes/no, default no): ").strip().lower()
    unix_separators = True if unix_separators_input in ['yes', 'y'] else False
    encoding = input("File encoding (default 'utf-8'): ").strip() or "utf-8"
    dry_run_input = input("Dry run mode? (yes/no, default no): ").strip().lower()
    dry_run = True if dry_run_input in ['yes', 'y'] else False

    debug_input = input("Enable debug mode? (yes/no, default no): ").strip().lower()
    debug = True if debug_input in ['yes', 'y'] else False

    debug_delay = 0.0
    if debug:
        debug_delay_input = input("Enter debug delay in seconds (default 0): ").strip()
        try:
            debug_delay = float(debug_delay_input) if debug_delay_input else 0.0
        except ValueError:
            debug_delay = 0.0

    # Create a simple object to mimic argparse.Namespace
    class Args:
        pass

    args = Args()
    args.input_file = input_file
    args.character_ignore_list = character_ignore_list
    args.indent_level = int(indent_level) if indent_level.isdigit() else 4
    args.path_prefix = path_prefix
    args.unix_separators = unix_separators
    args.encoding = encoding
    args.output_file = None  # In interactive mode, output is printed to the console
    args.dry_run = dry_run
    args.debug = debug
    args.debug_delay = debug_delay
    args.char_detect = char_detect
    return args


def run_tests():
    """
    Run unit tests for key functions.
    """
    import unittest

    class TestFileListingConverter(unittest.TestCase):
        def test_parse_unicode_string_valid(self):
            # Test valid Unicode escapes.
            self.assertEqual(parse_unicode_string("\\u00A0"), "\u00A0")
            self.assertEqual(parse_unicode_string("Test\\u0020String"), "Test String")

        def test_parse_unicode_string_invalid(self):
            # An invalid Unicode escape should return the original string.
            result = parse_unicode_string("\\u00G0")
            self.assertEqual(result, "\\u00G0")

        def test_find_file_or_directory_name_start_position(self):
            ignore_chars = " \t"
            line = "    filename.txt"
            # With 4 leading spaces, the index should be 4.
            self.assertEqual(find_file_or_directory_name_start_position(line, ignore_chars), 4)

            line2 = "\t\tfolder"
            self.assertEqual(find_file_or_directory_name_start_position(line2, ignore_chars), 2)

            line3 = "filename"
            self.assertEqual(find_file_or_directory_name_start_position(line3, ignore_chars), 0)

    suite = unittest.TestLoader().loadTestsFromTestCase(TestFileListingConverter)
    unittest.TextTestRunner(verbosity=2).run(suite)


if __name__ == "__main__":
    # If no arguments are provided, start in interactive mode.
    if len(sys.argv) == 1:
        args = interactive_mode()
    else:
        parser = argparse.ArgumentParser(
            description="Parse a file listing, extract directory/file names, and optionally write them out with a specific path prefix."
        )
        parser.add_argument("-i", "--input-file", type=str, required=False,
                            help="Path to the input file containing the directory/file listing.")
        parser.add_argument("-o", "--output-file", type=str, required=False,
                            help="Optional path to an output file for the parsed paths.")
        parser.add_argument("-c", "--character-ignore-list", type=str, required=True,
                            help="Characters to ignore at the beginning of each line (supports Unicode escapes).")
        parser.add_argument("-l", "--indent-level", type=int, required=True,
                            help="Number of characters that represent one indent level.")
        parser.add_argument("-p", "--path-prefix", type=str, default="C:",
                            help="Path prefix to prepend to parsed paths. Defaults to 'C:'.")
        parser.add_argument("-u", "--unix-separators", action='store_true',
                            help="Use UNIX-style '/' separators instead of Windows '\\'.")
        parser.add_argument("--encoding", type=str, default="utf-8",
                            help="File encoding for input and output files. Defaults to 'utf-8'.")
        parser.add_argument("--dry-run", action='store_true',
                            help="Process the file and output results to console without writing to an output file.")
        parser.add_argument("-d", "--debug", action='store_true',
                            help="Enable debug mode with verbose logging.")
        parser.add_argument("--debug-delay", type=float, default=0.0,
                            help="Delay (in seconds) between processing lines in debug mode.")
        parser.add_argument("--char-detect", action='store_true',
                            help="Enable interactive character detection mode.")
        parser.add_argument("--test", action='store_true',
                            help="Run unit tests and exit.")
        args = parser.parse_args()

        # Run unit tests if the --test flag is provided.
        if args.test:
            run_tests()
            sys.exit(0)

        # In non-interactive mode, input_file is required.
        if not args.input_file:
            parser.error("the following argument is required: -i/--input-file")

    # --- Enhanced Logging Setup ---
    logging_level = logging.DEBUG if getattr(args, "debug", False) else logging.INFO
    logging.basicConfig(
        level=logging_level,
        format="%(asctime)s - %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # If character detection mode is enabled, run that mode instead.
    if getattr(args, "char_detect", False):
        character_detection_mode(args)
    else:
        process_file_listing(args)