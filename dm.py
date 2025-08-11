# dm.py
import socket
import uuid
import net_comms
from ack import send_ack, send_with_ack
import utils.globals as globals
from datetime import datetime, timezone
from utils import *


# todo: may need to bind different clients to different ports to ensure direct
# messages are properly received.
def send_dm(
    sock: socket,
    content: str,
    target_user_id: str,
    app_state: AppState,
    custom_token=None,
):
    try:
        # sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # construct DM
        target_user = app_state.peers[target_user_id]
        target_username = target_user["display_name"]
        timestamp_now = datetime.now(timezone.utc).timestamp()

        message = {
            "TYPE": "DM",
            "FROM": app_state.user_id,
            "TO": target_user_id,
            "CONTENT": content,
            "TIMESTAMP": timestamp_now,
            "MESSAGE_ID": str(uuid.uuid4().hex[:16]),
            "TOKEN": (
                custom_token
                if custom_token
                else f"{app_state.user_id}|{timestamp_now + globals.TTL}|chat"
            ),
        }

        # Add avatar fields if avatar data exists
        if app_state.avatar_data:
            message["AVATAR_TYPE"] = "text"
            message["AVATAR_ENCODING"] = "utf-8"
            message["AVATAR_DATA"] = app_state.avatar_data

        # sock.send(build_message(message).encode('utf-8'), (target_user["ip"], globals.PORT))

        send_with_ack(sock, message, app_state, target_user["ip"])

        # Save sent DM to app state
        with app_state.lock:
            if target_user_id not in app_state.dm_messages:
                app_state.dm_messages[target_user_id] = []
            app_state.dm_messages[target_user_id].append(
                {
                    "from": app_state.user_id,
                    "to": target_user_id,
                    "content": content,
                    "timestamp": timestamp_now,
                    "direction": "sent",
                    "token": message["TOKEN"],
                    "message_id": message["MESSAGE_ID"],
                }
            )

        if globals.verbose:
            print(f"\n[SEND >]")
            print(f"Message Type : DM")
            print(f"Timestamp    : {timestamp_now}")
            print(f"From         : {app_state.user_id}")
            print(f"To           : {target_user_id}")
            print(f"To IP        : {target_user['ip']}")
            print(f"Display Name : {target_username}")
            print(f"Content      : {content}")
            print(f"Status       : SENT\n")
        print(f"\n[DM] You sent {target_username}: {content}", end="\n\n")
    except KeyError as e:
        print(f"\n[ERROR] invalid user_id | {e}", end="\n\n")


def handle_dm(
    message: dict,
    app_state: AppState,
    sock: socket,
    sender_ip: str,
):
    # verify TIMESTAMP, TOKEN, etc.

    content: str = message["CONTENT"]
    timestamp_now = datetime.now(timezone.utc).timestamp()
    token = parse_token(message["TOKEN"])

    timestamp_ttl = token["TIMESTAMP_TTL"]
    scope = token["SCOPE"]
    user_id = token["USER_ID"]

    # only receive the message within TTL and chat scope
    if timestamp_ttl - timestamp_now > 0 and scope == "chat":
        send_ack(sock, message["MESSAGE_ID"], sender_ip, app_state)
        display_name = app_state.peers[user_id]["display_name"]
        avatar_data = message.get("AVATAR_DATA", "")

        # Save received DM to app state
        with app_state.lock:
            if user_id not in app_state.dm_messages:
                app_state.dm_messages[user_id] = []
            dm_entry = {
                "from": user_id,
                "to": app_state.user_id,
                "content": content,
                "timestamp": timestamp_now,
                "direction": "received",
                "token": message["TOKEN"],
                "message_id": message["MESSAGE_ID"],
            }
            if avatar_data:
                dm_entry["avatar_data"] = avatar_data
                dm_entry["avatar_type"] = message.get("AVATAR_TYPE", "")
                dm_entry["avatar_encoding"] = message.get("AVATAR_ENCODING", "")
            app_state.dm_messages[user_id].append(dm_entry)

        if globals.verbose:
            print(f"\n[RECV <]")
            print(f"Message Type : DM")
            print(f"Timestamp    : {timestamp_now}")
            print(f"From         : {user_id}")
            print(f"From IP      : {sender_ip}")
            print(f"Display Name : {display_name}")
            print(f"Message Id : {message['MESSAGE_ID']}")
            print(f"Content      : {content}")
            if avatar_data:
                print(f"Avatar Type  : {message.get('AVATAR_TYPE', '')}")
                print(f"Avatar Data  :\n{avatar_data}")
            print(f"Status       : RECEIVED\n")
        print(f"\n[DM] {display_name} chatted you: {content}")
        if avatar_data:
            from utils.utils import display_avatar

            display_avatar(avatar_data)
        print(end="\n\n")
    else:
        if globals.verbose:
            print("\n[ERROR]: TOKEN invalid\n")
