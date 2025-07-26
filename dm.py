# dm.py
import socket
import uuid
import utils.globals as globals
from datetime import datetime, timezone
from utils import *

# todo: may need to bind different clients to different ports to ensure direct
# messages are properly received.
def send_dm(sock:socket, content:str, target_user_id:str, app_state: AppState):
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
            "MESSAGE_ID": uuid.uuid4(),
            "TOKEN": f'{app_state.user_id}|{timestamp_now + globals.TTL}|chat'
        }

        sock.sendto(build_message(message).encode('utf-8'), (target_user["ip"], globals.PORT))
            
        print(f'\n[DM] You sent {target_username}: {content}', end='\n\n')
    except KeyError as e:
        print(f'\n[ERROR] invalid user_id | {e}', end='\n\n')

def handle_dm(message: dict, app_state: AppState):
    # verify TIMESTAMP, TOKEN, etc.
    timestamp_now = datetime.now(timezone.utc).timestamp()
    token:str = message["TOKEN"] 
    user_id, timestamp_ttl, scope = token.split('|')
    timestamp_ttl = float(timestamp_ttl)
    content:str = message["CONTENT"]
    
    # only receive the message within TTL and chat scope
    if timestamp_ttl - timestamp_now > 0 and scope == 'chat':

        display_name = app_state.peers[user_id]["display_name"]
        print(f"\n[DM] {display_name} chatted you: {content}", end='\n\n')