# Stale-Repository-Checker
Checks the subdirectories of a directory (or the passed directory itself) for stale git repositories.


## About
---
The Intended usage of this script is to check if a directory or a root directory git repository is stale.
Stale is defined as being out of sync with either the remote or the local branch.

## Usage
---
Check if any of the subdirectories in ```~/projects``` are stale. List any modified/untracked files. Colorize the output. Look into a maximum of 2 subdirectories.
```bash
stale-repo-checker ~/projects -lcd2
```



## To-Do
---
- [ ] Look into fetching the remote branch before checking if the local branch is stale
- [ ] Add option to skip remote branches
- [ ] Add option to skip local branches