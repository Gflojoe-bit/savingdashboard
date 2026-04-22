#!/usr/bin/env python3
"""Tiny launcher so we can preview the placeholder HTML files.
Bypasses http.server's argparse default=os.getcwd() which trips the sandbox."""
import os, sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

SERVE_DIR = "/Users/josephgorenflo/Documents/savings-dashboard/savings-dashboard-screens"
PORT = 8765

os.chdir(SERVE_DIR)
with ThreadingHTTPServer(("127.0.0.1", PORT), SimpleHTTPRequestHandler) as httpd:
    print(f"serving {SERVE_DIR} on http://127.0.0.1:{PORT}", flush=True)
    httpd.serve_forever()
