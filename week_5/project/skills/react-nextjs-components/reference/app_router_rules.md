# Next.js App Router: Golden Rules

## 1. Server Components (Default)
By default, all components are Server Components. 
- **DO:** Use `async/await` directly in the component to fetch data.
- **DO NOT:** Use hooks (`useState`, `useEffect`, `useContext`).
- **DO NOT:** Add event listeners (`onClick`, `onChange`).

## 2. Client Components
If you need interactivity or browser APIs, it MUST be a Client Component.
- **DO:** Add `"use client";` at the absolute top of the file.
- **DO NOT:** Fetch data using `useEffect` unless absolutely necessary (prefer passing data as props from a Server Component parent).

## 3. The Composition Rule
You can pass a Server Component as a `children` prop to a Client Component, but you CANNOT directly import a Server Component into a Client Component.