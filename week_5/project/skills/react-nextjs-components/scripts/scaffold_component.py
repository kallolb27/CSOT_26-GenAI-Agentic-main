#!/usr/bin/env python3
import argparse
import os

def create_component(name: str, comp_type: str, path: str):
    os.makedirs(path, exist_ok=True)
    file_path = os.path.join(path, f"{name}.tsx")
    
    if os.path.exists(file_path):
        print(f"⚠️ {file_path} already exists. Please use edit_file to modify it.")
        return

    with open(file_path, "w") as f:
        if comp_type == "client":
            f.write('"use client";\n\n')
            f.write("import { useState } from 'react';\n\n")
        
        f.write(f"export default function {name}() {{\n")
        
        if comp_type == "server":
            f.write("  // TODO: Fetch data directly here (Server Component)\n")
        else:
            f.write("  // TODO: Implement interactive state here (Client Component)\n")
            
        f.write("  return (\n")
        f.write(f"    <div>\n      <h1>{name} Component</h1>\n    </div>\n")
        f.write("  );\n")
        f.write("}\n")
        
    print(f"✅ Successfully scaffolded {comp_type} component at: {file_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scaffolds a Next.js App Router Component.")
    parser.add_argument("--name", required=True, help="Component name (PascalCase).")
    parser.add_argument("--type", required=True, choices=["server", "client"], help="Server or Client component.")
    parser.add_argument("--path", default="components", help="Directory to save the component.")
    args = parser.parse_args()
    
    create_component(args.name, args.type, args.path)