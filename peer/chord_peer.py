import hashlib
import threading
import socket
import pickle
import os
import time

M = 8  # Number of bits for the Chord ring (0-255)
RING_SIZE = 2 ** M


def hash_key(key):
    return int(hashlib.sha1(key.encode()).hexdigest(), 16) % RING_SIZE


class ChordPeer:
    @staticmethod
    def register_with_bootstrap(ip, port, bs_ip, bs_port):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((bs_ip, bs_port))
        msg = f'REG {ip} {port}'
        s.sendall(msg.encode())
        data = s.recv(1024).decode()
        s.close()
        toks = data.strip().split()
        if len(toks) < 2 or toks[1] != 'REGOK':
            print(f"[ChordPeer] Bootstrap registration failed: {data}")
            return []
        n = int(toks[2])
        peers = []
        for i in range(n):
            peer_ip = toks[3 + 2 * i]
            peer_port = int(toks[4 + 2 * i])
            peers.append((peer_ip, peer_port))
        print(f"[ChordPeer] Registered with bootstrap server. Peers: {peers}")
        return peers

    def unregister_with_bootstrap(self, bs_ip, bs_port):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((bs_ip, bs_port))
            msg = f'UNREG {self.ip} {self.port}'
            s.sendall(msg.encode())
            data = s.recv(1024).decode()
            s.close()
            print(f"[ChordPeer] Unregistered from bootstrap server: {data.strip()}")
        except Exception as e:
            print(f"[ChordPeer] Error unregistering from bootstrap server: {e}")
    def transfer_all_keys_to_successor(self):
        if self.successor[2] == self.id or not self.dht_storage:
            return
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((self.successor[0], self.successor[1]))
            req = {'action': 'transfer_keys', 'files': list(self.dht_storage.keys())}
            s.sendall(pickle.dumps(req))
            ack = s.recv(1024)
            for fname, fdata in self.dht_storage.items():
                s.sendall(pickle.dumps({'filename': fname, 'filedata': fdata}))
                time.sleep(0.05)
            s.sendall(b'__END__')
            s.close()
            print(f"[ChordPeer] Transferred all keys/files to successor {self.successor[0]}:{self.successor[1]}")
        except Exception as e:
            print(f"[ChordPeer] Error transferring keys to successor on leave: {e}")
    def __init__(self, ip, port, shared_dir, bootstrap=None):
        self.ip = ip
        self.port = port
        self.id = hash_key(f"{ip}:{port}")
        self.shared_dir = shared_dir
        self.successor = (self.ip, self.port, self.id)
        self.predecessor = None
        self.finger = [(self.ip, self.port, self.id)] * M
        self.lock = threading.Lock()
        self.dht_storage = {}  # {filename: filedata}
        if bootstrap:
            self.join(bootstrap)
        else:
            self.predecessor = None
            self.successor = (self.ip, self.port, self.id)
        # Distribute files to responsible peers on startup
        self.distribute_files()
        # Start watcher for dynamic file addition
        threading.Thread(target=self.watch_shared_dir, daemon=True).start()

    def watch_shared_dir(self):
        known_files = set(os.listdir(self.shared_dir))
        while True:
            current_files = set(os.listdir(self.shared_dir))
            new_files = current_files - known_files
            for filename in new_files:
                print(f"[ChordPeer] Detected new file '{filename}' in shared_dir. Distributing...")
                self.distribute_single_file(filename)
            known_files = current_files
            time.sleep(2)

    def distribute_single_file(self, filename):
        file_id = hash_key(filename)
        responsible = self.find_successor(file_id)
        if responsible[2] == self.id:
            # Store locally in DHT storage
            with open(os.path.join(self.shared_dir, filename), 'rb') as f:
                self.dht_storage[filename] = f.read()
        else:
            # Send file to responsible peer
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect((responsible[0], responsible[1]))
                req = {'action': 'store_file', 'filename': filename}
                s.sendall(pickle.dumps(req))
                ack = s.recv(1024)  # Wait for ack to send file
                with open(os.path.join(self.shared_dir, filename), 'rb') as f:
                    while True:
                        chunk = f.read(4096)
                        if not chunk:
                            break
                        s.send(chunk)
                s.close()
            except Exception as e:
                print(f"[ChordPeer] Error sending file '{filename}' to {responsible}: {e}")

    def distribute_files(self):
        # For each file in shared_dir, send to responsible peer if not self
        for filename in os.listdir(self.shared_dir):
            file_id = hash_key(filename)
            responsible = self.find_successor(file_id)
            if responsible[2] == self.id:
                # Store locally in DHT storage
                with open(os.path.join(self.shared_dir, filename), 'rb') as f:
                    self.dht_storage[filename] = f.read()
            else:
                # Send file to responsible peer
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.connect((responsible[0], responsible[1]))
                    req = {'action': 'store_file', 'filename': filename}
                    s.sendall(pickle.dumps(req))
                    ack = s.recv(1024)  # Wait for ack to send file
                    with open(os.path.join(self.shared_dir, filename), 'rb') as f:
                        while True:
                            chunk = f.read(4096)
                            if not chunk:
                                break
                            s.send(chunk)
                    s.close()
                except Exception as e:
                    print(f"[ChordPeer] Error sending file '{filename}' to {responsible}: {e}")

    def join(self, bootstrap):
        # Contact bootstrap node to find successor
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(bootstrap)
        req = {'action': 'find_successor', 'id': self.id}
        s.sendall(pickle.dumps(req))
        resp = pickle.loads(s.recv(4096))
        self.successor = resp['successor']
        s.close()

    def find_successor(self, id_):
        if self.id == self.successor[2]:
            return (self.ip, self.port, self.id)
        if self.in_range(id_, self.id, self.successor[2], inclusive_right=True):
            return self.successor
        else:
            n0 = self.closest_preceding_node(id_)
            if n0[2] == self.id:
                return (self.ip, self.port, self.id)
            return self.remote_find_successor(n0, id_)

    def closest_preceding_node(self, id_):
        for i in reversed(range(M)):
            node = self.finger[i]
            if self.in_range(node[2], self.id, id_):
                return node
        return (self.ip, self.port, self.id)

    def remote_find_successor(self, node, id_):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((node[0], node[1]))
        req = {'action': 'find_successor', 'id': id_}
        s.sendall(pickle.dumps(req))
        resp = pickle.loads(s.recv(4096))
        s.close()
        return resp['successor']

    def in_range(self, x, a, b, inclusive_right=False):
        if a < b:
            return a < x < b or (inclusive_right and x == b)
        elif a > b:
            return x > a or x < b or (inclusive_right and x == b)
        else:
            return x != a or (inclusive_right and x == b)

    def stabilize(self):
        while True:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect((self.successor[0], self.successor[1]))
                req = {'action': 'get_predecessor'}
                s.sendall(pickle.dumps(req))
                resp = pickle.loads(s.recv(4096))
                x = resp.get('predecessor')
                if x and self.in_range(x[2], self.id, self.successor[2]):
                    self.successor = x
                # Notify successor
                req = {'action': 'notify', 'node': (self.ip, self.port, self.id)}
                s.sendall(pickle.dumps(req))
                s.close()
            except Exception:
                pass
            time.sleep(2)

    def notify(self, node):
        # If the new node is our new predecessor, transfer relevant keys/files
        if (self.predecessor is None or self.in_range(node[2], self.predecessor[2], self.id)):
            old_pred = self.predecessor
            self.predecessor = node
            # Transfer keys/files for which the new node is now responsible
            files_to_transfer = {}
            for filename, filedata in list(self.dht_storage.items()):
                file_id = hash_key(filename)
                # If file_id is in (old_pred, new_pred]
                if self.in_range(file_id, node[2], self.id, inclusive_right=True):
                    files_to_transfer[filename] = filedata
            if files_to_transfer:
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.connect((node[0], node[1]))
                    req = {'action': 'transfer_keys', 'files': list(files_to_transfer.keys())}
                    s.sendall(pickle.dumps(req))
                    ack = s.recv(1024)
                    for fname, fdata in files_to_transfer.items():
                        # Send filename and filedata
                        s.sendall(pickle.dumps({'filename': fname, 'filedata': fdata}))
                        time.sleep(0.05)  # Small delay to avoid packet merging
                    s.sendall(b'__END__')
                    s.close()
                    # Remove transferred files from local storage
                    for fname in files_to_transfer:
                        del self.dht_storage[fname]
                    print(f"[ChordPeer] Transferred {len(files_to_transfer)} keys/files to new predecessor {node[0]}:{node[1]}")
                except Exception as e:
                    print(f"[ChordPeer] Error transferring keys to new predecessor: {e}")

    def fix_fingers(self):
        while True:
            for i in range(M):
                start = (self.id + 2 ** i) % RING_SIZE
                self.finger[i] = self.find_successor(start)
            time.sleep(5)

    def serve(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((self.ip, self.port))
        s.listen(5)
        print(f"[ChordPeer] Listening on {self.ip}:{self.port} (id={self.id})")
        threading.Thread(target=self.stabilize, daemon=True).start()
        threading.Thread(target=self.fix_fingers, daemon=True).start()
        while True:
            conn, addr = s.accept()
            threading.Thread(target=self.handle_conn, args=(conn, addr)).start()

    def handle_conn(self, conn, addr):
        try:
            data = conn.recv(4096)
            req = pickle.loads(data)
            action = req.get('action')
            if action == 'find_successor':
                id_ = req['id']
                succ = self.find_successor(id_)
                conn.sendall(pickle.dumps({'successor': succ}))
            elif action == 'get_predecessor':
                conn.sendall(pickle.dumps({'predecessor': self.predecessor}))
            elif action == 'notify':
                node = req['node']
                self.notify(node)
                conn.sendall(pickle.dumps({'status': 'ok'}))
            elif action == 'transfer_keys':
                # Accept keys/files from predecessor
                conn.send(b'READY')
                while True:
                    chunk = conn.recv(4096)
                    if chunk == b'__END__':
                        break
                    try:
                        obj = pickle.loads(chunk)
                        fname = obj['filename']
                        fdata = obj['filedata']
                        self.dht_storage[fname] = fdata
                        print(f"[ChordPeer] Received transferred file '{fname}' from predecessor.")
                    except Exception as e:
                        print(f"[ChordPeer] Error receiving transferred file: {e}")
            elif action == 'store_file':
                filename = req['filename']
                conn.send(b'READY')  # Ack to send file
                filedata = b''
                while True:
                    chunk = conn.recv(4096)
                    if not chunk:
                        break
                    filedata += chunk
                self.dht_storage[filename] = filedata
                print(f"[ChordPeer] Stored file '{filename}' in DHT storage.")
            elif action == 'search_file':
                filename = req['filename']
                if filename in self.dht_storage:
                    conn.sendall(pickle.dumps({'has_file': True, 'ip': self.ip, 'port': self.port}))
                else:
                    conn.sendall(pickle.dumps({'has_file': False}))
            elif action == 'download_file':
                filename = req['filename']
                if filename in self.dht_storage:
                    filedata = self.dht_storage[filename]
                    conn.sendall(filedata)
                else:
                    conn.send(b'')
            else:
                conn.sendall(pickle.dumps({'error': 'Unknown action'}))
        except Exception as e:
            print(f"[ChordPeer] Error: {e}")
        finally:
            conn.close()

    def search_file(self, filename):
        file_id = hash_key(filename)
        node = self.find_successor(file_id)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((node[0], node[1]))
        req = {'action': 'search_file', 'filename': filename}
        s.sendall(pickle.dumps(req))
        resp = pickle.loads(s.recv(4096))
        s.close()
        if resp.get('has_file'):
            print(f"[ChordPeer] File '{filename}' found at {resp['ip']}:{resp['port']}")
            return resp['ip'], resp['port']
        else:
            print(f"[ChordPeer] File '{filename}' not found in the ring.")
            return None, None

    def download_file(self, ip, port, filename, dest_dir):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((ip, port))
        req = {'action': 'download_file', 'filename': filename}
        s.sendall(pickle.dumps(req))
        filepath = os.path.join(dest_dir, filename)
        with open(filepath, 'wb') as f:
            while True:
                data = s.recv(4096)
                if not data:
                    break
                f.write(data)
        print(f"[ChordPeer] Downloaded '{filename}' from {ip}:{port}")
        s.close()

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Chord Peer Node')
    parser.add_argument('--ip', type=str, default='127.0.0.1')
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--shared_dir', type=str, required=True)
    parser.add_argument('--bootstrap_ip', type=str)
    parser.add_argument('--bootstrap_port', type=int)
    args = parser.parse_args()

    # Register with bootstrap server and get peers
    bs_ip = '127.0.0.1'
    bs_port = 55555
    peers = []
    try:
        peers = ChordPeer.register_with_bootstrap(args.ip, args.port, bs_ip, bs_port)
    except Exception as e:
        print(f"[ChordPeer] Error registering with bootstrap server: {e}")

    # Use first peer from bootstrap as Chord bootstrap node, else start new ring
    if peers:
        bootstrap = peers[0]
    else:
        bootstrap = None

    peer = ChordPeer(args.ip, args.port, args.shared_dir, bootstrap)
    threading.Thread(target=peer.serve, daemon=True).start()
    time.sleep(1)
    while True:
        cmd = input('Enter command (search <filename> | download <filename> <dest_dir> | exit): ')
        if cmd.startswith('search '):
            _, filename = cmd.split(maxsplit=1)
            peer.search_file(filename)
        elif cmd.startswith('download '):
            _, filename, dest_dir = cmd.split(maxsplit=2)
            ip, port = peer.search_file(filename)
            if ip and port:
                peer.download_file(ip, port, filename, dest_dir)
        elif cmd == 'exit':
            print("[ChordPeer] Transferring all keys/files to successor before exit...")
            peer.transfer_all_keys_to_successor()
            peer.unregister_with_bootstrap(bs_ip, bs_port)
            print("[ChordPeer] Graceful exit complete.")
            break
