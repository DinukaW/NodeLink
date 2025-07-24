#!/usr/bin/env python3
"""
Simple test to verify the fixes work
"""

import os
import sys
import time

def create_test_files():
    """Create test files in the expected directories"""
    dirs = ["localhost_8001", "localhost_8002", "localhost_8003"]
    for dir_name in dirs:
        os.makedirs(dir_name, exist_ok=True)
        # Create test files
        test_file = f"{dir_name}/test{dir_name[-1]}.txt"
        with open(test_file, "w") as f:
            f.write(f"Test content from {dir_name}")
        print(f"Created {test_file}")

def main():
    print("=== Creating test files ===")
    create_test_files()
    print("\n=== Test files created successfully ===")
    print("\nNow you can:")
    print("1. Start bootstrap server: python3 bootstrap_server.py")
    print("2. Start nodes: python3 chord_cli.py localhost 8001")
    print("3. Test file operations: put test1.txt, get test1.txt")

if __name__ == "__main__":
    main()
