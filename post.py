# post.py
import socket
import uuid
import utils.globals as globals
from datetime import datetime, timezone
from utils import *

def send_post(sock:socket, content:str, app_state: AppState):
    # construct POST message
    try:
        timestamp_now = datetime.now(timezone.utc).timestamp()

        message = {
            "TYPE": "POST",
            "MESSAGE_ID": uuid.uuid4(),
            "USER_ID": app_state.user_id,
            "CONTENT": content,
            "TTL": globals.TTL,
            "TIMESTAMP": timestamp_now,
            "TOKEN": f'{app_state.user_id}|{timestamp_now + globals.TTL}|broadcast'
        }

        # I have been trying this approach for over an hour. It actually makes no sense.
        # If I simply send to the ip of every user in the the following list, they should receive it
        # just like how they would receive a private message. What difference does it make if they're on the same machine hmmm?
        # for id in app_state.followers:
        #    try:
        #        print(id)
        #        target_user = app_state.peers[id]
        #        sock.sendto(build_message(message).encode('utf-8'), (target_user["ip"].strip(), globals.PORT))
        #    except KeyError as e:
        #        print(f'\n[ERROR] invalid user_id | {e}', end='\n\n')

        sock.sendto(build_message(message).encode('utf-8'), (app_state.broadcast_ip, globals.PORT))
            
        print(f'\n[POST] You posted: {content}', end='\n\n')
    except KeyError as e:
        print(f'\n[ERROR] | {e}', end='\n\n')


def handle_post_message(message: dict, app_state: AppState):
    # verify TIMESTAMP, TOKEN, etc.

    timestamp_now = datetime.now(timezone.utc).timestamp()
    token:str = message["TOKEN"] 
    user_id, timestamp_ttl, scope = token.split('|')
    timestamp_ttl = float(timestamp_ttl)

    # only receive post if sender broadcasting is being followed
    if user_id in app_state.following:
        # get content from the post
        content:str = message["CONTENT"]
    
        if timestamp_ttl - timestamp_now > 0 and scope == 'broadcast':
            with app_state.lock:
                app_state.followers.add(user_id)

            display_name = app_state.peers[user_id]["display_name"]
            print(f"\n[POST] {display_name}: {content}", end='\n\n')
    