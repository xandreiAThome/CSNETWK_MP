# like.py
import socket
import uuid
import utils.globals as globals
from datetime import datetime, timezone
from utils import *


def send_like(sock: socket, action: str, post_timestamp: str, app_state: AppState):
    # construct like message
    try:
        timestamp_now = datetime.now(timezone.utc).timestamp()

        original_post = app_state.received_posts[post_timestamp]

        post_user_id = original_post.get("USER_ID")

        message = {
            "TYPE": "LIKE",
            "FROM": app_state.user_id,
            "TO": post_user_id,
            "POST_TIMESTAMP": post_timestamp,
            "ACTION": action,
            "TIMESTAMP": timestamp_now,
            "TOKEN": f"{app_state.user_id}|{timestamp_now + globals.POST_TTL}|broadcast",
        }

        display_name = app_state.peers[post_user_id].get("display_name")

        # if user is liking an existing post that was not previously liked
        if (
            action == "LIKE"
            and original_post.get("LIKED") == 0
            and post_timestamp in app_state.received_posts
        ):
            sock.sendto(
                build_message(message).encode("utf-8"),
                (app_state.broadcast_ip, globals.PORT),
            )
            if globals.verbose:
                print(f"\n[SEND >]")
                print(f"Message Type : LIKE")
                print(f"Timestamp    : {timestamp_now}")
                print(f"From         : {app_state.user_id}")
                print(f"To           : {post_user_id}")
                print(f"Post Time    : {post_timestamp}")
                print(f"Action       : LIKE")
                print(f"Status       : SENT\n")
            with app_state.lock:
                app_state.received_posts[post_timestamp]["LIKED"] = 1
            print(f"\n[LIKE] You liked the post of {display_name}.", end="\n\n")
        # otherwise if user is withdrawing their like in an existing post they used to like
        elif (
            action == "UNLIKE"
            and original_post.get("LIKED") == 1
            and post_timestamp in app_state.received_posts
        ):
            sock.sendto(
                build_message(message).encode("utf-8"),
                (app_state.broadcast_ip, globals.PORT),
            )
            if globals.verbose:
                print(f"\n[SEND >]")
                print(f"Message Type : LIKE")
                print(f"Timestamp    : {timestamp_now}")
                print(f"From         : {app_state.user_id}")
                print(f"To           : {post_user_id}")
                print(f"Post Time    : {post_timestamp}")
                print(f"Action       : UNLIKE")
                print(f"Status       : SENT\n")
            with app_state.lock:
                app_state.received_posts[post_timestamp]["LIKED"] = 0
            print(f"\n[UNLIKE] You unliked the post of {display_name}.", end="\n\n")

    except KeyError as e:
        print(f"\n[ERROR] | {e}", end="\n\n")


def handle_like_message(message: dict, app_state: AppState):
    # verify TIMESTAMP, TOKEN, etc.
    timestamp_now = datetime.now(timezone.utc).timestamp()
    original_post_timestamp = message.get("POST_TIMESTAMP")
    token: str = message["TOKEN"]
    user_id, timestamp_ttl, scope = token.split("|")
    timestamp_ttl = float(timestamp_ttl)

    if (
        timestamp_ttl - timestamp_now > 0
        and scope == "broadcast"
        and original_post_timestamp in app_state.sent_posts
    ):
        display_name = app_state.peers.get(user_id).get("display_name")
        content = app_state.sent_posts.get(original_post_timestamp).get("CONTENT")
        action = message.get("ACTION")
        # increment or dicrement based on user action (LIKE or DISLIKE)
        if action == "LIKE":
            if globals.verbose:
                print(f"\n[RECV <]")
                print(f"Message Type : LIKE")
                print(f"Timestamp    : {timestamp_now}")
                print(f"From         : {user_id}")
                print(f"Display Name : {display_name}")
                print(f"Post Time    : {original_post_timestamp}")
                print(f"Action       : LIKE")
                print(f"Content      : {content}")
                print(f"Status       : RECEIVED\n")
            print(f"\n[LIKE] {display_name} likes your post: {content}", end="\n\n")
            with app_state.lock:
                app_state.sent_posts[original_post_timestamp]["LIKES"] += 1
        elif action == "UNLIKE":
            if globals.verbose:
                print(f"\n[RECV <]")
                print(f"Message Type : LIKE")
                print(f"Timestamp    : {timestamp_now}")
                print(f"From         : {user_id}")
                print(f"Display Name : {display_name}")
                print(f"Post Time    : {original_post_timestamp}")
                print(f"Action       : UNLIKE")
                print(f"Content      : {content}")
                print(f"Status       : RECEIVED\n")
            print(f"\n[UNLIKE] {display_name} unliked your post: {content}", end="\n\n")
            with app_state.lock:
                app_state.sent_posts[original_post_timestamp]["LIKES"] -= 1
    else:
        if globals.verbose:
            print("\n[ERROR]: TOKEN invalid\n")
