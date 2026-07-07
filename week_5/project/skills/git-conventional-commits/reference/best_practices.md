# Conventional Commits: Best Practices

1. **Imperative Mood:** Always use the imperative, present tense in your message (e.g., "add feature" not "added feature" or "adds feature").
2. **Capitalization:** The commit message description should remain entirely lowercase.
3. **Staging:** You MUST stage files using `git add` before attempting to commit. Never use `git commit -a` as it may include unintended files.
4. **Scoping:** Use scopes sparingly. They should only be used when a project has clearly defined modules (e.g., `feat(api): ...` or `fix(database): ...`).