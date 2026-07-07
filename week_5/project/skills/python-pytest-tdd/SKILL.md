---
name: python-pytest-tdd
description: Strict Test-Driven Development (TDD) workflow and scaffolding tools for Python projects.
tags: python, testing, tdd, pytest
---

# Pytest TDD Workflow

When tasked with creating new Python features, you are strictly forbidden from writing implementation logic first. You MUST follow this precise TDD cycle:

## Execution Protocol

1. **Scaffold:** Use your `run_command` tool to run the bundled scaffold script for the module you are building:
   `python skills/python-pytest-tdd/scripts/scaffold_tdd.py --module <module_name>`
2. **Write the Test:** Use `edit_file` to write the actual test assertions inside the newly created `tests/test_<module_name>.py` file.
3. **Fail:** Use `run_command` to execute `pytest tests/test_<module_name>.py`. You MUST verify that the test fails.
4. **Implement:** Only after seeing a failure may you use `edit_file` to write the implementation logic in `<module_name>.py`.
5. **Pass:** Run `pytest` again until the test passes.

## Pytest Patterns & Mocking
If you need to mock external API calls, environment variables, or write complex teardown logic, **do not guess**. Use your `read_file` tool to read `skills/python-pytest-tdd/reference/pytest_patterns.md` for the correct Pytest native implementations.