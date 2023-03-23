#!/bin/env python3

"""
    Stale Directory Checker

    Checks if any directories in a given root directory are stale (i.e. contain a git repository with uncommitted/untracked changes or behind/ahead of the remote)

    Author: Kyle W.
    Date: 2023-01-11
    Version: 0.0.1
    License: GPL-3.0-or-later

    Dependencies: see requirements.txt
        install with: pip install -r requirements.txt
        generate with: update_requirements.sh or update_requirements.ps1

"""


##############################################################################

### Imports ###

# Version guard
import sys
if sys.version_info < (3, 10):
    print("Python 3.10 or later is required.")
    sys.exit(1)

import os
from git import Repo
from git.exc import InvalidGitRepositoryError
import argparse
from typing import Dict, Union, Set, Tuple, NewType, NamedTuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

from colorama import init as colorama_init
from colorama import Fore, Style

colorama_init()

##############################################################################

# Obtain a root directory to check directories in
# Check and report which directories are 'stale'


#### Typedefs ####

class RepoFiles(NamedTuple):
    modified: list[str] = []
    untracked: list[str] = []

# StaleResult = Tuple[str, bool, list[str]]
class StaleResult(NamedTuple):
    directory: str
    stale: bool
    status_message: str = ""
    files: RepoFiles = RepoFiles()


#### Constants ####

COLOR_REPO      = Fore.GREEN
COLOR_STATUS    = Fore.LIGHTCYAN_EX
COLOR_FILE      = Fore.LIGHTWHITE_EX
COLOR_UNTRACKED = Fore.LIGHTYELLOW_EX
COLOR_MODIFIED  = Fore.LIGHTRED_EX

STYLE_REPO      = Style.BRIGHT
STYLE_STATUS    = Style.BRIGHT
STYLE_FILE      = Style.DIM
STYLE_UNTRACKED = Style.DIM
STYLE_MODIFIED  = Style.DIM


#### Methods ####

def insert_indentation(text: str, indentation: str, quantity=1) -> str:
    """Insert indentation before each line of text."""
    ident = indentation * quantity
    return ident + text.replace("\n", f"\n{ident}")


def setup_logging(verbosity: int) -> None:
    """Setup logging based on verbosity level."""
    # NotSet = 0
    # DEBUG = 10    -vvv
    # INFO = 20     -vv
    # WARNING = 30  -v
    # ERROR = 40    default
    # CRITICAL = 50 default

    log_level = logging.ERROR - (10 * min(3, verbosity)) # This is silly

    logging.basicConfig(level=logging.ERROR, format="%(levelname)s: %(message)s")
    logger.setLevel(log_level)


def get_repo_commit_diff(repo: Repo) -> int:
    """Returns the number of commits ahead or behind the active branch's remote. Positive if ahead, negative if behind."""
    local_branch = repo.active_branch
    if len(repo.remotes) == 0:
        return 0
    remote = repo.remote()
    remote_branch = remote.refs[local_branch.name]
    return local_branch.commit.count() - remote_branch.commit.count()


def get_repo_status(repo: Repo) -> str:
    """Get the status message of a git repository. (How many commits ahead/behind, etc.)"""
    # status = repo.git.status()
    status = ""

    diff = get_repo_commit_diff(repo)
    if diff != 0:
        adverb = "ahead" if diff > 0 else "behind"
        local_branch = repo.active_branch
        if len(repo.remotes) == 0:
            return 0
        remote = repo.remote()
        remote_branch = remote.refs[repo.active_branch.name]
        status += f"'{local_branch.name}' is {adverb} '{remote_branch.name}' by {abs(diff)} commits."
    
    return status


def get_repo_modified_files(repo: Repo) -> list[str]:
    """Get a list of modified files in a git repository."""
    # modified_files = repo.git.diff("--name-only").splitlines()
    modified_files = [item.a_path for item in repo.index.diff(None)]
    return modified_files

def get_repo_untracked_files(repo: Repo) -> list[str]:
    """Get a list of untracked files in a git repository."""
    # untracked_files = repo.git.ls_files("--others", "--exclude-standard").splitlines()
    untracked_files = repo.untracked_files
    return untracked_files


def is_repo_dirty(repo: Repo) -> bool:
    """Check if a repo has any uncommited changes or is ahead/behind the remote."""
    is_dirty = repo.is_dirty()
    if not is_dirty:
        # Check if the local branch is behind/ahead of the remote
        local_branch = repo.active_branch
        if len(repo.remotes) == 0:
            return 0
        remote = repo.remote()
        remote_branch = remote.refs[local_branch.name]
        is_dirty = local_branch.commit != remote_branch.commit
    return is_dirty


# TODO: Should the depth only be checked if the parent isn't a git repo?
def check_directory(directory: str) -> StaleResult:
    """Check if a directory is a git repository and if it has any uncommitted changes. Checks remote if not dirty."""
    logger.debug("Checking directory: [%s]", directory)
    files_list = {
        "modified": [],
        "untracked": []
    }

    try:
        repo = Repo(directory)
        # Add modified and untracked files to the list
        files_list["modified"].extend(get_repo_modified_files(repo))
        files_list["untracked"].extend(get_repo_untracked_files(repo))

        # print(f"{directory}")
        # print(f"untracked: {len(files_list['untracked'])}, modified: {len(files_list['modified'])}")

        is_dirty = is_repo_dirty(repo)
        
        if is_dirty:
            logger.info("Directory is dirty: [%s]", directory)

        return StaleResult(directory, is_dirty, "", RepoFiles(**files_list))
        
    except InvalidGitRepositoryError:
        logger.debug("Directory is not a git repository: [%s]", directory)
        return StaleResult(directory, False)
    except Exception as e:
        logger.error("Error checking directory: %s", e)
        return StaleResult(directory, False)


#### Output Helpers ####

def output_repo(args: argparse.Namespace, result: StaleResult, diff: int):
    """Output the name of the repository and the number of commits ahead/behind the remote. Automatically handles colorization."""
    diff_sign = "+" if diff > 0 else "-"

    if args.colorize:
        color_diff = Fore.LIGHTGREEN_EX if diff > 0 else Fore.LIGHTRED_EX

        print(f"{COLOR_REPO}{STYLE_REPO}{result.directory}{Style.RESET_ALL} [{color_diff}{diff_sign}{abs(diff)}{Style.RESET_ALL}]{Style.RESET_ALL}")
    else:
        print(f"{result.directory} [{diff_sign}{abs(diff)}]")

def output_status(args: argparse.Namespace, status: str):
    """Output the status of the repository. Automatically handles colorization."""
    if not args.status:
        return

    status = status.strip()
    if args.colorize:
        status = f"{COLOR_STATUS}{STYLE_STATUS}{status}{Style.RESET_ALL}"

    status = insert_indentation(status, args.indent)

    print(status)


def output_files(args: argparse.Namespace, files: RepoFiles):
    """Output the modified and untracked files lists. Automatically handles colorization."""
    if not args.status:
        return

    if args.list_files:
        if len(files.modified) == 0 and len(files.untracked) == 0:
            return

        def output_files(files: list[str], color: str=COLOR_FILE, style: str=STYLE_FILE):
            text = ""
            for name in files:
                if args.colorize:
                    text = f"{color}{style}{name}{Style.RESET_ALL}"
                    # TODO: Instead of checking the arg for each output function, create a "get_colorize" function that will return the correct codes or nothing based on that argument.
                    # i.e. text = f"{get_colorize(args.colorize, "MODIFIED")}{name}{get_colorize()}
                else:
                    text = name

                text = insert_indentation(text, args.indent, 2)
                print(text)

        if len(files.modified) > 0:
            print(insert_indentation("Modified:", args.indent))
            output_files(files.modified, COLOR_MODIFIED, STYLE_MODIFIED)

        if len(files.untracked) > 0:
            output_blank(args)
            print(insert_indentation("Untracked:", args.indent))
            output_files(files.untracked, COLOR_UNTRACKED, STYLE_UNTRACKED)


def output_blank(args: argparse.Namespace):
    """Output a newline to separate the output of multiple repositories. Resets colorization if enabled."""
    if args.colorize:
        print(f"{Style.RESET_ALL}")
    else:
        print("")


#### Main ####

def main(args):
    """Check if the passed root directory or any of it's subdirectories contains a git repository with uncommitted changes."""
    setup_logging(args.verbose)
    root_directory = args.root
    logger.info("Checking root directory: %s", args.root)

    # First check if the supplied directory is a git repository itself. If it is, assume this is the only directory to check.
    result = check_directory(root_directory)

    max_depth = args.depth
    walked_depth = 0

    results: list[StaleResult] = []

    # Glob the root directory for directories
    for subdir, dirs, files in os.walk(root_directory):
        walked_depth += 1

        for directory in dirs:
            full_path = os.path.join(subdir, directory)
            result = check_directory(full_path)
            
            results.append(result)

        if walked_depth >= max_depth:
            break

    # Remove any directories that aren't stale
    results = [result for result in results if result.stale]
    # Then sort and print results
    results.sort(key=lambda x: x[0])
    for result in results:
        if not result.stale:
            continue

        status = get_repo_status(Repo(result.directory))
        diff = get_repo_commit_diff(Repo(result.directory))
        color_diff = Fore.LIGHTGREEN_EX if diff > 0 else Fore.LIGHTRED_EX
        diff_sign = "+" if diff > 0 else "-"

        output_repo(args, result, diff)
        output_status(args, status)
        output_files(args, result.files)
        output_blank(args)


##############################################################################


#### Startup ####

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("root", help="Root directory to check")
    parser.add_argument("-v", "--verbose", help="increase output verbosity", action="count", default=0)
    parser.add_argument("-d", "--depth", help="Depth of tree to check for stale directories. 1-99", type=int, default=1)
    parser.add_argument("-l", "--list", help="List untracked/modified files", action="store_true", dest="list_files")
    parser.add_argument("-c", "--color", help="Colorize output", action="store_true", dest="colorize")
    parser.add_argument("-S", "--no-status", help="Don't show status", action="store_false", dest="status")
    parser.add_argument("-i", "--indent", help="String to insert per level of indentation.", type=str, default="\t")
    args = parser.parse_args()

    # Validation???
    if 1 > args.depth > 99: # (depth < 1 or depth > 99) Python's chained comparison is cool!
        logger.warning("Depth '%i' is outside of range 1-99. Defaulting to 1!", args.depth)
        args.depth = 1
    else:
        args.depth = max(min(args.depth, 99), 1) # constrain to 1-99


    main(args)
