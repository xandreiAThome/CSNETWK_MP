import socket
import sys
import ipaddress
from net_comms import (
    get_local_ip,
    broadcast_loop,
    listener_loop,
    ack_resend_loop,
    peer_cleanup_loop,
)
from utils import AppState, globals
import threading
from follow import send_follow, send_unfollow
from dm import send_dm
from post import send_post
from like import send_like
from pprint import pprint
from group import create_group, update_group, group_message
from tictactoe import move, send_invite, print_board, send_result
import random

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
    app_state.broadcast_ip = str(
        ipaddress.IPv4Network(
            app_state.local_ip + "/" + globals.MASK, False
        ).broadcast_address
    )

    app_state.user_id = f"{user_name}@{app_state.local_ip}"
    app_state.display_name = display_name

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Allow rebinding
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)  # Enable broadcast
        sock.bind(("0.0.0.0", globals.PORT))  # Use PORT constant
        print(f"[INFO] Socket bound to port {globals.PORT}")
        print(f"[INFO] Local IP: {app_state.local_ip}")
        print(f"[INFO] user_id: {app_state.user_id}")
        print(f"[INFO] Broadcasting to: {app_state.broadcast_ip}")
    except Exception as e:
        print(f"[ERROR] Failed to create/bind socket: {e}")
        return

    threading.Thread(target=broadcast_loop, args=(sock, app_state), daemon=True).start()
    threading.Thread(target=listener_loop, args=(sock, app_state), daemon=True).start()
    threading.Thread(
        target=ack_resend_loop, args=(sock, app_state), daemon=True
    ).start()
    threading.Thread(target=peer_cleanup_loop, args=(app_state,), daemon=True).start()

    from cli_commands import get_cli_commands

    commands = get_cli_commands(sock, app_state, globals)

    while True:
        cmd = input("Enter command: \n")
        func = commands.get(cmd)
        if func:
            result = func()
            if result == "__exit__":
                break
        else:
            print("Unknown command.")


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
