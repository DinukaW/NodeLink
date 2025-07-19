#!/usr/bin/env python3
"""
Main entry point for Advanced Chord DHT File Sharing System
Provides easy access to all system components
"""

import sys
import os
import argparse
from pathlib import Path

def main():
    """Main entry point with command selection"""
    parser = argparse.ArgumentParser(
        description="Advanced Chord DHT File Sharing System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Available commands:
  api               Start REST API server (Latest working solution)
  demo              Run interactive demonstration
  test              Run comprehensive test suite
  docker            Show Docker deployment options

Examples:
  python main.py api                    # Start REST API on port 8000
  python main.py demo                   # Run interactive demo
  python main.py test                   # Run test suite
        """
    )
    
    parser.add_argument(
        'command', 
        choices=['api', 'demo', 'test', 'docker'],
        help='Command to execute'
    )
    
    parser.add_argument(
        '--port', 
        type=int, 
        default=8000,
        help='Port number (default: 8000 for API, 7000 for nodes)'
    )
    
    parser.add_argument(
        '--shared-folder', 
        default='shared',
        help='Shared folder for file storage (default: shared)'
    )
    
    parser.add_argument(
        '--host', 
        default='127.0.0.1',
        help='Host address to bind to (default: 127.0.0.1)'
    )
    
    args = parser.parse_args()
    
    # Add src to Python path
    src_path = Path(__file__).parent / 'src'
    sys.path.insert(0, str(src_path))
    
    if args.command == 'api':
        print(f"🌐 Starting REST API server on {args.host}:{args.port}")
        print(f"📚 Documentation will be available at: http://{args.host}:{args.port}/docs")
        os.system(f"python src/rest_api.py --host {args.host} --port {args.port}")
        
    elif args.command == 'demo':
        print("🎉 Starting interactive demonstration...")
        os.system("python demos/demo_comprehensive.py")
        
    elif args.command == 'test':
        print("🧪 Running comprehensive test suite...")
        os.system("python tests/test_comprehensive.py")
        
    elif args.command == 'docker':
        print("🐳 Docker Deployment Options:")
        print()
        print("Quick start:")
        print("  ./scripts/docker-manager.sh start    # Start 3-node cluster")
        print("  ./scripts/docker-manager.sh health   # Check cluster health")
        print("  ./scripts/docker-manager.sh logs     # View logs")
        print("  ./scripts/docker-manager.sh stop     # Stop cluster")
        print()
        print("Manual Docker commands:")
        print("  docker-compose -f docker/docker-compose.yml up -d")
        print()
        print("For complete guide:")
        print("  See docs/DOCKER_GUIDE.md")


if __name__ == "__main__":
    main()
