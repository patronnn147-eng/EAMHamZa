## Claude Code — slash commands and permission flags

**What Claude Code is:** Claude Code is the command-line tool that lets you run Claude
directly in your terminal, inside your actual project folder. It can read files, write
files, run shell commands, and execute tests. This section documents how to control it,
what every important flag does, and which slash commands you will use constantly.

---

### Starting Claude Code with the right flags

**Standard start:** `claude` — opens Claude Code in interactive mode in the current
directory.

**Skip permissions (dangerously skip all prompts):**
```
claude --dangerously-skip-permissions
```
What this does: Claude Code normally asks for confirmation before reading files, writing
files, or running commands — like a safety check. `--dangerously-skip-permissions` turns
off all those checks. Claude will read, write, and execute without asking for approval on
every action. Use this when you trust the task and do not want to click "allow" fifty
times. The word "dangerously" is there on purpose — if Claude makes a mistake, it will
make it without pausing to confirm. Only use in projects where you can recover from
mistakes (git-tracked, backed up, or throw-away code).

**Non-interactive (run a single task and exit):**
```
claude -p "your task here"
```
What this does: Runs a single prompt, prints the response, and exits. No interactive
session. Useful in scripts, CI pipelines, or when you know exactly what you want.

**Non-interactive with permission skip (fully automated):**
```
claude --dangerously-skip-permissions -p "your task here"
```
This is the fully automated mode — runs the task, applies all file changes, executes
all commands, and exits without ever asking for confirmation. Use in CI or automated
scripts where human intervention is not possible.

**Continue the most recent conversation:**
```
claude --continue
```
Picks up exactly where the last session left off — same context, same files.

**Resume a specific conversation:**
```
claude --resume
```
Shows a list of recent sessions to choose from. Select one to continue it.

**Specify a model:**
```
claude --model claude-opus-4-5
```
Default is the latest Sonnet. Use Opus for complex reasoning tasks. Use Haiku for fast,
cheap, simple tasks.

**Set the output format:**
```
claude --output-format json
claude --output-format text
claude --output-format stream-json
```
Useful in scripts where you need to parse Claude's output programmatically.

---

### Slash commands (used inside an active Claude Code session)

These commands are typed directly in the Claude Code chat interface during a session.
They control behavior, context, and the session itself.

---

**`/help`**
Shows all available slash commands with brief descriptions. Run this first in any new
session if you cannot remember a command.

---

**`/clear`**
Clears the conversation history from Claude's memory for the current session. Use when
the context is getting long and confused, or when you want to start a fresh task without
the previous conversation influencing Claude's decisions. Note: this does not undo any
file changes that were already made.

---

**`/compact`**
Compresses the conversation history into a shorter summary while keeping the essential
context. Use this instead of `/clear` when the conversation is getting long but you
still need Claude to remember the key decisions and files from earlier in the session.
Think of it as "summarize what we have discussed so we can keep going without running
out of context."

---

**`/cost`**
Shows how many tokens the current session has used and the approximate cost. Use this
to understand how long and expensive a session is getting. If the cost seems high, use
`/compact` to reduce context.

---

**`/status`**
Shows the current state of Claude Code: which model is being used, what the current
working directory is, which files are in context, and the session configuration.

---

**`/init`**
Initializes Claude Code in the current project — creates a `CLAUDE.md` file if one does
not exist. If this global `CLAUDE.md` is already set up, you do not need to run `/init`,
but it is useful for adding a project-level `CLAUDE.md` with project-specific notes.

---

**`/review`**
Asks Claude to do a code review of the current state of modified files. Claude reads the
changes and gives feedback using the blocker / suggestion / nit taxonomy defined in the
Code Review phase section above.

---

**`/doctor`**
Checks that Claude Code is correctly installed and configured — verifies the CLI version,
checks for updates, and validates the environment. Run this if Claude Code is behaving
unexpectedly.

---

**`/vim`**
Switches to vim keybindings in the Claude Code input. Use if you are comfortable with
vim navigation and want to use it for editing prompts.

---

**`/add-dir <path>`**
Adds a directory to Claude's working context. By default, Claude Code operates in the
current directory. If your project spans multiple directories (`../shared-lib`, for
example), use `/add-dir` to include them. Example: `/add-dir ../shared-components`.

---

**`/bug`**
Opens a pre-filled bug report for Claude Code itself. Use if Claude Code is crashing,
producing wrong outputs, or behaving unexpectedly — this sends the report to Anthropic.

---

### The `CLAUDE.md` file hierarchy

Claude Code looks for `CLAUDE.md` files in three places, and all three are merged:

1. **`~/.claude/CLAUDE.md`** — your global file (this file). Applies to every project
   on your machine. Contains your personal preferences, workflow rules, and the full
   language/architecture knowledge base.

2. **`./CLAUDE.md`** — the project-level file. Lives in the project's root folder.
   Contains project-specific notes: what the project does, the tech stack used, how to
   run it, where the important files are, and any team conventions. Commit this to the
   repo so every team member's Claude Code session uses the same project context.

3. **`./.claude/CLAUDE.md`** — a sub-folder level file. For large monorepos where
   different directories have different rules.

When all three exist, Claude reads and applies all of them. The project-level file takes
precedence over the global file on conflicts. Use the global file for universal
preferences and the project file for project-specific overrides.

**Recommended project-level `CLAUDE.md` template:**
```markdown
# Project: [Name]

## What this is
[One paragraph describing what the project does]

## Stack
- Frontend: [e.g. Next.js 14, TypeScript, Tailwind]
- Backend: [e.g. NestJS, PostgreSQL, Prisma]
- Infrastructure: [e.g. Docker, GitHub Actions, Vercel]

## How to run
- `npm install` — install dependencies
- `npm run dev` — start development server
- `npm test` — run tests
- `npm run db:migrate` — run migrations

## Key files and folders
- `src/app/` — Next.js App Router pages
- `src/components/` — shared React components
- `src/server/` — backend services

## Conventions
- Components use the named export pattern
- API routes return `{ data, error }` shape
- Database queries go in `src/server/db/`

## Do not touch
- `src/generated/` — auto-generated files
- `.env.local` — never read or modify
```

---

### Environment variables for Claude Code

These can be set in your shell profile (`~/.zshrc` or `~/.bashrc`) to apply globally:

```bash
# Set the default model
export ANTHROPIC_MODEL=claude-sonnet-4-5

# Disable the auto-updater
export CLAUDE_CODE_DISABLE_AUTOUPDATE=1

# Set the max tokens for responses (default is usually fine)
export ANTHROPIC_MAX_TOKENS=8192

# Point to a custom API endpoint (for proxies or enterprise deployments)
export ANTHROPIC_BASE_URL=https://your-proxy.example.com
```

---

### Common workflows with Claude Code

**Start every project session with context:**
```
claude --continue
```
Or if starting fresh:
```
claude
> Read the CLAUDE.md and the package.json and give me a one-paragraph summary of what this project is and what stack it uses.
```
This grounds Claude in the project before any tasks begin.

**Automated task (CI or script):**
```bash
claude --dangerously-skip-permissions -p "Run the tests and fix any failing ones. 
Explain each fix."
```

**Review before committing:**
```
claude
> I am about to commit these changes. Review the git diff and tell me if there is 
anything I should fix or reconsider before committing.
```

**Debugging session:**
```
claude
> I am getting this error: [paste error]. Read the relevant files and give me 
the two most likely causes ranked by probability, then tell me exactly what 
to check to confirm which one it is.
```

