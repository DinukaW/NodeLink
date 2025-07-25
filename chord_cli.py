#!/usr/bin/env python3

import sys
import time
from chord import Node

def main():
    if len(sys.argv) < 3:
        print("Usage: python3 chord_cli.py <host> <port> [bootstrap_host] [bootstrap_port]")
        print("Examples:")
        print("  # Start node with default bootstrap server (localhost:5000):")
        print("  python3 chord_cli.py localhost 8001")
        print("  # Start node with custom bootstrap server:")
        print("  python3 chord_cli.py localhost 8002 localhost 5000")
        sys.exit(1)
    
    host = sys.argv[1]
    port = int(sys.argv[2])
    
    # Bootstrap server configuration
    bootstrap_host = "localhost"
    bootstrap_port = 5000
    
    if len(sys.argv) >= 4:
        bootstrap_host = sys.argv[3]
    if len(sys.argv) >= 5:
        bootstrap_port = int(sys.argv[4])
    
    # Create node
    print(f"Creating node at {host}:{port}")
    print(f"Bootstrap server: {bootstrap_host}:{bootstrap_port}")
    node = Node(host, port, bootstrap_host, bootstrap_port)
    
    # Join network through bootstrap server
    print("Joining network through bootstrap server...")
    success = node.join(None)  # No longer need joining address
    
    if not success:
        print("Failed to join network!")
        sys.exit(1)
    
    print(f"Node started successfully!")
    print(f"Node key: {node.key}")
    print("Available commands:")
    print("  put <filename>    - Store a file")
    print("  get <filename>    - Retrieve a file") 
    print("  status           - Show node status")
    print("  leave            - Leave network")
    print("  quit             - Exit")
    
    # Interactive command loop
    try:
        while True:
            command = input(f"\n[{host}:{port}]> ").strip().split()
            
            if not command:
                continue
                
            if command[0] == "put" and len(command) == 2:
                filename = command[1]
                try:
                    node.put(filename)
                    print(f"File '{filename}' stored successfully")
                except Exception as e:
                    print(f"Error storing file: {e}")
                    
            elif command[0] == "get" and len(command) == 2:
                filename = command[1]
                try:
                    result = node.get(filename)
                    if result:
                        print(f"File '{filename}' retrieved successfully")
                    else:
                        print(f"File '{filename}' not found")
                except Exception as e:
                    print(f"Error retrieving file: {e}")
                    
            elif command[0] == "status":
                print(f"Node Key: {node.key}")
                print(f"Successor: {node.successor}")
                print(f"Predecessor: {node.predecessor}")
                print(f"Files: {node.files}")
                print(f"Backup Files: {node.backUpFiles}")
                print(f"Bootstrap Server: {node.bootstrap_host}:{node.bootstrap_port}")
                print(f"Stop flag: {node.stop}")
                print(f"Leave flag: {node.leave_bool}")
                
            elif command[0] == "leave":
                print("Leaving network...")
                node.leave()
                print("Node left network successfully")
                break
                
            elif command[0] in ["quit", "exit"]:
                print("Shutting down node and transferring files...")
                node.quit_with_transfer()
                print("Node shutdown complete")
                break
                
            else:
                print("Unknown command. Available commands: put, get, status, leave, quit")
                
    except KeyboardInterrupt:
        print("\nShutting down node and transferring files...")
        node.quit_with_transfer()
    except Exception as e:
        print(f"Error: {e}")
        print("Shutting down node and transferring files...")
        node.quit_with_transfer()

if __name__ == "__main__":
    main()
