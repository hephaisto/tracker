import argparse

from nicegui import ui
from .main import *

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("hostname", type=str, help="Hostname, IP, 0.0.0.0 or [::]")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen at")
    return parser.parse_args()

def main():
    args = parse_args()
    ui.run(title="dependency test", reload=False, host=args.hostname, port=args.port)

if __name__ == '__main__':
    main()

