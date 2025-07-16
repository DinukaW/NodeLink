import socket
import threading

class BootstrapServer:
    def __init__(self, host='0.0.0.0', port=55555, max_nodes=10):
        self.host = host
        self.port = port
        self.max_nodes = max_nodes
        self.nodes = []  # List of (ip, port)
        self.lock = threading.Lock()

    def start(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((self.host, self.port))
        s.listen(5)
        print(f"[Bootstrap] Listening on {self.host}:{self.port}")
        while True:
            conn, addr = s.accept()
            threading.Thread(target=self.handle_client, args=(conn, addr)).start()

    def handle_client(self, conn, addr):
        try:
            data = conn.recv(1024).decode()
            if not data:
                return
            toks = data.strip().split()
            if len(toks) < 2:
                conn.sendall(b' 9999 Invalid command')
                return
            cmd = toks[0]
            if cmd == 'REG':
                ip, port = toks[1], toks[2]
                with self.lock:
                    node = (ip, port)
                    if node not in self.nodes:
                        if len(self.nodes) < self.max_nodes:
                            self.nodes.append(node)
                            print(f"[Bootstrap] Node joined: {ip}:{port} (Total: {len(self.nodes)})")
                            # Send up to 2 other nodes
                            others = [n for n in self.nodes if n != node]
                            reply = f' REGOK {len(others)}'
                            for n in others[:2]:
                                reply += f' {n[0]} {n[1]}'
                            conn.sendall(reply.encode())
                        else:
                            conn.sendall(b' 9996 BSFull')
                    else:
                        print(f"[Bootstrap] Node already registered: {ip}:{port}")
                        conn.sendall(b' 9998 AlreadyRegistered')
            elif cmd == 'UNREG':
                ip, port = toks[1], toks[2]
                with self.lock:
                    node = (ip, port)
                    if node in self.nodes:
                        self.nodes.remove(node)
                        print(f"[Bootstrap] Node left: {ip}:{port} (Total: {len(self.nodes)})")
                        conn.sendall(b' UNROK 0')
                    else:
                        print(f"[Bootstrap] Node not found for removal: {ip}:{port}")
                        conn.sendall(b' UNROK 9999')
            else:
                conn.sendall(b' 9999 Invalid command')
        except Exception as e:
            print(f"[Bootstrap] Error: {e}")
        finally:
            conn.close()

if __name__ == '__main__':
    server = BootstrapServer()
    server.start()
