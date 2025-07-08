import socket
import sys
from net_comms import get_local_ip, broadcast_loop, listener_loop
from utils import *
import threading

PORT = 50999
BROADCAST_INTERVAL = 5
BROADCAST_IP = '255.255.255.255'

def main(display_name, user_name, avatar_source_file=None):
   user_id = f'{user_name}@{get_local_ip()}'
   
   sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
   sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Allow rebinding
   sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)  # Enable broadcast
   sock.bind(('', 50999))  # Bind to all interfaces on the given port

   threading.Thread(target=broadcast_loop, args=(sock, user_id, display_name, BROADCAST_IP, PORT, BROADCAST_INTERVAL), daemon=True).start()
   listener_loop(sock, PORT, user_id)

if __name__ == "__main__":
    if len(sys.argv) < 3 or len(sys.argv) > 4:
        print("Usage: python app.py <display_name> <user_name> [avatar_source_file]")
        print("Example: python app.py 'Juan Tamad' juan")
        print("Example: python app.py 'Juan Tamad' juan juan_tamad.png")
        sys.exit(1)
    
    display_name = sys.argv[1]
    user_name = sys.argv[2]
    avatar_source_file = sys.argv[3] if len(sys.argv) == 4 else None
    main(display_name, user_name, avatar_source_file)
    