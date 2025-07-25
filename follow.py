# follow.py
import socket
import uuid
import utils.globals as globals
from datetime import datetime, timezone
from utils import *


def send_follow(sock:socket, target_user_id:str, app_state: AppState):
    # construct FOLLOW message
    # send to target_ip via unicast UDP
    target_user = app_state.peers[target_user_id]
    timestamp = datetime.now(timezone.utc).timestamp()
    app_state.following.add(target_user_id)
    message = {
        "TYPE": "FOLLOW",
        "MESSAGE_ID": uuid.uuid4(),
        "FROM": app_state.user_id,
        "TO": target_user_id,
        "TIMESTAMP": timestamp,
        "TOKEN": f'{app_state.user_id}|{timestamp + globals.TTL}|follow'
    }
    
    sock.sendto(build_message(message).encode('utf-8'), (target_user["ip"], globals.PORT))

def handle_follow_message(message: dict, addr: str, app_state: AppState):
    # verify TIMESTAMP, TOKEN, etc.
    # update followers list
    timestamp_now = datetime.now(timezone.utc).timestamp()
    token:str = message["TOKEN"] 
    user_id, timestamp_ttl, scope = token.split('|')
    timestamp_ttl = float(timestamp_ttl)
    
    if timestamp_ttl - timestamp_now > 0 and scope == 'follow':
        app_state.followers.add(user_id)
        display_name = app_state.peers[user_id]["display_name"]
        print(f"[FOLLOW] {display_name} followed you")
    

def send_unfollow(sock, target_user_id, target_ip):
    # construct and send UNFOLLOW message
    ...

def handle_unfollow_message(message, addr):
    # remove follower from followers list
    ...

def load_follow_list():
    ...

def save_follow_list():
    ...
