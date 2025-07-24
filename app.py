import socket
import sys
import ipaddress
from net_comms import get_local_ip, broadcast_loop, listener_loop
from utils import *
import threading
import globals

# user object (stored in peers and following dicts) has the following fields
# TODO add the avatar fields
# "ip", "display_name, "status","last_seen"


def main(display_name, user_name, avatar_source_file=None):
   peers = {}
   following = {}
   globals.local_ip = get_local_ip()
   globals.user_id = f'{user_name}@{globals.local_ip}'
   globals.broadcast_ip = str(ipaddress.IPv4Network(globals.local_ip + '/' + globals.MASK, False).broadcast_address)
   globals.display_name = display_name

   try:
       sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
       sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Allow rebinding
       sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)  # Enable broadcast
       sock.bind(('', globals.PORT))  # Use PORT constant
       print(f"[INFO] Socket bound to port {globals.PORT}")
       print(f"[INFO] Local IP: {globals.local_ip}")
       print(f"[INFO] user_id: {globals.user_id}")
       print(f"[INFO] Broadcasting to: {globals.broadcast_ip}")
   except Exception as e:
       print(f"[ERROR] Failed to create/bind socket: {e}")
       return

   threading.Thread(target=broadcast_loop, args=(sock,), daemon=True).start()
   threading.Thread(target=listener_loop, args=(sock, peers), daemon=True).start()

   while True:
        cmd = input("Enter command: ")
        if cmd == "exit":
            break

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
    