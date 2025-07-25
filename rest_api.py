#!/usr/bin/env python3
"""
REST API Server for Chord DHT System
Provides HTTP endpoints for file operations and node management
"""

import os
import sys
import json
import logging
import hashlib
import threading
import time
import socket
from datetime import datetime
from flask import Flask, request, jsonify, send_file, abort
from werkzeug.utils import secure_filename
from werkzeug.exceptions import BadRequest

# Import Chord components
from chord import Node as ChordNode
from bootstrap_server import BootstrapServer

class ChordRESTAPI:
    def __init__(self, node_host='localhost', node_port=8000, api_port=5001, bootstrap_host='localhost', bootstrap_port=5000):
        self.node_host = node_host
        self.node_port = node_port
        self.api_port = api_port
        self.bootstrap_host = bootstrap_host
        self.bootstrap_port = bootstrap_port
        
        # Setup logging
        self.setup_logging()
        
        # Initialize Flask app
        self.app = Flask(__name__)
        self.app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size
        
        # Initialize Chord node
        self.chord_node = None
        self.node_thread = None
        
        # Shutdown mechanism
        self.shutdown_requested = False
        
        # Setup routes
        self.setup_routes()
        
        # Create uploads directory
        self.uploads_dir = "api_uploads"
        os.makedirs(self.uploads_dir, exist_ok=True)
        
        self.logger.info(f"REST API initialized - Node: {node_host}:{node_port}, API: {api_port}")
    
    def setup_logging(self):
        """Setup logging for REST API"""
        logs_dir = "logs"
        os.makedirs(logs_dir, exist_ok=True)
        
        # Create logger
        self.logger = logging.getLogger(f'rest_api_{self.node_host}_{self.api_port}')
        self.logger.setLevel(logging.DEBUG)
        
        # Create file handler
        log_file = os.path.join(logs_dir, f'rest_api_{self.node_host}_{self.api_port}.log')
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        
        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Add handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def start_chord_node(self):
        """Start the Chord node in a separate thread"""
        try:
            self.chord_node = ChordNode(self.node_host, self.node_port, self.bootstrap_host, self.bootstrap_port)
            success = self.chord_node.join(None)  # Join network through bootstrap server
            
            if not success:
                self.logger.error("Failed to join network through bootstrap server")
                return False
                
            self.logger.info(f"Chord node started successfully: {self.node_host}:{self.node_port}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to start Chord node: {e}")
            return False
    
    def setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/health', methods=['GET'])
        def health_check():
            """Health check endpoint"""
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'node': f"{self.node_host}:{self.node_port}",
                'api_port': self.api_port
            })
        
        @self.app.route('/upload', methods=['POST'])
        def upload_file():
            """Upload a file to the Chord network"""
            try:
                if not self.chord_node:
                    return jsonify({'error': 'Chord node not initialized'}), 503
                
                if 'file' not in request.files:
                    return jsonify({'error': 'No file provided'}), 400
                
                file = request.files['file']
                if file.filename == '':
                    return jsonify({'error': 'No file selected'}), 400
                
                # Secure the filename
                filename = secure_filename(file.filename)
                if not filename:
                    return jsonify({'error': 'Invalid filename'}), 400
                
                # Save file to uploads directory
                file_path = os.path.join(self.uploads_dir, filename)
                file.save(file_path)
                
                # Move the file to the node directory (same as manual file discovery)
                node_dir = f"{self.node_host}_{self.node_port}"
                if not os.path.exists(node_dir):
                    os.makedirs(node_dir)
                
                node_file_path = os.path.join(node_dir, filename)
                
                # If file already exists in node directory, create a backup
                if os.path.exists(node_file_path):
                    import shutil
                    backup_name = f"{filename}.backup.{int(time.time())}"
                    backup_path = os.path.join(node_dir, backup_name)
                    shutil.move(node_file_path, backup_path)
                    self.logger.info(f"Backed up existing file to {backup_name}")
                
                # Move uploaded file to node directory for automatic discovery
                import shutil
                shutil.move(file_path, node_file_path)
                
                # The file will be automatically discovered by the node's file discovery process
                # Wait a moment for discovery to happen
                time.sleep(1)
                
                # Get file info
                file_size = os.path.getsize(node_file_path)
                file_hash = self.chord_node.hasher(filename)
                
                self.logger.info(f"File uploaded successfully: {filename} ({file_size} bytes)")
                
                return jsonify({
                    'message': 'File uploaded successfully',
                    'filename': filename,
                    'size': file_size,
                    'hash': file_hash,
                    'responsible_node': f"{self.node_host}:{self.node_port}"
                }), 201
                
            except Exception as e:
                self.logger.error(f"Upload error: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/search', methods=['GET'])
        def search_files():
            """Search for files in the Chord network"""
            try:
                if not self.chord_node:
                    return jsonify({'error': 'Chord node not initialized'}), 503
                
                query = request.args.get('q', '').strip()
                if not query:
                    return jsonify({'error': 'Search query is required'}), 400
                
                # Perform distributed search using the search method
                results = self.chord_node.search(query)
                
                self.logger.info(f"Search performed: '{query}' - {len(results)} results")
                
                return jsonify({
                    'query': query,
                    'results': results,
                    'count': len(results),
                    'timestamp': datetime.now().isoformat()
                })
                
            except Exception as e:
                self.logger.error(f"Search error: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/download/<filename>', methods=['GET'])
        def download_file(filename):
            """Download a file from the Chord network"""
            try:
                if not self.chord_node:
                    return jsonify({'error': 'Chord node not initialized'}), 503
                
                # Secure the filename
                filename = secure_filename(filename)
                if not filename:
                    return jsonify({'error': 'Invalid filename'}), 400
                
                # Try to find file in node directory first
                node_dir = f"{self.node_host}_{self.node_port}"
                file_path = os.path.join(node_dir, filename)
                if os.path.exists(file_path):
                    self.logger.info(f"File downloaded: {filename}")
                    return send_file(file_path, as_attachment=True)
                
                # Try to find file in uploads directory
                file_path = os.path.join(self.uploads_dir, filename)
                if os.path.exists(file_path):
                    self.logger.info(f"File downloaded from uploads: {filename}")
                    return send_file(file_path, as_attachment=True)
                
                # Try to get file using the Chord protocol
                try:
                    result = self.chord_node.get(filename)
                    if result:
                        # If get was successful, the file should now be in the node directory
                        if os.path.exists(os.path.join(node_dir, filename)):
                            self.logger.info(f"File retrieved via Chord and downloaded: {filename}")
                            return send_file(os.path.join(node_dir, filename), as_attachment=True)
                except Exception as e:
                    self.logger.warning(f"Chord get failed for {filename}: {e}")
                
                self.logger.warning(f"File not found: {filename}")
                return jsonify({'error': 'File not found'}), 404
                
            except Exception as e:
                self.logger.error(f"Download error: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/node/status', methods=['GET'])
        def get_node_status():
            """Get current node status"""
            try:
                if not self.chord_node:
                    return jsonify({'error': 'Chord node not initialized'}), 503
                
                status = {
                    'node_id': f"{self.node_host}:{self.node_port}",
                    'key': self.chord_node.key,
                    'successor': list(self.chord_node.successor),
                    'predecessor': list(self.chord_node.predecessor),
                    'files_count': len(self.chord_node.files),
                    'index_entries': len(self.chord_node.file_index),
                    'backup_files_count': len(self.chord_node.backUpFiles),
                    'status': 'active',
                    'timestamp': datetime.now().isoformat()
                }
                
                return jsonify(status)
                
            except Exception as e:
                self.logger.error(f"Status error: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/node/leave', methods=['POST'])
        def leave_network():
            """Make the node leave the network gracefully and shutdown the API server"""
            try:
                if not self.chord_node:
                    return jsonify({'error': 'Chord node not initialized'}), 503
                
                # Perform graceful leave
                self.chord_node.leave()
                
                self.logger.info("Node left the network gracefully")
                
                # Schedule server shutdown
                def shutdown_server():
                    time.sleep(2)  # Give time for response to be sent
                    self.logger.info("Shutting down REST API server...")
                    self.shutdown_requested = True
                    # Force shutdown by sending SIGTERM to self
                    import signal
                    os.kill(os.getpid(), signal.SIGTERM)
                
                # Start shutdown in background thread
                shutdown_thread = threading.Thread(target=shutdown_server)
                shutdown_thread.daemon = True
                shutdown_thread.start()
                
                return jsonify({
                    'message': 'Node left the network successfully. Server shutting down...',
                    'timestamp': datetime.now().isoformat()
                })
                
            except Exception as e:
                self.logger.error(f"Leave network error: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/bootstrap/status', methods=['GET'])
        def get_bootstrap_status():
            """Get bootstrap server status"""
            try:
                import socket
                import json
                
                # Connect to bootstrap server
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                sock.connect((self.bootstrap_host, self.bootstrap_port))
                
                # Request status (we'll need to modify bootstrap server to support this)
                request = json.dumps({'action': 'status'}) + '\n'
                sock.send(request.encode())
                
                response = sock.recv(1024).decode().strip()
                sock.close()
                
                if response:
                    status_data = json.loads(response)
                    return jsonify(status_data)
                else:
                    return jsonify({
                        'status': 'active',
                        'message': 'Bootstrap server is running',
                        'timestamp': datetime.now().isoformat()
                    })
                
            except Exception as e:
                self.logger.error(f"Bootstrap status error: {e}")
                return jsonify({
                    'error': 'Cannot connect to bootstrap server',
                    'details': str(e)
                }), 503
        
        @self.app.route('/files/list', methods=['GET'])
        def list_files():
            """List all files known to this node"""
            try:
                if not self.chord_node:
                    return jsonify({'error': 'Chord node not initialized'}), 503
                
                files = []
                
                # List files from the node's files list
                for filename in self.chord_node.files:
                    node_dir = f"{self.node_host}_{self.node_port}"
                    file_path = os.path.join(node_dir, filename)
                    
                    file_info = {
                        'filename': filename,
                        'path': file_path,
                        'size': os.path.getsize(file_path) if os.path.exists(file_path) else 0,
                        'hash': self.chord_node.hasher(filename)
                    }
                    files.append(file_info)
                
                return jsonify({
                    'files': files,
                    'count': len(files),
                    'timestamp': datetime.now().isoformat()
                })
                
            except Exception as e:
                self.logger.error(f"List files error: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.errorhandler(413)
        def too_large(e):
            return jsonify({'error': 'File too large. Maximum size is 100MB'}), 413
        
        @self.app.errorhandler(400)
        def bad_request(e):
            return jsonify({'error': 'Bad request'}), 400
        
        @self.app.errorhandler(500)
        def internal_error(e):
            return jsonify({'error': 'Internal server error'}), 500
    
    def run(self):
        """Start the REST API server"""
        try:
            # Start Chord node
            if not self.start_chord_node():
                self.logger.error("Failed to start Chord node. API server will not start.")
                return
            
            self.logger.info(f"Starting REST API server on port {self.api_port}")
            self.app.run(host='0.0.0.0', port=self.api_port, debug=False, threaded=True)
            
        except KeyboardInterrupt:
            self.logger.info("API server shutting down...")
        except Exception as e:
            self.logger.error(f"API server error: {e}")

def check_port_availability(port, host='localhost'):
    """Check if a port is available"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((host, port))
        sock.close()
        return result != 0  # Port is available if connection failed
    except:
        return True

def main():
    if len(sys.argv) < 2:
        print("Chord DHT REST API Server")
        print("=" * 30)
        print("Usage:")
        print("  python3 rest_api.py <api_port> [node_port] [bootstrap_host] [bootstrap_port]")
        print()
        print("Examples:")
        print("  python3 rest_api.py 5001                    # API on 5001, node on 8000")
        print("  python3 rest_api.py 5001 8001               # API on 5001, node on 8001")
        print("  python3 rest_api.py 5001 8001 localhost 5000 # Full configuration")
        print()
        print("⚠️  IMPORTANT: Do not use port 5000 for API - it's reserved for bootstrap server!")
        print()
        print("Endpoints:")
        print("  POST /upload                 # Upload file")
        print("  GET  /search?q=<query>       # Search files")
        print("  GET  /download/<filename>    # Download file")
        print("  GET  /node/status            # Node status")
        print("  POST /node/leave             # Leave network (shuts down server)")
        print("  GET  /bootstrap/status       # Bootstrap status")
        print("  GET  /files/list             # List files")
        print("  GET  /health                 # Health check")
        return
    
    api_port = int(sys.argv[1])
    node_port = int(sys.argv[2]) if len(sys.argv) > 2 else 8000
    bootstrap_host = sys.argv[3] if len(sys.argv) > 3 else 'localhost'
    bootstrap_port = int(sys.argv[4]) if len(sys.argv) > 4 else 5000
    
    # Check for port conflicts
    if api_port == 5000:
        print("❌ ERROR: Port 5000 is reserved for the bootstrap server!")
        print("   Please use a different port (e.g., 5001, 5002, 5003)")
        print("   Usage: python3 rest_api.py 5001 8001")
        return
    
    if not check_port_availability(api_port):
        print(f"❌ ERROR: Port {api_port} is already in use!")
        print("   Please choose a different API port.")
        return
    
    if not check_port_availability(node_port):
        print(f"❌ ERROR: Port {node_port} is already in use!")
        print("   Please choose a different node port.")
        return
    
    # Start API server
    api = ChordRESTAPI(
        node_host='localhost',
        node_port=node_port,
        api_port=api_port,
        bootstrap_host=bootstrap_host,
        bootstrap_port=bootstrap_port
    )
    
    api.run()

if __name__ == "__main__":
    main()
