# Git Workflow for Zigi Amazon MCP

## Overview
This workflow ensures consistent Git operations across all development work. All features must be developed in feature branches and merged via pull requests with Claude code review.

## 1. Starting New Work

### 1.1 Update Main Branch
```bash
# Ensure you're on main branch
git checkout main

# Fetch latest changes
git fetch origin

# Pull latest changes
git pull origin main
```

### 1.2 Create Feature Branch
```bash
# Create and checkout new feature branch
git checkout -b feature/<feature-name>

# Branch naming conventions:
# - feature/<feature-name> - New features
# - fix/<bug-description> - Bug fixes
# - refactor/<area> - Code refactoring
# - docs/<documentation-area> - Documentation updates
```

## 2. During Development

### 2.1 Regular Sync with Main
```bash
# Fetch latest changes from main
git fetch origin main

# Merge or rebase main into your feature branch
git merge origin/main
# OR
git rebase origin/main
```

### 2.2 Handling Merge Conflicts
```bash
# If conflicts occur during merge/rebase:

# 1. Identify conflicted files
git status

# 2. Open each conflicted file and resolve conflicts
# Look for conflict markers: <<<<<<<, =======, >>>>>>>

# 3. After resolving, stage the files
git add <resolved-files>

# 4. Continue the merge/rebase
git merge --continue
# OR
git rebase --continue

# 5. If you need to abort
git merge --abort
# OR
git rebase --abort
```

## 3. Committing Work

### 3.1 Commit Guidelines
```bash
# Stage specific files (avoid git add .)
git add <specific-files>

# Check what will be committed
git status
git diff --staged

# Commit with meaningful message
git commit -m "feat: Add Amazon product API integration

- Implement product search endpoint
- Add rate limiting for API calls
- Include error handling for API failures

🤖 Generated with Claude Code (https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

### 3.2 Commit Message Format
```
<type>: <subject>

<body>

🤖 Generated with Claude Code (https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, missing semicolons, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

## 4. Creating Pull Requests

### 4.1 Push Feature Branch
```bash
# Push feature branch to remote
git push -u origin feature/<feature-name>
```

### 4.2 Create Pull Request
```bash
# Create PR using GitHub CLI
gh pr create \
  --title "feat: Add Amazon product API integration" \
  --body "$(cat <<'EOF'
## Summary
- Implement Amazon Seller Central API product search functionality
- Add rate limiting to comply with API constraints
- Include comprehensive error handling

## Changes
- New `product_api.py` module for API interactions
- Rate limiter decorator for API calls
- Unit tests for product search functionality

## Test Plan
- [ ] Unit tests pass
- [ ] Integration tests with mock API
- [ ] Manual testing with real API credentials
- [ ] Error scenarios tested

🤖 Generated with Claude Code (https://claude.ai/code)
EOF
)"
```

### 4.3 Request Claude Review
After PR creation, immediately add a comment:
```bash
# Add review request comment
gh pr comment <PR-NUMBER> --body "@claude Please look through this code, stating a workable to-do list of corrections for any issues found"
```

## 5. PR Review Process

### 5.1 Addressing Claude's Feedback
1. Wait for Claude bot to analyze the PR
2. Review the to-do list provided by Claude
3. Make necessary changes in your feature branch
4. Commit and push changes
5. Respond to Claude's comments when resolved

### 5.2 Updating PR
```bash
# Make requested changes
# ... edit files ...

# Commit changes
git add <changed-files>
git commit -m "fix: Address PR review feedback

- Fix error handling as suggested
- Add missing type hints
- Improve test coverage"

# Push updates
git push origin feature/<feature-name>
```

## 6. Merging

### 6.1 Pre-merge Checklist
- [ ] All CI checks pass
- [ ] Claude's review feedback addressed
- [ ] Tests added/updated
- [ ] Documentation updated if needed
- [ ] No merge conflicts with main

### 6.2 Merge via GitHub
```bash
# DO NOT merge locally - use GitHub UI or CLI
gh pr merge <PR-NUMBER> --squash --delete-branch
```

## 7. Post-merge Cleanup

```bash
# Switch back to main
git checkout main

# Pull latest changes
git pull origin main

# Clean up local feature branch
git branch -d feature/<feature-name>

# Remove remote tracking branches
git remote prune origin
```

## Common Issues and Solutions

### Accidental Commit to Main
```bash
# Create a new branch from current state
git checkout -b feature/<feature-name>

# Reset main to origin/main
git checkout main
git reset --hard origin/main
```

### Need to Undo Last Commit
```bash
# Soft reset (keeps changes)
git reset --soft HEAD~1

# Hard reset (discards changes)
git reset --hard HEAD~1
```

### Stashing Work
```bash
# Save current changes
git stash save "WIP: Description of changes"

# List stashes
git stash list

# Apply latest stash
git stash pop

# Apply specific stash
git stash apply stash@{n}
```

## Important Notes

1. **Never commit directly to main** - Always use feature branches
2. **Always request Claude review** - Add the review comment immediately after PR creation
3. **Keep commits atomic** - Each commit should represent one logical change
4. **Update regularly** - Sync with main frequently to avoid large merge conflicts
5. **Test before pushing** - Run `make test` and `make check` before creating PR

## Related Documentation

- [Development Tools Workflow](./development-tools-workflow.md) - Detailed guide for Flask, UV, Python 3.12, and MCP server development