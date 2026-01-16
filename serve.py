#!/usr/bin/env python3
"""
DAVINCI-CODE Sandbox Server
Simple HTTP server for the sandbox UI.
"""

import http.server
import socketserver
import os
import sys
import webbrowser
from pathlib import Path

# Set the working directory to the directory where this script is located
script_dir = Path(__file__).parent.absolute()
os.chdir(script_dir)

PORT = 8081 if len(sys.argv) < 2 else int(sys.argv[1])

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        # Only log errors or important stuff to keep console clean
        if int(args[1]) >= 400:
            print(f"\033[91m[{args[1]}] {args[0]}\033[0m")
        else:
            print(f"\033[90m[{args[1]}] {args[0]}\033[0m")

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()

def main():
    socketserver.TCPServer.allow_reuse_address = True
    try:
        with socketserver.TCPServer(("", PORT), QuietHandler) as httpd:
            print(f"\033[94m")
            print("═" * 50)
            print("  DAVINCI-CODE Sandbox Server")
            print("═" * 50)
            print(f"\033[0m")
            print(f"\033[92m✓ Server: http://localhost:{PORT}/sandbox.html\033[0m")
            print(f"\033[90mPress Ctrl+C to stop.\033[0m\n")
            
            # Use a slightly longer delay before opening browser to ensure server is ready
            try:
                webbrowser.open(f"http://localhost:{PORT}/sandbox.html")
            except:
                pass
            
            httpd.serve_forever()
    except OSError as e:
        if e.errno == 98:
            print(f"\033[91mError: Port {PORT} is already in use.\033[0m")
            print(f"Try running: \033[93mfuser -k {PORT}/tcp\033[0m")
        else:
            print(f"\033[91mError: {e}\033[0m")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\033[93mServer stopped.\033[0m")
        sys.exit(0)

if __name__ == "__main__":
    main()
