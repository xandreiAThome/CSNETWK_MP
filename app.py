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
import ascii_magic
import os

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

    # Convert avatar source file to ASCII art if provided
    if avatar_source_file:
        try:
            if os.path.exists(avatar_source_file):
                # Convert image to ASCII art
                ascii_art_obj = ascii_magic.from_image(avatar_source_file)
                ascii_art = ascii_art_obj.to_terminal(
                    columns=40
                )  # Convert to terminal output format

                # Encode to base64 for transmission
                from utils.utils import encode_avatar_data

                app_state.avatar_data = encode_avatar_data(ascii_art)
                print(
                    f"[INFO] Avatar loaded and converted to ASCII art from: {avatar_source_file}"
                )
            else:
                print(f"[WARNING] Avatar file not found: {avatar_source_file}")
        except Exception as e:
            print(f"[ERROR] Failed to convert avatar to ASCII art: {e}")

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
