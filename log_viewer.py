#!/usr/bin/env python3
"""
Log Viewer for Chord DHT System
Displays real-time logs from nodes and bootstrap server
"""

import os
import sys
import time
import glob
from datetime import datetime

class LogViewer:
    def __init__(self):
        self.logs_dir = "logs"
        self.log_files = {}
        self.file_positions = {}
        
    def find_log_files(self):
        """Find all log files in the logs directory"""
        if not os.path.exists(self.logs_dir):
            print("No logs directory found. Start some nodes first.")
            return []
        
        pattern = os.path.join(self.logs_dir, "*.log")
        return glob.glob(pattern)
    
    def tail_logs(self, follow=True):
        """Tail all log files and display new entries"""
        log_files = self.find_log_files()
        
        if not log_files:
            print("No log files found.")
            return
        
        print(f"📋 Found {len(log_files)} log files:")
        for log_file in log_files:
            filename = os.path.basename(log_file)
            print(f"  • {filename}")
        
        print("\n🔍 Monitoring logs (Press Ctrl+C to stop):")
        print("=" * 80)
        
        # Initialize file positions
        for log_file in log_files:
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    # Go to end of file
                    f.seek(0, 2)
                    self.file_positions[log_file] = f.tell()
        
        try:
            while follow:
                new_lines = []
                
                # Check each log file for new content
                for log_file in log_files:
                    if os.path.exists(log_file):
                        with open(log_file, 'r') as f:
                            # Seek to last position
                            f.seek(self.file_positions.get(log_file, 0))
                            new_content = f.read()
                            
                            if new_content:
                                filename = os.path.basename(log_file)
                                for line in new_content.strip().split('\n'):
                                    if line.strip():
                                        new_lines.append(f"[{filename}] {line}")
                                
                                # Update position
                                self.file_positions[log_file] = f.tell()
                
                # Display new lines
                for line in new_lines:
                    print(line)
                
                time.sleep(1)  # Check every second
                
        except KeyboardInterrupt:
            print("\n\n📝 Log monitoring stopped.")
    
    def show_recent_logs(self, lines=50):
        """Show recent log entries from all files"""
        log_files = self.find_log_files()
        
        if not log_files:
            print("No log files found.")
            return
        
        print(f"📋 Recent log entries (last {lines} lines per file):")
        print("=" * 80)
        
        for log_file in log_files:
            filename = os.path.basename(log_file)
            print(f"\n🔍 {filename}:")
            print("-" * 40)
            
            if os.path.exists(log_file):
                try:
                    with open(log_file, 'r') as f:
                        all_lines = f.readlines()
                        recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
                        
                        for line in recent_lines:
                            print(line.rstrip())
                except Exception as e:
                    print(f"Error reading {filename}: {e}")
            else:
                print("File not found")
    
    def show_errors_only(self):
        """Show only error and warning log entries"""
        log_files = self.find_log_files()
        
        if not log_files:
            print("No log files found.")
            return
        
        print("🚨 Error and Warning Log Entries:")
        print("=" * 80)
        
        for log_file in log_files:
            filename = os.path.basename(log_file)
            
            if os.path.exists(log_file):
                try:
                    with open(log_file, 'r') as f:
                        lines = f.readlines()
                        
                    error_lines = []
                    for line in lines:
                        if any(level in line for level in ['ERROR', 'WARNING']):
                            error_lines.append(line.rstrip())
                    
                    if error_lines:
                        print(f"\n🔍 {filename}:")
                        print("-" * 40)
                        for line in error_lines:
                            print(line)
                        
                except Exception as e:
                    print(f"Error reading {filename}: {e}")
    
    def clear_logs(self):
        """Clear all log files"""
        log_files = self.find_log_files()
        
        if not log_files:
            print("No log files found.")
            return
        
        confirm = input(f"Are you sure you want to clear {len(log_files)} log files? (y/N): ")
        if confirm.lower() == 'y':
            for log_file in log_files:
                try:
                    open(log_file, 'w').close()
                    print(f"Cleared {os.path.basename(log_file)}")
                except Exception as e:
                    print(f"Error clearing {os.path.basename(log_file)}: {e}")
            print("✅ All log files cleared.")
        else:
            print("Operation cancelled.")

def main():
    viewer = LogViewer()
    
    if len(sys.argv) < 2:
        print("Chord DHT System - Log Viewer")
        print("=" * 30)
        print("Usage:")
        print("  python3 log_viewer.py tail      # Monitor logs in real-time")
        print("  python3 log_viewer.py recent    # Show recent log entries")
        print("  python3 log_viewer.py errors    # Show only errors and warnings")
        print("  python3 log_viewer.py clear     # Clear all log files")
        print("  python3 log_viewer.py list      # List available log files")
        return
    
    command = sys.argv[1].lower()
    
    if command == "tail":
        viewer.tail_logs()
    elif command == "recent":
        lines = int(sys.argv[2]) if len(sys.argv) > 2 else 50
        viewer.show_recent_logs(lines)
    elif command == "errors":
        viewer.show_errors_only()
    elif command == "clear":
        viewer.clear_logs()
    elif command == "list":
        log_files = viewer.find_log_files()
        if log_files:
            print("📋 Available log files:")
            for log_file in log_files:
                filename = os.path.basename(log_file)
                size = os.path.getsize(log_file)
                mtime = datetime.fromtimestamp(os.path.getmtime(log_file))
                print(f"  • {filename} ({size} bytes, modified: {mtime.strftime('%Y-%m-%d %H:%M:%S')})")
        else:
            print("No log files found.")
    else:
        print(f"Unknown command: {command}")

if __name__ == "__main__":
    main()
