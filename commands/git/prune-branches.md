Invoke the prune-branches git command to clean the old local branches.

```git config --global alias.prune-branches '!git fetch --prune && git branch -vv | grep '"'"': gone]'"'"' | awk '"'"'{print $1}'"'"' | xargs git branch -d'```

Use: git prune-branches
