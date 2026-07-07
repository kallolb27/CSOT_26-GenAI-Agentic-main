---
name: react-nextjs-components
description: Modern React component standards strictly for the Next.js App Router architecture.
tags: react, nextjs, frontend, typescript
---

# Next.js App Router Component Standards

When asked to create a React component for this Next.js project, you MUST use the following workflow.

## Execution Protocol

1. **Decide the Architecture:** Determine if the component needs state/interactivity (Client) or just displays data (Server).
2. **Scaffold:** Use your `run_command` tool to execute the bundled scaffold script:
   `python skills/react-nextjs-components/scripts/scaffold_component.py --name <ComponentName> --type <server|client> --path <directory/path>`
3. **Implement:** Use `edit_file` to build out the logic inside the newly generated `.tsx` file.

## Rule Enforcement
You are strictly forbidden from using outdated React patterns (like fetching data inside a `useEffect`). If you are unsure of the rules regarding Server vs. Client components, use your `read_file` tool to review `skills/react-nextjs-components/reference/app_router_rules.md`.