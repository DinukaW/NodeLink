# Chord-based File Sharing System

## Structure
- `peer/chord_peer.py`: Chord peer node for decentralized file sharing and lookup.
- `peer/shared/`: Directory for files to be shared by the peer.

## How to Run

### 1. Start the First Peer (Bootstrap Node)
```
python3 peer/chord_peer.py --ip 127.0.0.1 --port 6000 --shared_dir peer/shared
```

### 2. Start Additional Peers (Join the Ring)
```
python3 peer/chord_peer.py --ip 127.0.0.1 --port 6001 --shared_dir peer/shared --bootstrap_ip 127.0.0.1 --bootstrap_port 6000
```

You can run multiple peers on different ports and shared directories.

### 3. Peer Commands
- `search <filename>`: Search for a file in the Chord ring.
- `download <filename> <dest_dir>`: Download a file from the ring to a destination directory.
- `exit`: Exit the peer.

## Requirements
- Python 3.x

## Notes
- No central server: All peers form a Chord ring for decentralized lookup.
- Each peer is responsible for a range of file keys (hashes).
- Peers communicate using sockets and Chord protocol messages.
