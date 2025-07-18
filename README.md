
# Chord-based Distributed File Sharing System

## Overview
This project implements a decentralized file sharing system using the Chord DHT protocol in Python. Peers form a Chord ring, distribute files, and support dynamic membership. A bootstrap server is used for peer discovery and logs node join/leave events.

## Structure
- `bootstrap_server.py`: Bootstrap server for peer discovery and logging.
- `peer/chord_peer.py`: Chord peer node for decentralized file sharing and lookup.
- `peer/shared/`, `peer/shared2/`, `peer/shared3/`: Example directories for files to be shared by peers.

## How to Run

### 1. Start the Bootstrap Server
```
python3 bootstrap_server.py
```

### 2. Start the First Peer (Creates New Chord Ring)
```
python3 peer/chord_peer.py --ip 127.0.0.1 --port 6000 --shared_dir peer/shared
```

### 3. Start Additional Peers (Join Existing Ring)
```
python3 peer/chord_peer.py --ip 127.0.0.1 --port 6001 --shared_dir peer/shared2
python3 peer/chord_peer.py --ip 127.0.0.1 --port 6002 --shared_dir peer/shared3
```

You can run multiple peers on different ports and shared directories. All peers will register with the bootstrap server (default: 127.0.0.1:55555).


### 4. Peer CLI Commands
- `search <query>`: Search for files in the Chord ring by full filename or any keyword/substring. Example: `search distributed computing` will find files containing either word.
- `download <filename> <dest_dir>`: Download a file from the ring to a destination directory.
- `exit`: Gracefully leave the ring (transfers files to successor and unregisters from bootstrap server).


## Features
- Decentralized file sharing using Chord DHT (no central server for file storage).
- Bootstrap server for peer discovery and logging node join/leave events.
- Dynamic file addition: new files in `shared_dir` are automatically distributed to the responsible peer.
- Graceful peer exit: files are transferred to the successor to maintain data consistency.
- Search for files by full filename or any keyword/substring (partial search supported).
- Download files from any peer in the ring.
- No external dependencies (Python 3.x standard library only).

## Requirements
- Python 3.x


## Notes
- Each file is indexed by its keywords; keywords are distributed and stored on responsible nodes in the ring.
- Searching for any word or phrase will return all matching files (full or partial match).
- Peers communicate using TCP sockets and Chord protocol messages.
- The bootstrap server is only used for peer discovery and logging; all file operations are handled by the Chord ring.

