import os
import shutil
import argparse
import re # Import re module
import json # Import json module
import sys # Import sys module to get command line arguments
import datetime # Import datetime module
from collections import defaultdict # Import defaultdict

def get_filtered_relative_paths(base_dir, extensions):
    """
    Generates a set of relative paths for files matching the specified extensions
    from the given base directory.
    """
    if not os.path.isdir(base_dir):
        return set() # Return an empty set if the directory does not exist

    compiled_regexes = []
    patterns_to_compile = []

    # If no extensions are specified, or an empty list, use default '.*'
    if not extensions:
        patterns_to_compile = ['.*']
    else:
        # Convert extension list to regex patterns
        # Example: 'cs' -> '\.cs$'
        patterns_to_compile = [f"\\.{ext}$" for ext in extensions]

    for pattern in patterns_to_compile:
        try:
            # Add re.IGNORECASE to enable case-insensitive matching
            compiled_regexes.append(re.compile(pattern, re.IGNORECASE))
        except re.error as e:
            print(f"Error: Invalid regex pattern '{pattern}' (internal generation): {e}")
            return set() # Return an empty set on regex error

    relative_paths = set()
    for root, _, files in os.walk(base_dir):
        for file in files:
            is_matched = False
            for regex in compiled_regexes:
                if regex.search(file):
                    is_matched = True
                    break
            
            if is_matched:
                # Calculate relative path from the base directory
                relative_path = os.path.relpath(os.path.join(root, file), base_dir)
                # No path separator conversion here for internal processing
                relative_paths.add(relative_path)
    return relative_paths

def sync_files(source_dir, dest_dir, extensions, force_overwrite, dry_run, verbose):
    """
    Copies files matching any of the specified extensions from the source directory
    to the destination directory. Maintains directory structure and overwrites
    existing files by comparing modification times.
    If force_overwrite is True, existing files are unconditionally overwritten.
    If dry_run is True, no actual file copying is performed, and operations are listed.
    If verbose is True, skipped files are also displayed.
    """
    actions_log = [] # Initialize file operation log

    if not os.path.isdir(source_dir):
        print(f"Error: Source directory '{source_dir}' does not exist.")
        return actions_log

    if dry_run:
        print("\n--- Dry Run Mode: No actual file copy will be performed ---")

    # Create destination directory if it doesn't exist (message displayed even in dry run)
    print(f"Creating destination directory '{dest_dir}' {'(planned)' if dry_run else ''}.")
    if not dry_run:
        os.makedirs(dest_dir, exist_ok=True)

    print(f"Starting file copy from '{source_dir}' to '{dest_dir}'.")

    compiled_regexes = []
    patterns_to_compile = []

    if not extensions:
        patterns_to_compile = ['.*']
        print("Target files (extensions): All files (default: '.*')")
    else:
        patterns_to_compile = [f"\\.{ext}$" for ext in extensions]
        print(f"Target files (extensions): {', '.join(extensions)}")

    for pattern in patterns_to_compile:
        try:
            compiled_regexes.append(re.compile(pattern, re.IGNORECASE))
        except re.error as e:
            print(f"Error: Invalid regex pattern '{pattern}' (internal generation): {e}")
            return actions_log


    copied_count = 0
    skipped_count = 0
    overwritten_count = 0

    for root, _, files in os.walk(source_dir):
        for file in files:
            is_matched = False
            for regex in compiled_regexes:
                if regex.search(file):
                    is_matched = True
                    break
            
            if not is_matched:
                continue

            source_file_path = os.path.join(root, file)
            
            relative_path = os.path.relpath(source_file_path, source_dir)
            # Unify path separators to '/' for JSON log
            log_relative_path = relative_path.replace(os.sep, '/') 

            dest_file_path = os.path.join(dest_dir, relative_path)
            
            # Create destination directory if it doesn't exist
            dest_file_dir = os.path.dirname(dest_file_path)
            if not os.path.exists(dest_file_dir):
                print(f"Creating directory '{dest_file_dir}' {'(planned)' if dry_run else ''}.")
                if not dry_run:
                    os.makedirs(dest_file_dir, exist_ok=True)

            source_mtime = os.path.getmtime(source_file_path)
            
            if os.path.exists(dest_file_path):
                if force_overwrite:
                    # If -f option is specified, unconditionally overwrite
                    print(f"Overwriting (forced){' (planned)' if dry_run else ''}: '{source_file_path}' -> '{dest_file_path}'")
                    if not dry_run:
                        shutil.copy2(source_file_path, dest_file_path)
                        overwritten_count += 1
                    actions_log.append({"type": "cpu", "path": log_relative_path}) # Use log_relative_path
                else:
                    dest_mtime = os.path.getmtime(dest_file_path)
                    
                    # Overwrite only if source file is newer than destination file
                    if source_mtime > dest_mtime:
                        print(f"Overwriting{' (planned)' if dry_run else ''}: '{source_file_path}' -> '{dest_file_path}' (newer timestamp)")
                        if not dry_run:
                            shutil.copy2(source_file_path, dest_file_path)
                            overwritten_count += 1
                        actions_log.append({"type": "cpu", "path": log_relative_path}) # Use log_relative_path
                    else:
                        skipped_count += 1
                        if verbose: # Display only if verbose option is True
                            print(f"Skipped: '{source_file_path}' -> '{dest_file_path}' (same or older timestamp)")
                        actions_log.append({"type": "skip", "path": log_relative_path}) # Use log_relative_path
            else:
                # If destination file does not exist, copy as is
                print(f"New copy{' (planned)' if dry_run else ''}: '{source_file_path}' -> '{dest_file_path}'")
                if not dry_run:
                    shutil.copy2(source_file_path, dest_file_path)
                    copied_count += 1
                actions_log.append({"type": "cp", "path": log_relative_path}) # Use log_relative_path

    print("\n--- Copy Complete ---")
    if dry_run:
        print("Dry run mode: No actual file operations were performed.")
    print(f"New files copied: {copied_count}")
    print(f"Files overwritten: {overwritten_count}")
    print(f"Files skipped: {skipped_count}")
    print(f"Total files processed: {copied_count + overwritten_count + skipped_count}")

    return actions_log # Return log

def remove_extra_files(source_dir, dest_dir, extensions, dry_run, verbose):
    """
    Deletes files in the destination directory that do not exist in the source directory.
    If dry_run is True, no actual deletion is performed, and files to be deleted are listed.
    If verbose is True, detailed messages are displayed.
    """
    actions_log = [] # Initialize file operation log

    if not os.path.isdir(dest_dir):
        print(f"Error: Destination directory '{dest_dir}' does not exist. Deletion process will not be performed.")
        return actions_log

    if dry_run:
        print("\n--- Dry Run Mode: No actual file deletion will be performed ---")
    
    print(f"Starting deletion of files in '{dest_dir}' that do not exist in '{source_dir}'.")

    # Generate relative path list of target files in the source directory
    print(f"Generating target file list for '{source_dir}'...")
    source_relative_paths = get_filtered_relative_paths(source_dir, extensions)
    print(f"Target files in '{source_dir}': {len(source_relative_paths)}")

    # Generate relative path list of target files in the destination directory
    print(f"Generating target file list for '{dest_dir}'...")
    dest_relative_paths = get_filtered_relative_paths(dest_dir, extensions)
    print(f"Target files in '{dest_dir}': {len(dest_relative_paths)}")

    # Identify files to be deleted (files in destination but not in source)
    files_to_remove = dest_relative_paths - source_relative_paths

    removed_count = 0
    if not files_to_remove:
        print("\nNo files found for deletion.")
    else:
        print(f"\n{'Will delete' if dry_run else 'Deleting'} the following files from '{dest_dir}':")
        # Sort files to be deleted for consistent output
        for rel_path in sorted(list(files_to_remove)):
            full_path_to_remove = os.path.join(dest_dir, rel_path)
            log_relative_path = rel_path.replace(os.sep, '/') # Unify path separators to '/' for JSON log
            if dry_run:
                print(f"  Planned deletion: '{full_path_to_remove}'")
                actions_log.append({"type": "rm", "path": log_relative_path}) # Log planned deletion in dry run
            else:
                try:
                    os.remove(full_path_to_remove)
                    removed_count += 1
                    print(f"  Deleted: '{full_path_to_remove}'")
                    actions_log.append({"type": "rm", "path": log_relative_path}) # Log actual deletion
                except OSError as e:
                    print(f"  Error: Failed to delete '{full_path_to_remove}': {e}")
        
        # Delete empty directories (from deepest to shallowest)
        print(f"\n{'Will clean up' if dry_run else 'Cleaning up'} empty directories...")
        for root, dirs, files in os.walk(dest_dir, topdown=False):
            if not dirs and not files: # If directory is currently empty
                relative_dir_path = os.path.relpath(root, dest_dir)
                log_relative_dir_path = relative_dir_path.replace(os.sep, '/')
                if dry_run:
                    print(f"  Planned empty directory deletion: '{root}'")
                    actions_log.append({"type": "rmdir", "path": log_relative_dir_path}) # Log planned empty directory deletion in dry run
                else:
                    try:
                        os.rmdir(root)
                        print(f"  Deleted empty directory: '{root}'")
                        actions_log.append({"type": "rmdir", "path": log_relative_dir_path}) # Log actual empty directory deletion
                    except OSError:
                        pass

    print("\n--- Deletion Complete ---")
    if dry_run:
        print("Dry run mode: No actual file operations were performed.")
    print(f"Files deleted: {removed_count}")
    print(f"Total files processed (candidates for deletion): {len(dest_relative_paths)}")

    return actions_log # Return log


def main_cli():
    parser = argparse.ArgumentParser(
        description="A tool to synchronize files between directories."
    )
    
    # Add subcommands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Create parser for 'cp' subcommand
    cp_parser = subparsers.add_parser(
        'cp', 
        help='Copies files from the specified source directory to the destination directory, maintaining the directory structure. Existing files are overwritten based on modification time.'
    )
    cp_parser.add_argument(
        "source_directory",
        help="Path to the source directory"
    )
    cp_parser.add_argument(
        "destination_directory",
        help="Path to the destination directory"
    )
    cp_parser.add_argument(
        "-e", "--extensions",
        action="append",
        help="File extensions to process (e.g., 'cs'). Can be specified multiple times. If not specified, all files are targeted.",
        default=None
    )
    cp_parser.add_argument(
        "-f", "--force",
        action="store_true",
        help="Force overwrite existing files in the destination, regardless of modification time."
    )
    
    # Dry run and log output are mutually exclusive
    cp_group = cp_parser.add_mutually_exclusive_group()
    cp_group.add_argument(
        "-d", "--dry-run",
        action="store_true",
        help="Performs a dry run, listing operations without actual file copying or overwriting."
    )
    cp_group.add_argument(
        "-l", "--log-json",
        nargs='?',  # Make argument optional
        const='.',  # Default value if argument is not provided
        type=str,
        help="Outputs actual file operations in JSON format to the specified directory. Cannot be used with dry-run mode. If no directory is specified, outputs to the current directory."
    )
    cp_parser.add_argument( # Add -v/--verbose option to cp subcommand
        "-v", "--verbose",
        action="store_true",
        help="Displays detailed messages (e.g., skipped files)."
    )

    # Create parser for 'rm' subcommand
    rm_parser = subparsers.add_parser(
        'rm',
        help='Deletes files in the destination directory that do not exist in the source directory.'
    )
    rm_parser.add_argument(
        "source_directory",
        help="Path to the source directory for comparison (files not in this directory will be deleted from the destination)"
    )
    rm_parser.add_argument(
        "destination_directory",
        help="Path to the directory from which files will be deleted"
    )
    rm_parser.add_argument(
        "-e", "--extensions",
        action="append",
        help="File extensions to process (e.g., 'cs'). Can be specified multiple times. If not specified, all files are targeted.",
        default=None
    )
    # Dry run and log output are mutually exclusive
    rm_group = rm_parser.add_mutually_exclusive_group() # Add exclusive group for rm_parser
    rm_group.add_argument(
        "-d", "--dry-run",
        action="store_true",
        help="Performs a dry run, listing operations without actual file deletion."
    )
    rm_group.add_argument( # Add -l/--log-json option to rm subcommand
        "-l", "--log-json",
        nargs='?',  # Make argument optional
        const='.',  # Default value if argument is not provided
        type=str,
        help="Outputs actual file operations in JSON format to the specified directory. Cannot be used with dry-run mode. If no directory is specified, outputs to the current directory."
    )
    rm_parser.add_argument( # Add -v/--verbose option to rm subcommand
        "-v", "--verbose",
        action="store_true",
        help="Displays detailed messages."
    )

    # Create parser for 'sync' subcommand
    sync_parser = subparsers.add_parser(
        'sync',
        help='Synchronizes directories by copying files from source to destination, then deleting files in the destination that do not exist in the source.'
    )
    sync_parser.add_argument(
        "source_directory",
        help="Path to the source directory for synchronization"
    )
    sync_parser.add_argument(
        "destination_directory",
        help="Path to the destination directory for synchronization"
    )
    sync_parser.add_argument(
        "-e", "--extensions",
        action="append",
        help="File extensions to process (e.g., 'cs'). Can be specified multiple times. If not specified, all files are targeted.",
        default=None
    )
    sync_parser.add_argument(
        "-f", "--force",
        action="store_true",
        help="Force overwrite existing files in the destination, regardless of modification time (applies to copy phase)."
    )
    # Dry run and log output are mutually exclusive
    sync_group = sync_parser.add_mutually_exclusive_group()
    sync_group.add_argument(
        "-d", "--dry-run",
        action="store_true",
        help="Performs a dry run, listing operations without actual file operations."
    )
    sync_group.add_argument(
        "-l", "--log-json",
        nargs='?',  # Make argument optional
        const='.',  # Default value if argument is not provided
        type=str,
        help="Outputs actual file operations in JSON format to the specified directory. Cannot be used with dry-run mode. If no directory is specified, outputs to the current directory."
    )
    sync_parser.add_argument( # Add -v/--verbose option to sync subcommand
        "-v", "--verbose",
        action="store_true",
        help="Displays detailed messages (e.g., skipped files)."
    )


    args = parser.parse_args()

    # Path validation check for cp, rm, sync commands
    if args.command in ['cp', 'rm', 'sync']:
        source_abs = os.path.abspath(args.source_directory)
        dest_abs = os.path.abspath(args.destination_directory)

        # Check if destination is a subdirectory of source
        # Add os.sep to ensure it's a proper subdirectory, not just a prefix match
        if dest_abs.startswith(source_abs + os.sep):
            print(f"Error: The destination directory '{args.destination_directory}' "
                  f"cannot be a subdirectory of the source directory '{args.source_directory}'. "
                  "This can lead to infinite loops or data loss. Please specify independent paths.", file=sys.stderr)
            sys.exit(1)

    # Get command line arguments (excluding script name)
    command_line_args = sys.argv[1:] 
    actions_performed = [] # List to store all operation logs
    subcommand_name = None # Store the executed subcommand name

    # Execute subcommand
    if args.command == 'cp':
        actions_performed = sync_files(args.source_directory, args.destination_directory, args.extensions, args.force, args.dry_run, args.verbose)
        subcommand_name = args.command
        
    elif args.command == 'rm':
        actions_performed = remove_extra_files(args.source_directory, args.destination_directory, args.extensions, args.dry_run, args.verbose)
        subcommand_name = args.command

    elif args.command == 'sync':
        print("\n--- Starting synchronization (copy phase) ---")
        cp_actions = sync_files(args.source_directory, args.destination_directory, args.extensions, args.force, args.dry_run, args.verbose)
        actions_performed.extend(cp_actions) # Add copy operation logs

        print("\n--- Continuing synchronization (deletion phase) ---")
        rm_actions = remove_extra_files(args.source_directory, args.destination_directory, args.extensions, args.dry_run, args.verbose)
        actions_performed.extend(rm_actions) # Add deletion operation logs
        
        print("\n--- Synchronization complete ---")
        subcommand_name = args.command

    else:
        # If no subcommand is specified or unknown
        parser.print_help()
        sys.exit(0) # Exit after printing help

    # Log output processing (common for cp, rm, sync commands)
    if args.log_json is not None: # If -l option is specified
        # Get timestamp in system's local timezone
        current_timestamp_dt = datetime.datetime.now().astimezone()
        # Generate filename (including microseconds and timezone offset)
        log_filename = current_timestamp_dt.strftime("dirsync_%Y%m%d_%H%M%S_%f%z.json")
        
        # Log output directory
        log_output_dir = args.log_json
        
        # Create directory if it doesn't exist
        if not os.path.exists(log_output_dir):
            try:
                os.makedirs(log_output_dir)
                print(f"Created log output directory '{log_output_dir}'.")
            except OSError as e:
                print(f"Error: Failed to create log output directory '{log_output_dir}': {e}")
                # Do not output log if directory creation fails
                sys.exit(1) # Exit with error

        log_file_path = os.path.join(log_output_dir, log_filename)

        # Generate summary from actions_performed
        summary = defaultdict(int)
        for action in actions_performed:
            summary[action["type"]] += 1
        
        # Create a list excluding 'skip' type from actions_performed
        filtered_actions_for_log = [action for action in actions_performed if action["type"] != "skip"]

        # Create JSON output data
        json_output_data = {
            "app": "mfdirsync", # Changed from "dirsync"
            "version": 1,
            "timestamp": current_timestamp_dt.isoformat(), # Output in ISO 8601 format
            "cmd": command_line_args,
            "subcmd": subcommand_name, # Name of the executed subcommand
            "summary": dict(summary), # Convert defaultdict to regular dict and store
            "actions": filtered_actions_for_log # Use the filtered list
        }
        try:
            with open(log_file_path, 'w', encoding='utf-8') as f:
                json.dump(json_output_data, f, indent=4, ensure_ascii=False)
            print(f"\nFile operation log output to '{log_file_path}'.")
        except IOError as e:
            print(f"Error: Failed to write JSON log file '{log_file_path}': {e}")

