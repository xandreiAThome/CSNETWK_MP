import socket
import sys
import ipaddress
from net_comms import get_local_ip, broadcast_loop, listener_loop
from utils import AppState, globals
import threading
from follow import send_follow, send_unfollow
from dm import send_dm
from post import send_post
from pprint import pprint

# TODO message queue to wait for acks
# proccess action after getting ack
# retransmission with max attempts if msg not ack 

# Persistent Live variables in app_state class
# App flow for now is
# - 2 seperate threads for broadcasting profile and listening to LSP messages
# - Main loop in app.py for executing commands


def main(display_name, user_name, avatar_source_file=None):
   app_state = AppState()
   app_state.local_ip = get_local_ip()
   app_state.broadcast_ip = str(ipaddress.IPv4Network(app_state.local_ip + '/' + globals.MASK, False).broadcast_address)

   app_state.user_id = f'{user_name}@{app_state.local_ip}'
   app_state.display_name = display_name

   try:
       sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
       sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Allow rebinding
       sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)  # Enable broadcast
       sock.bind(('', globals.PORT))  # Use PORT constant
       print(f"[INFO] Socket bound to port {globals.PORT}")
       print(f"[INFO] Local IP: {app_state.local_ip}")
       print(f"[INFO] user_id: {app_state.user_id}")
       print(f"[INFO] Broadcasting to: {app_state.broadcast_ip}")
   except Exception as e:
       print(f"[ERROR] Failed to create/bind socket: {e}")
       return

   threading.Thread(target=broadcast_loop, args=(sock, app_state), daemon=True).start()
   threading.Thread(target=listener_loop, args=(sock, app_state), daemon=True).start()

   while True:
        cmd = input("Enter command: \n")
        if cmd == "exit":
            break
        elif cmd == "follow":
            target_user_id = input('Enter target user id: \n')
            send_follow(sock, target_user_id, app_state)
        elif cmd == "unfollow":
            target_user_id = input('Enter target user id: \n')
            send_unfollow(sock, target_user_id, app_state)
        elif cmd == "check_followers":
            print() # Adding newline for a more seperated cli logs
            print(app_state.followers,)
            print()
        elif cmd == "check_peers":
            print()
            pprint(app_state.peers)
            print()
        elif cmd == "check_following":
            print()
            pprint( app_state.following)
            print()
        elif cmd == "post":
            post_content = input('Enter post content: \n')
            send_post(sock, post_content, app_state)
        elif cmd == "dm":
            target_user = input('Enter target user id: \n')
            dm_content = input('Enter message content: \n')
            send_dm(sock, dm_content, target_user, app_state)


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
    