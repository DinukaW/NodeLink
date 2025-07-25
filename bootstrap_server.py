#!/usr/bin/env python3

import socket
import threading
import time
import hashlib
import json
from datetime import datetime

class BootstrapServer:
    def __init__(self, host="localhost", port=5000):
        self.host = host
        self.port = port
        self.stop = False
        self.M = 16
        self.N = 2**self.M
        
        # Track all nodes in the network
        self.nodes = {}  # {(host, port): {"key": key, "successor": tuple, "predecessor": tuple, "last_heartbeat": timestamp}}
        self.nodes_lock = threading.Lock()
        
        # Start the server
        self.server_socket = None
        self.start_server()
        
        # Start heartbeat monitoring
        threading.Thread(target=self.monitor_heartbeats, daemon=True).start()
        
        print(f"Bootstrap server started on {host}:{port}")
        
    def hasher(self, key):
        """Hash function consistent with Node class"""
        return int(hashlib.md5(key.encode()).hexdigest(), 16) % self.N
    
    def start_server(self):
        """Start the bootstrap server"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(10)
        
        # Start accepting connections in a separate thread
        threading.Thread(target=self.accept_connections, daemon=True).start()
    
    def accept_connections(self):
        """Accept incoming connections"""
        while not self.stop:
            try:
                client_socket, addr = self.server_socket.accept()
                threading.Thread(target=self.handle_connection, args=(client_socket, addr), daemon=True).start()
            except Exception as e:
                if not self.stop:
                    print(f"Error accepting connection: {e}")
                break
    
    def handle_connection(self, client_socket, addr):
        """Handle incoming connections from nodes"""
        try:
            message = client_socket.recv(1024).decode('utf-8')
            message_parts = message.split()
            
            if not message_parts:
                client_socket.close()
                return
                
            command = message_parts[0]
            
            if command == "register":
                self.handle_register(client_socket, message_parts)
            elif command == "lookup":
                self.handle_lookup(client_socket, message_parts)
            elif command == "heartbeat":
                self.handle_heartbeat(client_socket, message_parts)
            elif command == "leave":
                self.handle_leave(client_socket, message_parts)
            elif command == "get_nodes":
                self.handle_get_nodes(client_socket, message_parts)
            else:
                print(f"Unknown command: {command}")
                client_socket.close()
                
        except Exception as e:
            print(f"Error handling connection from {addr}: {e}")
            client_socket.close()
    
    def handle_register(self, client_socket, message_parts):
        """Handle node registration"""
        try:
            # Format: register <host> <port>
            if len(message_parts) < 3:
                client_socket.send("error invalid_format".encode('utf-8'))
                client_socket.close()
                return
                
            node_host = message_parts[1]
            node_port = int(message_parts[2])
            node_addr = (node_host, node_port)
            node_key = self.hasher(node_host + str(node_port))
            
            with self.nodes_lock:
                if len(self.nodes) == 0:
                    # First node - becomes its own successor and predecessor
                    self.nodes[node_addr] = {
                        "key": node_key,
                        "successor": node_addr,
                        "predecessor": node_addr,
                        "last_heartbeat": time.time()
                    }
                    client_socket.send(f"first_node {node_host} {node_port}".encode('utf-8'))
                else:
                    # Find appropriate position in the ring
                    successor_addr = self.find_successor(node_key)
                    predecessor_addr = self.nodes[successor_addr]["predecessor"]
                    
                    # Update the ring
                    self.nodes[node_addr] = {
                        "key": node_key,
                        "successor": successor_addr,
                        "predecessor": predecessor_addr,
                        "last_heartbeat": time.time()
                    }
                    
                    # Update successor's predecessor
                    self.nodes[successor_addr]["predecessor"] = node_addr
                    
                    # Update predecessor's successor  
                    self.nodes[predecessor_addr]["successor"] = node_addr
                    
                    client_socket.send(f"join_position {successor_addr[0]} {successor_addr[1]} {predecessor_addr[0]} {predecessor_addr[1]}".encode('utf-8'))
                    
            print(f"Node {node_addr} registered with key {node_key}")
            
        except Exception as e:
            print(f"Error in handle_register: {e}")
            client_socket.send("error registration_failed".encode('utf-8'))
        finally:
            client_socket.close()
    
    def handle_lookup(self, client_socket, message_parts):
        """Handle lookup requests"""
        try:
            # Format: lookup <key>
            if len(message_parts) < 2:
                client_socket.send("error invalid_format".encode('utf-8'))
                client_socket.close()
                return
                
            target_key = int(message_parts[1])
            
            with self.nodes_lock:
                if len(self.nodes) == 0:
                    client_socket.send("error no_nodes".encode('utf-8'))
                else:
                    successor_addr = self.find_successor(target_key)
                    client_socket.send(f"found {successor_addr[0]} {successor_addr[1]}".encode('utf-8'))
                    
        except Exception as e:
            print(f"Error in handle_lookup: {e}")
            client_socket.send("error lookup_failed".encode('utf-8'))
        finally:
            client_socket.close()
    
    def handle_heartbeat(self, client_socket, message_parts):
        """Handle heartbeat from nodes"""
        try:
            # Format: heartbeat <host> <port>
            if len(message_parts) < 3:
                client_socket.send("error invalid_format".encode('utf-8'))
                client_socket.close()
                return
                
            node_host = message_parts[1]
            node_port = int(message_parts[2])
            node_addr = (node_host, node_port)
            
            with self.nodes_lock:
                if node_addr in self.nodes:
                    self.nodes[node_addr]["last_heartbeat"] = time.time()
                    client_socket.send("ack".encode('utf-8'))
                else:
                    client_socket.send("error not_registered".encode('utf-8'))
                    
        except Exception as e:
            print(f"Error in handle_heartbeat: {e}")
            client_socket.send("error heartbeat_failed".encode('utf-8'))
        finally:
            client_socket.close()
    
    def handle_leave(self, client_socket, message_parts):
        """Handle node leaving"""
        try:
            # Format: leave <host> <port>
            if len(message_parts) < 3:
                client_socket.send("error invalid_format".encode('utf-8'))
                client_socket.close()
                return
                
            node_host = message_parts[1]
            node_port = int(message_parts[2])
            node_addr = (node_host, node_port)
            
            with self.nodes_lock:
                if node_addr in self.nodes:
                    self.remove_node(node_addr)
                    client_socket.send("ack".encode('utf-8'))
                    print(f"Node {node_addr} left the network")
                else:
                    client_socket.send("error not_registered".encode('utf-8'))
                    
        except Exception as e:
            print(f"Error in handle_leave: {e}")
            client_socket.send("error leave_failed".encode('utf-8'))
        finally:
            client_socket.close()
    
    def handle_get_nodes(self, client_socket, message_parts):
        """Return list of all active nodes"""
        try:
            with self.nodes_lock:
                nodes_info = []
                for addr, info in self.nodes.items():
                    nodes_info.append(f"{addr[0]}:{addr[1]}:{info['key']}")
                
                response = "nodes " + ",".join(nodes_info)
                client_socket.send(response.encode('utf-8'))
                
        except Exception as e:
            print(f"Error in handle_get_nodes: {e}")
            client_socket.send("error get_nodes_failed".encode('utf-8'))
        finally:
            client_socket.close()
    
    def find_successor(self, key):
        """Find the successor node for a given key"""
        if not self.nodes:
            return None
            
        # Sort nodes by key
        sorted_nodes = sorted(self.nodes.items(), key=lambda x: x[1]["key"])
        
        # Find the first node with key >= target key
        for addr, info in sorted_nodes:
            if info["key"] >= key:
                return addr
                
        # If no node found, return the first node (wrap around)
        return sorted_nodes[0][0]
    
    def remove_node(self, node_addr):
        """Remove a node from the ring and update connections"""
        if node_addr not in self.nodes:
            return
            
        node_info = self.nodes[node_addr]
        successor_addr = node_info["successor"]
        predecessor_addr = node_info["predecessor"]
        
        # If this is the only node
        if successor_addr == node_addr:
            del self.nodes[node_addr]
            return
            
        # Update successor's predecessor
        if successor_addr in self.nodes:
            self.nodes[successor_addr]["predecessor"] = predecessor_addr
            
        # Update predecessor's successor
        if predecessor_addr in self.nodes:
            self.nodes[predecessor_addr]["successor"] = successor_addr
            
        # Remove the node
        del self.nodes[node_addr]
        
        # Notify affected nodes about the topology change
        self.notify_topology_change(successor_addr, predecessor_addr)
    
    def notify_topology_change(self, successor_addr, predecessor_addr):
        """Notify nodes about topology changes when a node leaves"""
        try:
            # Notify successor about new predecessor
            if successor_addr in self.nodes:
                threading.Thread(target=self.send_topology_update, 
                               args=(successor_addr, "update_predecessor", predecessor_addr), 
                               daemon=True).start()
            
            # Notify predecessor about new successor  
            if predecessor_addr in self.nodes:
                threading.Thread(target=self.send_topology_update,
                               args=(predecessor_addr, "update_successor", successor_addr),
                               daemon=True).start()
        except Exception as e:
            print(f"Error notifying topology change: {e}")
    
    def send_topology_update(self, target_addr, update_type, new_addr):
        """Send topology update to a specific node"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            sock.connect(target_addr)
            
            if update_type == "update_predecessor":
                message = f"topology_update_pred {new_addr[0]} {new_addr[1]}"
            elif update_type == "update_successor":
                message = f"topology_update_succ {new_addr[0]} {new_addr[1]}"
            else:
                return
                
            sock.send(message.encode('utf-8'))
            sock.close()
            print(f"Sent topology update to {target_addr}: {update_type} -> {new_addr}")
            
        except Exception as e:
            print(f"Failed to send topology update to {target_addr}: {e}")
    
    def monitor_heartbeats(self):
        """Monitor node heartbeats and remove failed nodes"""
        HEARTBEAT_TIMEOUT = 10  # seconds
        
        while not self.stop:
            time.sleep(5)  # Check every 5 seconds
            
            current_time = time.time()
            failed_nodes = []
            
            with self.nodes_lock:
                for addr, info in self.nodes.items():
                    if current_time - info["last_heartbeat"] > HEARTBEAT_TIMEOUT:
                        failed_nodes.append(addr)
                        
                # Remove failed nodes
                for addr in failed_nodes:
                    print(f"Node {addr} failed - removing from network")
                    self.remove_node(addr)
    
    def get_network_status(self):
        """Get current network status"""
        with self.nodes_lock:
            return {
                "total_nodes": len(self.nodes),
                "nodes": dict(self.nodes)
            }
    
    def stop_server(self):
        """Stop the bootstrap server"""
        self.stop = True
        if self.server_socket:
            self.server_socket.close()
        print("Bootstrap server stopped")

def main():
    import sys
    
    host = "localhost"
    port = 5000
    
    if len(sys.argv) >= 2:
        port = int(sys.argv[1])
    if len(sys.argv) >= 3:
        host = sys.argv[2]
    
    server = BootstrapServer(host, port)
    
    try:
        print(f"Bootstrap server running on {host}:{port}")
        print("Commands: status, stop")
        
        while True:
            command = input("> ").strip().lower()
            
            if command == "status":
                status = server.get_network_status()
                print(f"Network Status:")
                print(f"  Total nodes: {status['total_nodes']}")
                for addr, info in status['nodes'].items():
                    print(f"  {addr}: key={info['key']}, succ={info['successor']}, pred={info['predecessor']}")
                    
            elif command == "stop":
                break
            elif command == "help":
                print("Available commands:")
                print("  status - Show network status")
                print("  stop   - Stop the server")
                print("  help   - Show this help")
            elif command:
                print("Unknown command. Type 'help' for available commands.")
                
    except KeyboardInterrupt:
        pass
    finally:
        server.stop_server()

if __name__ == "__main__":
    main()
