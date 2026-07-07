#!/usr/bin/env python3
import argparse
import os

def create_files(module_name: str):
    # Ensure directories exist
    os.makedirs("tests", exist_ok=True)
    
    impl_file = f"{module_name}.py"
    test_file = f"tests/test_{module_name}.py"
    
    # 1. Scaffold the implementation file (Empty Stub)
    if not os.path.exists(impl_file):
        with open(impl_file, "w") as f:
            f.write(f'"""\nImplementation of {module_name}\n"""\n\n')
            f.write(f"def stub_{module_name}():\n")
            f.write(f"    \"\"\"TODO: Implement {module_name}\"\"\"\n")
            f.write(f"    return None\n\n")
        print(f"✅ Created stub: {impl_file}")
    else:
        print(f"⚠️ {impl_file} already exists.")

    # 2. Scaffold the Test file (Failing by default)
    if not os.path.exists(test_file):
        with open(test_file, "w") as f:
            f.write(f"import pytest\n")
            f.write(f"import {module_name}\n\n")
            f.write("@pytest.fixture\n")
            f.write("def sample_fixture():\n")
            f.write("    # Setup your test state here\n")
            f.write("    return True\n\n")
            f.write(f"def test_{module_name}_initial(sample_fixture):\n")
            f.write("    # TODO: Write your assertions here BEFORE implementing the logic\n")
            f.write('    assert False, "TDD Enforcement: Write the test first, watch it fail, then pass it."\n')
        print(f"✅ Created test: {test_file}")
    else:
        print(f"⚠️ {test_file} already exists.")
        
    print("\n🚀 TDD Scaffold complete! Next step: Run `pytest` to watch it fail.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scaffold files for TDD.")
    parser.add_argument("--module", required=True, help="The name of the module (e.g., calculator).")
    args = parser.parse_args()
    create_files(args.module)
