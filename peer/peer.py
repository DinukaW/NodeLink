import socket
import threading
import pickle
import os

class Peer:
    def __init__(self, server_host, server_port, shared_dir, peer_port=0):
        self.server_host = server_host
        self.server_port = server_port
        self.shared_dir = shared_dir
        self.peer_port = peer_port
        self.host = '0.0.0.0'

    def register_with_server(self):
        files = os.listdir(self.shared_dir)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((self.server_host, self.server_port))
        req = {'action': 'register', 'files': files}
        s.sendall(pickle.dumps(req))
        resp = pickle.loads(s.recv(4096))
        print(f"[PEER] Registration response: {resp}")
        s.close()

    def search_file(self, filename):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((self.server_host, self.server_port))
        req = {'action': 'search', 'filename': filename}
        s.sendall(pickle.dumps(req))
        resp = pickle.loads(s.recv(4096))
        print(f"[PEER] Owners of '{filename}': {resp.get('owners', [])}")
        s.close()
        return resp.get('owners', [])

    def serve_files(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((self.host, self.peer_port))
        s.listen(5)
        print(f"[PEER] Serving files from {self.shared_dir} on port {s.getsockname()[1]}")
        while True:
            conn, addr = s.accept()
            threading.Thread(target=self.handle_download, args=(conn, addr)).start()

    def handle_download(self, conn, addr):
        try:
            data = conn.recv(4096)
            filename = data.decode()
            filepath = os.path.join(self.shared_dir, filename)
            if os.path.exists(filepath):
                with open(filepath, 'rb') as f:
                    conn.sendfile(f)
                print(f"[PEER] Sent '{filename}' to {addr[0]}")
            else:
                conn.send(b'')
        except Exception as e:
            print(f"[PEER] Download error: {e}")
        finally:
            conn.close()

    def download_file(self, peer_ip, filename, dest_dir):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((peer_ip, self.peer_port))
        s.sendall(filename.encode())
        filepath = os.path.join(dest_dir, filename)
        with open(filepath, 'wb') as f:
            while True:
                data = s.recv(4096)
                if not data:
                    break
                f.write(data)
        print(f"[PEER] Downloaded '{filename}' from {peer_ip}")
        s.close()

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Peer Node')
    parser.add_argument('--server_host', type=str, default='127.0.0.1')
    parser.add_argument('--server_port', type=int, default=5000)
    parser.add_argument('--shared_dir', type=str, required=True)
    parser.add_argument('--peer_port', type=int, default=6000)
    args = parser.parse_args()

    peer = Peer(args.server_host, args.server_port, args.shared_dir, args.peer_port)
    threading.Thread(target=peer.serve_files, daemon=True).start()
    peer.register_with_server()
    while True:
        cmd = input('Enter command (search <filename> | download <peer_ip> <filename> <dest_dir> | exit): ')
        if cmd.startswith('search '):
            _, filename = cmd.split(maxsplit=1)
            peer.search_file(filename)
        elif cmd.startswith('download '):
            _, peer_ip, filename, dest_dir = cmd.split(maxsplit=3)
            peer.download_file(peer_ip, filename, dest_dir)
        elif cmd == 'exit':
            break
