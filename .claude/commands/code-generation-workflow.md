# Code Generation Workflow

This workflow defines the logging format to use during code generation and file modifications, including automatic logging to a project-level logs directory.

## Logging System

### Log File Management
1. **Directory**: Create logs in `/logs/` at the project root
2. **File Naming**: `<feature-or-bug-name>_<YYYY-MM-DD_HH-MM>.md`
   - Example: `user-authentication_2024-01-15_14-30.md`
   - Example: `fix-database-connection_2024-01-15_15-45.md`

### Log File Reuse Rules
- **Reuse existing log** when:
  - Working on the same feature/bug within the same session
  - Making iterative improvements to recently modified code
  - The most recent log for this feature is less than 4 hours old
- **Create new log** when:
  - Starting a new feature or bug fix
  - Returning to a feature after significant time (>4 hours)
  - The user explicitly requests a new task

### Log File Structure
```markdown
# <Feature/Bug Name>
**Started**: <timestamp>
**Last Updated**: <timestamp>

## Task List
- [ ] <Task 1: Brief description>
- [ ] <Task 2: Brief description>
- [ ] <Task 3: Brief description>
- [ ] <Task 4: Brief description>
- [ ] <Task N: Brief description>

## Change Log

### [HH:MM:SS] <Action Description>
**Rationale**: <why this change>
**Files Modified**: <list of files>
<optional details>

---
```

### Task List Requirements
1. **Generate before any changes**: Always create a comprehensive task list before making any modifications
2. **Be exhaustive**: Include all steps, even small ones like "verify installation" or "run tests"
3. **Order logically**: Tasks should follow a logical implementation sequence
4. **Update status**: Mark tasks as completed with [x] as you progress
5. **Add new tasks**: If you discover additional required tasks during implementation, add them to the list

### When Reusing Log Files
When appending to an existing log file:
1. Add a separator line: `========== NEW SESSION ==========`
2. Add new timestamp and task list for the current session
3. Continue with the change log entries below

## Format Structure

For every code change, follow this pattern:

### 1. Action Description (1-2 lines)
- Briefly explain what you are doing
- Be concise but clear about the specific action

### 2. Rationale (1-4 lines)
- Explain why you are making this change
- Describe how it corrects a bug or adds a feature
- Include the expected outcome or benefit
- Connect to the broader context if relevant

### 3. Important Details (Optional, up to 4 lines)
- Note if the change cannot be undone
- List any new package installations required
- Highlight breaking changes or compatibility issues
- Mention any required user confirmation before proceeding

## Rules

1. **No extraneous text** between changes unless:
   - At the start of a task
   - At the end of a task
   - A specific question requires user input

2. **Ask before proceeding** when:
   - Changes cannot be undone
   - New dependencies are required
   - Breaking changes will occur

3. **Keep descriptions dense but informative**:
   - Avoid redundancy
   - Focus on "what" and "why"
   - Include technical details only when necessary

## Example Log Entry

```markdown
# User Authentication Feature
**Started**: 2024-01-15 14:30:00
**Last Updated**: 2024-01-15 14:45:23

## Task List
- [x] Create database migration for user authentication table
- [x] Design user model with required fields
- [x] Implement JWT token generation service
- [x] Create authentication middleware
- [x] Update API endpoints with authentication
- [ ] Write unit tests for auth service
- [ ] Add integration tests for protected endpoints
- [ ] Update API documentation
- [ ] Add error handling for invalid tokens

## Change Log

### [14:30:15] Creating database migration for user authentication table
**Rationale**: This adds a users table with email, password hash, and timestamp fields to support the new authentication feature. The migration will enable user registration and login functionality required by the auth system.
**Files Modified**: `migrations/001_create_users_table.sql`, `src/models/user.py`

---

### [14:35:42] Implementing JWT token generation in auth service
**Rationale**: Adding token creation logic to generate secure JWTs for authenticated users, fixing the security vulnerability where sessions were not properly managed. This uses the existing cryptography library and follows OWASP best practices.
**Files Modified**: `src/services/auth.py`, `src/utils/jwt_handler.py`
**WARNING**: This requires the pyjwt package to be installed. Should I proceed with adding it to requirements?

---

### [14:45:23] Updating API endpoint to validate authentication tokens
**Rationale**: Modifying the /api/protected route to check for valid JWT tokens in request headers. This completes the authentication flow by ensuring only authenticated users can access protected resources.
**Files Modified**: `src/api/routes.py`, `src/middleware/auth.py`

---
```

## Implementation Notes

1. **Always create the logs directory** if it doesn't exist before writing
2. **Use descriptive feature names** in log filenames (kebab-case preferred)
3. **Include timestamps** for both file creation and each entry
4. **List all modified files** for traceability
5. **Append to existing logs** when working on the same feature
6. **Create new logs** for distinct features or after time gaps
