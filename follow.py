# follow.py
import socket
import uuid
import globals
from datetime import datetime, timezone
from utils import *


def send_follow(sock:socket, target_user_id:str, target_user: dict, following:dict):
    # construct FOLLOW message
    # send to target_ip via unicast UDP
    timestamp = datetime.now(timezone.utc).timestamp()
    following[target_user_id] = target_user
    message = {
        "TYPE": "FOLLOW",
        "MESSAGE_ID": uuid.uuid4(),
        "FROM": globals.user_id,
        "TO": target_user_id,
        "TIMESTAMP": timestamp,
        "TOKEN": f'{globals.user_id}|{timestamp}|follow'
    }
    
    sock.sendto(build_message(message).encode('utf-8'), (target_user["ip"], globals.PORT))

def handle_follow_message(message, addr):
    # verify TIMESTAMP, TOKEN, etc.
    # update followers list
    ...

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
