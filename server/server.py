import socket
import threading
import pickle

class FileServer:
    def __init__(self, host='0.0.0.0', port=5000):
        self.host = host
        self.port = port
        self.peers = {}  # {peer_addr: [file1, file2, ...]}
        self.lock = threading.Lock()

    def start(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((self.host, self.port))
        s.listen(5)
        print(f"[SERVER] Listening on {self.host}:{self.port}")
        while True:
            conn, addr = s.accept()
            threading.Thread(target=self.handle_client, args=(conn, addr)).start()

    def handle_client(self, conn, addr):
        try:
            data = conn.recv(4096)
            if not data:
                return
            request = pickle.loads(data)
            action = request.get('action')
            if action == 'register':
                files = request.get('files', [])
                with self.lock:
                    self.peers[addr[0]] = files
                conn.sendall(pickle.dumps({'status': 'registered'}))
                print(f"[SERVER] Registered {addr[0]} with files: {files}")
            elif action == 'search':
                filename = request.get('filename')
                with self.lock:
                    owners = [peer for peer, files in self.peers.items() if filename in files]
                conn.sendall(pickle.dumps({'owners': owners}))
                print(f"[SERVER] Search for '{filename}' by {addr[0]}: {owners}")
            else:
                conn.sendall(pickle.dumps({'error': 'Unknown action'}))
        except Exception as e:
            print(f"[SERVER] Error: {e}")
        finally:
            conn.close()

if __name__ == '__main__':
    server = FileServer()
    server.start()
