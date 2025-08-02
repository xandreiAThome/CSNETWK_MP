# post.py
import socket
import uuid
import utils.globals as globals
from datetime import datetime, timezone
from utils import *

def send_post(sock:socket, content:str, app_state: AppState):
    # construct post message
    try:
        timestamp_now = datetime.now(timezone.utc).timestamp()

        message = {
            "TYPE": "POST",
            "MESSAGE_ID": uuid.uuid4(),
            "USER_ID": app_state.user_id,
            "CONTENT": content,
            "TTL": globals.POST_TTL,
            "TIMESTAMP": timestamp_now,
            "TOKEN": f'{app_state.user_id}|{timestamp_now + globals.POST_TTL}|broadcast'
        }

        # add to dictionary of sent posts
        with app_state.lock:
            app_state.sent_posts[str(message.get('TIMESTAMP'))] = message
            app_state.sent_posts[str(message.get('TIMESTAMP'))]["LIKES"] = 0
        
        # print(app_state.sent_posts)

        sock.sendto(build_message(message).encode('utf-8'), (app_state.broadcast_ip, globals.PORT))
        if globals.verbose:
            print(f"\n[SEND >]")
            print(f"Message Type : POST")
            print(f"Timestamp    : {timestamp_now}")
            print(f"From         : {app_state.user_id}")
            print(f"To           : {app_state.broadcast_ip}")
            print(f"Content      : {content}")
            print(f"Status       : SENT\n")
        print(f'\n[POST] You posted: {content}', end='\n\n')
    except KeyError as e:
        print(f'\n[ERROR] | {e}', end='\n\n')


def handle_post_message(message: dict, app_state: AppState):
    # verify TIMESTAMP, TOKEN, etc.

    timestamp_now = datetime.now(timezone.utc).timestamp()
    token:str = message["TOKEN"]
    post_timestamp:str = message["TIMESTAMP"]
    user_id, timestamp_ttl, scope = token.split('|')
    timestamp_ttl = float(timestamp_ttl)

    # only receive post if sender broadcasting is being followed
    if user_id in app_state.following:
        # get content from the post
        content:str = message["CONTENT"]
    
        if timestamp_ttl - timestamp_now > 0 and scope == 'broadcast':

            display_name = app_state.peers[user_id]["display_name"]
            if globals.verbose:
                print(f"\n[RECV <]")
                print(f"Message Type : POST")
                print(f"Timestamp    : {post_timestamp}")
                print(f"From         : {user_id}")
                print(f"Display Name : {display_name}")
                print(f"Content      : {content}")
                print(f"Status       : RECEIVED\n")
            print(f"\n[POST : [UTC Time: {post_timestamp}] {display_name}: {content}", end='\n\n')

            with app_state.lock:
                app_state.received_posts[post_timestamp] = {
                    "USER_ID": user_id,
                    "CONTENT": content,
                    "LIKED": 0,
                }
            # print(app_state.received_posts)
    