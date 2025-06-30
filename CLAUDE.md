# CLAUDE.md

**IMPORTANT**: This file is read-only. Claude Code must NOT edit this file. All architecture and test documentation should be maintained in the imported files listed below.

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Imported Documentation

The following files contain detailed documentation that Claude Code should reference and maintain:

1. **[CLAUDE-architecture.md](./CLAUDE-architecture.md)** - System architecture, classes, and database schema
   - Claude Code MUST maintain this file as the codebase evolves
   - Update when adding/modifying classes, APIs, or architectural patterns

2. **[tests/CLAUDE-tests.md](./tests/CLAUDE-tests.md)** - Test suite documentation
   - Claude Code MUST maintain this file when creating or modifying tests
   - Update when adding new test files or test scenarios

3. **./.claude/CLAUDE-mylocaldevenvironment.md** - Local development environment details
   - Read-only file describing the Linux VM, Parallels setup, Docker containers
   - Claude Code must NOT edit this file (if it exists)

4.  **[README.md](./README.md)** - User Guide on how to use the package
   - Claude Code MUST maintain this file as the codebase evolves
   - Update when adding/modifying with how users interact with the package

## Planning Process

All significant changes MUST start with a planning document:

1. **Create/Update Planning Doc**: 
   - Use a single planning document per feature branch
   - Name format: `planning-docs/feature-branch-name.md`
   - For current branch: `planning-docs/modularize-june282025.md`
2. **User Review**: User reads and provides feedback via conversation
3. **Iterate**: Claude Code updates the same planning doc based on feedback
4. **Implement**: Use finalized planning doc to guide implementation

Planning documents should include:
- Overview and motivation
- Technical approach
- Impact analysis
- Testing strategy
- Migration plan (if applicable) including files that will need to be updated or deleted.

**Note**: Each feature branch should maintain a single planning document that evolves throughout the planning phase, rather than creating multiple dated documents.

## User Usage
Start YOLO Session:
```bash
claude --dangerously-skip-permissions
```

Start with planning a feature:
> I want to greatly simplify this library. let's make the core features very very good. Given a very large google meets recording, we want the audio from the meeting, a transcription of the meeting, and generated notes from the meeting, and a way to share all of those artifacts easily.

Followed by a request to implement:
> prompt with very clear instructions. Iterate until the plan is met and the features are rock solid for the following feature doc: planning-docs/2025-01-20-development-test-mode.md

## Error Handling Philosophy: Fail Fast

This codebase follows a **"fail fast"** philosophy for better debugging and development:

1. **NO try/except blocks** in most code - let errors bubble up with full stack traces
2. **Exceptions are for truly exceptional cases** - use them sparingly, if at all
3. **Full visibility into errors** - see exactly what went wrong and where
4. **Development mode exits on error** - fix issues immediately
5. **Production resilience through process managers** - systemd/supervisor handle restarts

### When try/except is acceptable:
- External API calls that might legitimately fail (network issues)
- Resource cleanup that must happen even on error
- Top-level error reporting (but still re-raise)

### What to do instead:
- Let errors propagate naturally
- Use proper validation before operations
- Check preconditions explicitly
- Use process managers for production resilience

This approach makes development MUCH easier by showing real errors immediately.