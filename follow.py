# follow.py
import socket
import uuid
import utils.globals as globals
from datetime import datetime, timezone
from utils import *


def send_follow(sock:socket, target_user_id:str, app_state: AppState):
    # construct FOLLOW message
    # send to target_ip via unicast UDP
    try:   
        target_user = app_state.peers[target_user_id]
        timestamp_now = datetime.now(timezone.utc).timestamp()
        app_state.following.add(target_user_id)
        message = {
            "TYPE": "FOLLOW",
            "MESSAGE_ID": uuid.uuid4(),
            "FROM": app_state.user_id,
            "TO": target_user_id,
            "TIMESTAMP": timestamp_now,
            "TOKEN": f'{app_state.user_id}|{timestamp_now + globals.TTL}|follow'
        }
        sock.sendto(build_message(message).encode('utf-8'), (target_user["ip"], globals.PORT))
        print(f'\n[FOLLOW] You followed {target_user["display_name"]}', end='\n\n')
    except KeyError as e:
        print(f'\n[ERROR] invalid user_id | {e}', end='\n\n')

def handle_follow_message(message: dict, app_state: AppState):
    # verify TIMESTAMP, TOKEN, etc.
    # update followers list
    timestamp_now = datetime.now(timezone.utc).timestamp()
    token:str = message["TOKEN"] 
    user_id, timestamp_ttl, scope = token.split('|')
    timestamp_ttl = float(timestamp_ttl)
    
    if timestamp_ttl - timestamp_now > 0 and scope == 'follow':
        app_state.followers.add(user_id)
        display_name = app_state.peers[user_id]["display_name"]
        print(f"\n[FOLLOW] {display_name} followed you", end='\n\n')
    

def send_unfollow(sock: socket, target_user_id: str, app_state: AppState):
    # construct and send UNFOLLOW message
    try:
        target_user = app_state.peers[target_user_id]
        timestamp_now = datetime.now(timezone.utc).timestamp()

        message = {
            "TYPE": "UNFOLLOW",
            "MESSAGE_ID": uuid.uuid4(),
            "FROM": app_state.user_id,
            "TO": target_user_id,
            "TIMESTAMP": timestamp_now,
            "TOKEN": f'{app_state.user_id}|{timestamp_now + globals.TTL}|follow'
        }

        try:
            app_state.following.remove(target_user_id)
            print(f'\n[FOLLOW] You unfollowed {target_user["display_name"]}', end='\n\n')
            sock.sendto(build_message(message).encode('utf-8'), (target_user["ip"], globals.PORT))
        except KeyError as e:
            print(f'\n[ERROR] You unfollowed a user you did not follow | {e}', end='\n\n')
    except KeyError as e:
        print(f'\n[ERROR] invalid user_id | {e}', end='\n\n')


def handle_unfollow_message(message, app_state: AppState):
    # remove follower from followers list
    timestamp_now = datetime.now(timezone.utc).timestamp()
    token:str = message["TOKEN"] 
    user_id, timestamp_ttl, scope = token.split('|')
    timestamp_ttl = float(timestamp_ttl)
    
    if timestamp_ttl - timestamp_now > 0 and scope == 'follow':
        app_state.followers.discard(user_id)
        display_name = app_state.peers[user_id]["display_name"]
        print(f"\n[FOLLOW] {display_name} followed you", end='\n\n')



# still thinking if we implement local storage
def load_follow_list():
    ...

def save_follow_list():
    ...
