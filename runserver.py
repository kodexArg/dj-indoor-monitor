import os
import subprocess
import argparse
import psutil
import signal
import sys

def kill_process_using_port(port):
    """Kill the process that is using the specified port."""
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            with proc.oneshot():
                # Check both open files and network connections for the process
                sockets = proc.open_files() + proc.net_connections(kind='inet4')
                for conn in sockets:
                    try:
                        # Check if connection is on the desired port
                        if hasattr(conn, 'laddr') and conn.laddr.port == port:
                            print(f"Killing process {proc.info['name']} with PID {proc.info['pid']} on port {port}")
                            proc.kill()
                            return
                    except AttributeError:
                        continue
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

def signal_handler(signum, frame):
    """Handle termination signals gracefully."""
    print("\nShutting down server...")
    sys.exit(0)

def start_uvicorn(host, port):
    """Start Uvicorn with the specified host and port."""
    command = ["uvicorn", "project.asgi:application", "--reload", "--host", host, "--port", str(port)]
    try:
        print(f"Starting Uvicorn server at {host}:{port}")
        process = subprocess.Popen(command, shell=True, close_fds=True)
        return process
    except FileNotFoundError:
        print("Error: Uvicorn not found. Please install it using 'pip install uvicorn'")
        sys.exit(1)
    except subprocess.SubprocessError as e:
        print(f"Error starting Uvicorn: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Control script for Uvicorn server.")
    parser.add_argument("-H", "--host", type=str, default="0.0.0.0", help="IP of the host to bind Uvicorn to.")
    parser.add_argument("-p", "--port", type=int, default=8000, help="Port to bind Uvicorn to.")
    parser.add_argument("-K", "--killzombies", action="store_true", help="Kill any process using the port before starting.")
    args = parser.parse_args()

    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Kill any process using the port if --killzombies is specified
    if args.killzombies:
        print(f"--killzombies specified, attempting to kill any process using port {args.port}")
        kill_process_using_port(args.port)
    else:
        print("--killzombies not specified, skipping killing processes on the specified port.")

    # Start Uvicorn process
    process = start_uvicorn(args.host, args.port)

    try:
        process.wait()
    except KeyboardInterrupt:
        process.terminate()
        process.wait()
        print("\nServer stopped.")

if __name__ == "__main__":
    main()
