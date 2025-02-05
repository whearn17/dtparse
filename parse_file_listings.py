import argparse
import codecs
import time


def parse_unicode_string(string: str) -> str:
    """
    Parse a string that might contain unicode escape sequences.
    Handles both regular characters and unicode escape sequences.
    """
    try:
        # Handle \u escape sequences
        return codecs.decode(string, 'unicode_escape')
    except Exception as exception:
        print(f"Error while decoding unicode sequences: {exception}")
        return string


def find_file_or_directory_name_start_position(line: str, ignore_characters: str) -> int:
    count = 0

    for char in line:
        if char in ignore_characters:
            count += 1
        else:
            return count
    return count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Parse a file listing, extract directory/file names, and optionally write them out with a specific path prefix."
    )

    parser.add_argument(
        "-i", "--input-file", 
        type=str,
        required=True, 
        help=(
            "Path to the input file containing the directory/file listing. "
            "Each line represents a directory or file, potentially indented to indicate hierarchy."
        )
    )

    parser.add_argument(
        "-o", "--output-file", 
        type=str,
        required=False, 
        help=(
            "Optional path to an output file where the parsed directory/file paths will be written. "
            "If not provided, the results will only be printed in debug mode or processed internally."
        )
    )

    parser.add_argument(
        "-c", "--character-ignore-list", 
        type=str, 
        required=True,
        help=(
            "A string of characters to ignore at the beginning of each line until the actual "
            "directory or file name is found. This string can include Unicode escape sequences "
            "using \\u notation (e.g., '\\u00A0')."
        )
    )

    parser.add_argument(
        "-l", "--indent-level", 
        type=int, 
        required=True,
        help=(
            "Defines how many characters separate a single directory level in the listing. "
            "For example, if a file/directory is indented by 4 spaces from the previous item "
            "and --indent-level=4, that directory would be considered one level deeper than the previous entry."
        )
    )

    parser.add_argument(
        "-p", "--path-prefix", 
        type=str, 
        required=False, 
        default="C:",
        help=(
            "A prefix (such as a drive letter or relative path) to prepend to all parsed paths. "
            "Common examples include 'C:', 'D:', or '.'. Defaults to 'C:'."
        )
    )

    parser.add_argument(
        "-u", "--unix-separators", 
        type=bool, 
        required=False, 
        default=False,
        help=(
            "If True, use UNIX-style '/' path separators in the output. "
            "If False (the default), use Windows-style '\\' path separators."
        )
    )

    parser.add_argument(
        "-d", "--debug", 
        type=bool, 
        required=False, 
        default=False,
        help=(
            "Enable debug mode. If set to True, additional debug information will be printed "
            "to the console, including intermediate path calculations."
        )
    )  

    args = parser.parse_args()

    # Parse the ignore characters string to handle Unicode escape sequences
    ignore_chars = parse_unicode_string(args.character_ignore_list)

    path_separators = "\\"

    if args.unix_separators:
        path_separators = "/"

    file_listing_lines = []
    path_stack = []

    with open(args.input_file, "r", encoding="utf-8") as f:
        file_listing_lines = f.readlines()


    path_stack.append(args.path_prefix)

    output_file = None

    if args.output_file:
        output_file = open(args.output_file, "w", encoding="utf-8")

    for line in file_listing_lines:
        starting_position = find_file_or_directory_name_start_position(line, ignore_chars)

        file_or_directory_name = line[starting_position:].strip()

        current_directory_level = int(starting_position / args.indent_level)

        while current_directory_level < len(path_stack) - 1:
            path_stack.pop()

        if current_directory_level == len(path_stack) and not len(path_stack) == 0:
            path_stack.pop()

        path_stack.append(file_or_directory_name)

        if args.debug:
            print(f"Working on line: {line.strip()}")
            print(f"Starting position of file or directory: {starting_position}")
            print(f"Stop character: {line[starting_position]}")
            print(f"Extracted file or directory name: {file_or_directory_name}")
            print(f"Current directory level: {current_directory_level}\n")
            time.sleep(1)

        # print(f"Current path stack: {f'{path_separators}'.join(map(str, path_stack))}")

        if args.output_file:
            output_file.write(f'{path_separators}'.join(map(str, path_stack)))
            output_file.write("\n")

    output_file.flush()
    output_file.close()
