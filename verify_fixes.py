#!/usr/bin/env python3
"""
Quick verification that fixes are working
"""

import os
import sys

def check_files():
    """Check if test files exist"""
    expected_files = [
        "localhost_8001/test1.txt",
        "localhost_8002/test2.txt", 
        "localhost_8003/test3.txt"
    ]
    
    print("=== Checking test files ===")
    all_good = True
    for file_path in expected_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path} exists")
        else:
            print(f"❌ {file_path} missing")
            all_good = False
    
    return all_good

def check_bootstrap_port():
    """Check if bootstrap server code has correct port"""
    print("\n=== Checking bootstrap server configuration ===")
    
    try:
        with open("bootstrap_server.py", "r") as f:
            content = f.read()
            if "port=9000" in content:
                print("✅ Bootstrap server using port 9000")
                return True
            else:
                print("❌ Bootstrap server port configuration issue")
                return False
    except Exception as e:
        print(f"❌ Error checking bootstrap server: {e}")
        return False

def check_chord_port():
    """Check if chord.py has correct bootstrap port"""
    print("\n=== Checking chord node configuration ===")
    
    try:
        with open("chord.py", "r") as f:
            content = f.read()
            if "bootstrap_port=9000" in content:
                print("✅ Chord nodes using bootstrap port 9000")
                return True
            else:
                print("❌ Chord node bootstrap port configuration issue")
                return False
    except Exception as e:
        print(f"❌ Error checking chord configuration: {e}")
        return False

def main():
    print("=== Chord DHT System - Fix Verification ===\n")
    
    files_ok = check_files()
    bootstrap_ok = check_bootstrap_port() 
    chord_ok = check_chord_port()
    
    print("\n=== Summary ===")
    if files_ok and bootstrap_ok and chord_ok:
        print("✅ All checks passed! System is ready to test.")
        print("\nNext steps:")
        print("1. Terminal 1: python3 bootstrap_server.py")
        print("2. Terminal 2: python3 chord_cli.py localhost 8001") 
        print("3. Terminal 3: python3 chord_cli.py localhost 8002")
        print("4. Test: put test1.txt, get test1.txt, status, quit")
    else:
        print("❌ Some issues found. Please check the output above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
