from datetime import datetime, timezone
import socket
import time
import random
from utils import *
import utils.globals as globals
from follow import handle_follow_message, handle_unfollow_message
from dm import handle_dm
from post import handle_post_message
from like import handle_like_message
from group import handle_create_group, handle_update_group, handle_group_message
from tictactoe import handle_invite, handle_move, handle_result
from file_transfer import (
    handle_file_offer,
    handle_file_chunk,
    handle_file_accepted,
    handle_file_received,
)
from ack import handle_ack


def get_local_ip():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
        return ip
    except Exception:
        return "127.0.0.1"


def send_ping(sock: socket, app_state: AppState):
    message = {"TYPE": "PING", "USER_ID": app_state.user_id}

    sock.sendto(
        build_message(message).encode("utf-8"), (app_state.broadcast_ip, globals.PORT)
    )
    if globals.broadcast_verbose:
        print(f"\n[SEND >]")
        print(f"Message Type : PING")
        print(f"Timestamp    : {time.time()}")
        print(f"From IP      : {app_state.user_id.split('@')[1]}")
        print(f"From         : {app_state.user_id}")
        print(f"To           : {app_state.broadcast_ip}")
        print(f"Status       : SENT\n")


def send_profile(sock: socket, status: str, app_state: AppState):
    message = {
        "TYPE": "PROFILE",
        "USER_ID": app_state.user_id,
        "DISPLAY_NAME": app_state.display_name,
        "STATUS": status,
    }

    # Add avatar fields if avatar data exists
    if app_state.avatar_data:
        message["AVATAR_TYPE"] = "text"
        message["AVATAR_ENCODING"] = "utf-8"
        message["AVATAR_DATA"] = app_state.avatar_data

    sock.sendto(
        build_message(message).encode("utf-8"), (app_state.broadcast_ip, globals.PORT)
    )
    if globals.broadcast_verbose:
        print(f"\n[SEND >]")
        print(f"Message Type : PROFILE")
        print(f"Timestamp    : {time.time()}")
        print(f"From IP      : {app_state.user_id.split('@')[1]}")
        print(f"From         : {app_state.user_id}")
        print(f"To           : {app_state.broadcast_ip}")
        print(f"Status       : {status}")
        print(f"Display Name : {app_state.display_name}")
        print(f"\n")


def handle_ping(msg: dict, addr: str, app_state: AppState):
    user_id = msg.get("USER_ID")

    if globals.broadcast_verbose:
        print(f"\n[RECV <]")
        print(f"Message Type : PING")
        print(f"Timestamp    : {datetime.now(timezone.utc).timestamp()}")
        print(f"From IP      : {addr}")
        print(f"User ID      : {user_id}\n")

    # Update last_seen timestamp for existing peers
    if user_id in app_state.peers:
        with app_state.lock:
            app_state.peers[user_id]["last_seen"] = datetime.now(
                timezone.utc
            ).timestamp()


def handle_profile(msg: dict, addr: str, app_state: AppState):
    display_name = msg.get("DISPLAY_NAME", "Unknown")
    user_id = msg.get("USER_ID")
    status = msg.get("STATUS", "")
    avatar_data = msg.get("AVATAR_DATA", "")

    if globals.broadcast_verbose:
        print(f"\n[RECV <]")
        print(f"Message Type : PROFILE")
        print(f"Timestamp    : {datetime.now(timezone.utc).timestamp()}")
        print(f"From IP      : {addr}")
        print(f"User ID      : {user_id}")
        print(f"Display Name : {display_name}")
        print(f"Status       : {status}")
        if avatar_data:
            print(f"Avatar Type  : {msg.get('AVATAR_TYPE', '')}")
            print(f"Avatar Data  :\n{avatar_data}")
        print(f"\n")

    if user_id not in app_state.peers:
        print(
            f"\n[PROFILE] (Detected User) {display_name} [{user_id}]: {status}",
            end="",
        )
        if avatar_data:
            print(f"\nAvatar:\n{avatar_data}")
        print(end="\n\n")
    # Avatar is optional — we ignore AVATAR_* if unsupported
    with app_state.lock:
        peer_data = {
            "ip": addr,
            "display_name": display_name,
            "status": status,
            "last_seen": datetime.now(timezone.utc).timestamp(),
        }
        if avatar_data:
            peer_data["avatar_data"] = avatar_data
            peer_data["avatar_type"] = msg.get("AVATAR_TYPE", "")
            peer_data["avatar_encoding"] = msg.get("AVATAR_ENCODING", "")
        app_state.peers[user_id] = peer_data


def broadcast_loop(sock: socket, app_state: AppState):
    send_profile(sock, "BROADCASTING", app_state)
    # send profile every 3rd time, else send ping
    while True:
        send_ping(sock, app_state)
        time.sleep(globals.BROADCAST_INTERVAL)


def listener_loop(sock: socket, app_state: AppState):
    print(f"[LISTENING] UDP port {globals.PORT} on {app_state.local_ip}...\n")
    min_profile_interval = 5  # seconds
    last_profile_time = 0

    while True:
        data, addr = sock.recvfrom(65535)
        try:
            raw_msg = data.decode("utf-8")
            msg = parse_message(raw_msg)
            msg_type = msg.get("TYPE")

            # Induce packet loss for FILE and GAME messages
            if globals.induce_loss and msg_type in {
                "TICTACTOE_INVITE",
                "TICTACTOE_MOVE",
                "TICTACTOE_RESULT",
                "FILE_CHUNK",
            }:
                if random.random() < globals.loss_rate:
                    if globals.verbose:
                        print(f"[DROP] Induced packet loss for {msg_type}")
                    continue

            from_field = msg.get("FROM")
            user_id_field = msg.get("USER_ID")

            # Only check FROM if it exists and is expected for this msg_type
            if from_field:
                try:
                    # check for core feature msgs that the ip hasnt been spoofed
                    # I am crying from the fact that the format of msgs are inconsistent
                    # some only have user_id and others have FROM which basically is the user_id of the sender
                    # so I need to seperate the if else of PING AND PROFILE from the rest of the msg_types
                    # REMINDER that POST also has user_id instead of FROM :-(
                    username, user_ip = from_field.split("@")
                    if user_ip != addr[0]:
                        continue
                    if from_field == app_state.user_id:
                        continue
                except ValueError:
                    pass  # FROM field is malformed, skip or handle as needed

            # Only check USER_ID if it exists and is expected for this msg_type
            if user_id_field and user_id_field == app_state.user_id:
                continue

            # discovery
            # only send profile if interval has passed, pings just trigger the check
            if msg_type == "PING":
                handle_ping(msg, addr[0], app_state)
                now = time.time()
                if (now - last_profile_time) > min_profile_interval:
                    send_profile(sock, "BROADCASTING", app_state)
                    last_profile_time = now

            elif msg_type == "PROFILE":
                handle_profile(msg, addr[0], app_state)

            # handle cases where the message uses USER_ID instead of FROM
            # failure to handle such cases used to result in errors trying to parse Nonetype

            elif msg.get("FROM") == app_state.user_id:
                continue  # Message is from self again, curse the msg formats
            elif msg_type == "ACK":
                handle_ack(msg, app_state, addr[0])
            # core features
            elif msg_type == "FOLLOW":
                handle_follow_message(msg, app_state)
            elif msg_type == "UNFOLLOW":
                handle_unfollow_message(msg, app_state)
            elif msg_type == "POST":
                handle_post_message(msg, app_state)
            elif msg_type == "DM":
                handle_dm(msg, app_state, sock, addr[0])
            elif msg_type == "LIKE":
                handle_like_message(msg, app_state)
            elif msg_type == "GROUP_CREATE":
                handle_create_group(msg, app_state)
            elif msg_type == "GROUP_UPDATE":
                handle_update_group(msg, app_state)
            elif msg_type == "GROUP_MESSAGE":
                handle_group_message(msg, app_state)
            elif msg_type == "TICTACTOE_INVITE":
                handle_invite(msg, app_state, sock, addr[0])
            elif msg_type == "TICTACTOE_MOVE":
                handle_move(msg, app_state, sock, addr[0])
            elif msg_type == "TICTACTOE_RESULT":
                handle_result(msg, app_state, sock, addr[0])
            elif msg_type == "FILE_OFFER":
                handle_file_offer(msg, app_state, sock)
            elif msg_type == "FILE_CHUNK":
                handle_file_chunk(msg, app_state, sock, addr[0])
            elif msg_type == "FILE_ACCEPTED":
                handle_file_accepted(msg, app_state)
            elif msg_type == "FILE_RECEIVED":
                handle_file_received(msg)
            else:
                print(f"[UNKNOWN TYPE] {msg_type} from {addr}")
        except Exception as e:
            print("[ERROR] Could not parse message:", e)


def ack_resend_loop(sock, app_state):
    while True:
        time.sleep(1)
        with app_state.lock:
            for msg_id, entry in list(app_state.pending_acks.items()):
                if time.time() - entry["timestamp"] > 2:
                    if entry["retries"] >= 3:
                        if globals.verbose:
                            print(f"\n[DROP !]")
                            print(f"MessageID    : {msg_id}")
                            print(f"Reason       : Max retries reached\n")
                            print(f"[RESEND !] Gave up on {msg_id}")
                        del app_state.pending_acks[msg_id]
                    else:
                        entry["retries"] += 1
                        entry["timestamp"] = time.time()
                        sock.sendto(
                            build_message(entry["message"]).encode("utf-8"),
                            (entry["destination"], globals.PORT),
                        )

                        if globals.verbose or globals.induce_loss:
                            msg_type = entry["message"].get("TYPE", "UNKNOWN")
                            print(f"\n[RESEND !]")
                            print(f"Message Type : {msg_type}")
                            print(
                                f"Timestamp    : {datetime.now(timezone.utc).timestamp()}"
                            )
                            print(f"From IP      : {app_state.user_id.split('@')[1]}")
                            print(f"From         : {app_state.user_id}")
                            print(f"MessageID    : {msg_id}")
                            print(f"Retry Count  : {entry['retries']}")
                            print(f"Destination  : {entry['destination']}\n")


def peer_cleanup_loop(app_state):
    """Remove inactive peers that haven't been seen within TTL seconds"""
    while True:
        time.sleep(globals.TTL // 2)  # Check every 30 seconds (half of TTL)
        current_time = datetime.now(timezone.utc).timestamp()

        with app_state.lock:
            inactive_peers = []
            for user_id, peer_data in app_state.peers.items():
                if current_time - peer_data["last_seen"] > globals.TTL:
                    inactive_peers.append(user_id)

            for user_id in inactive_peers:
                peer_data = app_state.peers[user_id]
                print(
                    f"\n[CLEANUP] Removed inactive peer: {peer_data['display_name']} [{user_id}]",
                    end="\n\n",
                )
                del app_state.peers[user_id]

            # Cleanup expired sent posts
            expired_sent = [
                post_timestamp
                for post_timestamp, post in app_state.sent_posts.items()
                if current_time > post.get("TIMESTAMP", 0) + globals.POST_TTL
            ]
            for post_timestamp in expired_sent:
                print(f"[CLEANUP] Removed expired sent post: {post_timestamp}")
                del app_state.sent_posts[post_timestamp]

            # Cleanup expired received posts
            expired_received = [
                post_timestamp
                for post_timestamp, post in app_state.received_posts.items()
                if current_time > post.get("TIMESTAMP", 0) + globals.POST_TTL
            ]
            for post_timestamp in expired_received:
                print(f"[CLEANUP] Removed expired received post: {post_timestamp}")
                del app_state.received_posts[post_timestamp]
