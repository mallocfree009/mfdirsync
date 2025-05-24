# mfdirsync - Unidirectional Directory Synchronization Tool

[English](README.md) | [日本語](README_ja.md)

**[IMPORTANT] This software is distributed under the MIT License and comes without warranty. The developer is not responsible for any issues. Please refer to the LICENSE file for details.**

**[IMPORTANT] While the developer takes care in daily use, there is no guarantee against data loss if used incorrectly or due to bugs. Use at your own risk.**

**[NOTICE] The developer may not be able to respond to pull requests or other contributions. It all depends on the developer's motivation, state of mind, and free time...**

## Overview

`mfdirsync` is a command-line interface (CLI) tool written in Python for synchronizing directories.

It performs file copying and deletion to ensure the destination directory's content matches the source directory. It supports specifying target file extensions and provides a JSON logging feature for operations.

The tool offers the following subcommands for unidirectional file synchronization from a source to a destination directory:

*   `cp`: Copies files that exist only in the source directory, or files that exist in both but are newer in the source, to the destination directory.
*   `rm`: Deletes files from the destination directory that do not exist in the source directory.
*   `sync`: Use this command for a complete synchronization that reflects the latest file states, including deletions. It executes `cp` followed by `rm`.

## Installation

First, install Python. You can install it using your preferred method, such as from the official Python website or Anaconda.

Once Python is installed, run the following command:

```sh
pip install git+https://github.com/mallocfree009/mfdirsync.git
```

This will make the `mfdirsync` command available.

## Detailed Usage

**[IMPORTANT] Caution:**

Specifying a destination directory path that is a subdirectory of the source directory (e.g., `mfdirsync cp ./source ./source/backup`) can lead to issues such as infinite loops or unexpected file deletions. **This is now treated as an error and execution will be stopped.** This restriction applies to all `cp`, `rm`, and `sync` subcommands. Please specify independent paths for the source and destination.

### Command Help

For detailed usage and options of each command, you can use the `-h` or `--help` option:

```bash
mfdirsync -h
mfdirsync cp -h
mfdirsync rm -h
mfdirsync sync -h
```

### Options

*   `-e`, `--extensions <EXT>`: Specifies file extensions to process. Can be specified multiple times for multiple extensions (e.g., `-e cs -e txt`). Regular expression patterns can also be used for extensions. If not specified, all files are targeted.
*   `-f`, `--force`: For copy operations, unconditionally overwrites existing files in the destination, regardless of their modification time.
*   `-d`, `--dry-run`: Runs in dry-run mode. No actual file operations are performed; instead, planned operations are listed.
*   `-l`, `--log-json [DIR]`: Outputs actual file operations in JSON format. If a directory path is specified, the log will be saved directly under that directory with a filename in the format `dirsync_YYYYMMDD_HHMMSS_ffffff+ZZZZ.json`, including the date and time. If no directory path is specified (i.e., only `-l` is used), the log will be output to the current directory. Cannot be used simultaneously with dry-run mode (`-d`).
*   `-v`, `--verbose`: Displays detailed messages (e.g., skipped files) to standard output.

### Subcommand `cp` (Copy)

Copies files from the source directory to the destination directory.

**Features:**
*   Copies new files that exist only in the source directory to the destination.
*   Overwrites files in the destination if they exist in both directories and the source file has a newer modification time.
*   If the `-f` (`--force`) option is specified, existing files are unconditionally overwritten regardless of modification time.

**Examples:**

```bash
# Copy .cs and .txt files from ./my_source to ./my_backup (new and updated only)
mfdirsync cp ./my_source ./my_backup -e cs -e txt

# Force copy all files (new, updated, and forced overwrite)
mfdirsync cp ./project_files ./archive -f

# Dry run for copy operation (no actual copying)
mfdirsync cp ./source ./destination -d

# Log copy operations to a JSON file
mfdirsync cp ./source ./destination -l ./logs

# Copy while displaying skipped files
mfdirsync cp ./source ./destination -v
```

### Subcommand `rm` (Remove)

Deletes files from the destination directory that do not exist in the source directory.

**Features:**
*   Deletes files in the destination directory for which no corresponding file exists in the source directory.
*   Deletes empty directories after file deletion.

**Examples:**

```bash
# Delete .cs and .txt files from ./old_backup that are not in ./original_data
mfdirsync rm ./original_data ./old_backup -e cs -e txt

# Dry run for delete operation (no actual deletion)
mfdirsync rm ./source ./destination -d

# Log delete operations to a JSON file
mfdirsync rm ./source ./destination -l ./logs
```

### Subcommand `sync` (Synchronize)

Performs a complete synchronization by first executing the copy process similar to the `cp` command, and then the deletion process similar to the `rm` command.

**Features:**
*   First, copies and overwrites files using the same logic as `cp`.
*   Then, deletes files that exist only in the destination using the same logic as `rm`.

**Examples:**

```bash
# Fully synchronize .cs and .txt files between ./project_root and ./synced_copy
mfdirsync sync ./project_root ./synced_copy -e cs -e txt

# Force synchronize all files
mfdirsync sync ./source ./destination -f

# Dry run for synchronization operation (no actual operations)
mfdirsync sync ./source ./destination -d

# Log synchronization operations to a JSON file
mfdirsync sync ./source ./destination -l ./logs

# Synchronize while displaying skipped files
mfdirsync sync ./source ./destination -v
```

### JSON Log Format

When the `-l` or `--log-json` option is specified, detailed file operations are output in JSON format.

**Output Example:**

```json
{
    "app": "mfdirsync",
    "version": 1,
    "timestamp": "2023-10-27T10:30:00.123456+09:00",
    "cmd": ["sync", "source_dir", "dest_dir", "-e", "cs"],
    "subcmd": "sync",
    "summary": {
        "cp": 5,
        "cpu": 2,
        "rm": 3,
        "rmdir": 1,
        "skip": 10
    },
    "actions": [
        {"type": "cp", "path": "path/to/new_file.cs"},
        {"type": "cpu", "path": "path/to/updated_file.cs"},
        {"type": "rm", "path": "path/to/deleted_file.txt"},
        {"type": "rmdir", "path": "path/to/empty_dir"}
    ]
}
```

**Field Descriptions:**

*   `app`: Application name (`mfdirsync`).
*   `version`: Log format version.
*   `timestamp`: Date and time when the operation was executed (ISO 8601 format, with timezone information).
*   `cmd`: List of command-line arguments executed.
*   `subcmd`: The subcommand executed (`cp`, `rm`, `sync`).
*   `summary`: A summary of the occurrences for each action type.
    *   `cp`: Number of newly copied files.
    *   `cpu`: Number of files overwritten because the source had a newer modification time, or due to forced overwrite.
    *   `rm`: Number of files deleted (includes files planned for deletion in dry run).
    *   `rmdir`: Number of empty directories deleted (includes directories planned for deletion in dry run).
    *   `skip`: Number of skipped files (files with the same or older modification time in `cp` command). This type is not included in the `actions` list but is included in the summary.
*   `actions`: A list of individual file operations performed. `skip` type actions are not included here.
    *   `type`: Type of operation (`cp`, `cpu`, `rm`, `rmdir`).
    *   `path`: Relative path from the base directory.
