# follow.py
import socket
import uuid
import utils.globals as globals
from datetime import datetime, timezone
from utils import *


def send_follow(sock: socket, target_user_id: str, app_state: AppState):
    # construct FOLLOW message
    # send to target_ip via unicast UDP
    try:
        target_user = app_state.peers[target_user_id]
        timestamp_now = datetime.now(timezone.utc).timestamp()

        with app_state.lock:
            app_state.following.add(target_user_id)

        message = {
            "TYPE": "FOLLOW",
            "MESSAGE_ID": uuid.uuid4().hex[:16],
            "FROM": app_state.user_id,
            "TO": target_user_id,
            "TIMESTAMP": timestamp_now,
            "TOKEN": f"{app_state.user_id}|{timestamp_now + globals.TTL}|follow",
        }
        sock.sendto(
            build_message(message).encode("utf-8"), (target_user["ip"], globals.PORT)
        )
        if globals.verbose:
            print(f"\n[SEND >]")
            print(f"Message Type : FOLLOW")
            print(f"Timestamp    : {timestamp_now}")
            print(f"From         : {app_state.user_id}")
            print(f"To           : {target_user_id}")
            print(f"To IP        : {target_user['ip']}")
            print(f"Display Name : {target_user['display_name']}")
            print(f"Status       : SENT\n")
        print(f'\n[FOLLOW] You followed {target_user["display_name"]}', end="\n\n")
    except KeyError as e:
        print(f"\n[ERROR] invalid user_id | {e}", end="\n\n")


def handle_follow_message(message: dict, app_state: AppState):
    # verify TIMESTAMP, TOKEN, etc.
    # update followers list
    timestamp_now = datetime.now(timezone.utc).timestamp()
    token: str = message["TOKEN"]
    user_id, timestamp_ttl, scope = token.split("|")
    timestamp_ttl = float(timestamp_ttl)

    if timestamp_ttl - timestamp_now > 0 and scope == "follow":
        with app_state.lock:
            app_state.followers.add(user_id)

        display_name = app_state.peers[user_id]["display_name"]
        if globals.verbose:
            print(f"\n[RECV <]")
            print(f"Message Type : FOLLOW")
            print(f"Timestamp    : {timestamp_now}")
            print(f"From         : {user_id}")
            print(f"Display Name : {display_name}")
            print(f"Status       : RECEIVED\n")
        print(f"\n[FOLLOW] {display_name} followed you", end="\n\n")
    else:
        if globals.verbose:
            print("\n[ERROR]: TOKEN invalid\n")


def send_unfollow(sock: socket, target_user_id: str, app_state: AppState):
    # construct and send UNFOLLOW message
    try:
        target_user = app_state.peers[target_user_id]
        timestamp_now = datetime.now(timezone.utc).timestamp()

        message = {
            "TYPE": "UNFOLLOW",
            "MESSAGE_ID": uuid.uuid4().hex[:16],
            "FROM": app_state.user_id,
            "TO": target_user_id,
            "TIMESTAMP": timestamp_now,
            "TOKEN": f"{app_state.user_id}|{timestamp_now + globals.TTL}|follow",
        }

        try:
            with app_state.lock:
                app_state.following.remove(target_user_id)

            if globals.verbose:
                print(f"\n[SEND >]")
                print(f"Message Type : UNFOLLOW")
                print(f"Timestamp    : {timestamp_now}")
                print(f"From         : {app_state.user_id}")
                print(f"To           : {target_user_id}")
                print(f"To IP        : {target_user['ip']}")
                print(f"Display Name : {target_user['display_name']}")
                print(f"Status       : SENT\n")
            print(
                f'\n[FOLLOW] You unfollowed {target_user["display_name"]}', end="\n\n"
            )
            sock.sendto(
                build_message(message).encode("utf-8"),
                (target_user["ip"], globals.PORT),
            )
        except KeyError as e:
            print(
                f"\n[ERROR] You unfollowed a user you did not follow | {e}", end="\n\n"
            )
    except KeyError as e:
        print(f"\n[ERROR] invalid user_id | {e}", end="\n\n")


def handle_unfollow_message(message, app_state: AppState):
    # remove follower from followers list
    timestamp_now = datetime.now(timezone.utc).timestamp()
    token: str = message["TOKEN"]
    user_id, timestamp_ttl, scope = token.split("|")
    timestamp_ttl = float(timestamp_ttl)

    if timestamp_ttl - timestamp_now > 0 and scope == "follow":
        with app_state.lock:
            app_state.followers.discard(user_id)
        display_name = app_state.peers[user_id]["display_name"]
        if globals.verbose:
            print(f"\n[RECV <]")
            print(f"Message Type : UNFOLLOW")
            print(f"Timestamp    : {timestamp_now}")
            print(f"From         : {user_id}")
            print(f"Display Name : {display_name}")
            print(f"Status       : RECEIVED\n")
        print(f"\n[FOLLOW] {display_name} unfollowed you", end="\n\n")
    else:
        if globals.verbose:
            print("\n[ERROR]: TOKEN invalid\n")


# still thinking if we implement local storage
def load_follow_list(): ...


def save_follow_list(): ...
