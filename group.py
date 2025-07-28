# group.py
# post.py
import socket
import uuid
import utils.globals as globals
from datetime import datetime, timezone
from utils import *

def create_group(sock:socket, group_name:str, members:str,app_state: AppState):
    # construct post message
    try:
        timestamp_now = datetime.now(timezone.utc).timestamp()

        message = {
            "TYPE": "GROUP_CREATE",
            "FROM": app_state.user_id,
            "GROUP_ID": group_name.lower() + str(uuid.uuid4()),
            "GROUP_NAME": group_name,
            "MEMBERS": members, # comma separated values
            "TIMESTAMP": timestamp_now,
            "TOKEN": f'{app_state.user_id}|{timestamp_now}|group'
        }

       
        # define initial group data, more importantly, store user ids in dictionary or smthn
        member_list = members.split(',')
        member_list = list(filter(lambda x: x in app_state.peers, member_list))
        # add to dictionary of created groups
        with app_state.lock:
            app_state.owned_groups[message.get("GROUP_ID")] = {
                "GROUP_NAME" : group_name,
                "MEMBERS" : member_list
            }

        sock.sendto(build_message(message).encode('utf-8'), (app_state.broadcast_ip, globals.PORT))
            
        print(f'\n[GROUP_CREATE] You created a new group: {group_name}', end='\n\n')
    except KeyError as e:
        print(f'\n[ERROR] | {e}', end='\n\n')

def handle_create_group(message: dict, app_state: AppState):
    # timestamp_now = datetime.now(timezone.utc).timestamp()
    token:str = message["TOKEN"]
    group_name:str = message["GROUP_NAME"]
    group_id:str = message.get("GROUP_ID")
    invited_members:str = message["MEMBERS"]
    user_id, timestamp, scope = token.split('|')
    timestamp = float(timestamp)

    part_of_group = app_state.user_id in invited_members

    # only receive the message if within group scope and contains this user's id
    if scope == 'group' and part_of_group:
        print(f"\n[GROUP] You've been added to {group_name}", end='\n\n')

        with app_state.lock:
            app_state.joined_groups[group_id] = {
                # empty for now, unless other properties may need to be tracked by members
            }

def handle_update_group(message: dict, app_state: AppState):
    # TODO: remove yourself if part of users to remove, add if part of users to add
    # timestamp_now = datetime.now(timezone.utc).timestamp()
    token:str = message["TOKEN"]
    group_name:str = message.get("GROUP_NAME")
    group_id:str = message.get("GROUP_ID")
    invited_members:str = message.get("ADD")
    removed_members:str = message.get("REMOVE")
    user_id, timestamp, scope = token.split('|')
    timestamp = float(timestamp)

    part_of_group = group_id in app_state.joined_groups

    # only receive the message if within group scope and contains this user's id
    if scope == 'group':
        if part_of_group and app_state.user_id in removed_members:
            print(f"\n[GROUP] You've been removed from {group_name}", end='\n\n')

            with app_state.lock:
                app_state.joined_groups.pop(group_id, None)
        elif not part_of_group and app_state.user_id in invited_members:
            print(f"\n[GROUP] You've been added to {group_name}", end='\n\n')

            with app_state.lock:
                app_state.joined_groups[group_id] = {
                    # empty for now, unless other properties may need to be tracked by members
                }

def update_group(sock:socket, group_id:str, members_add:str, members_remove:str, app_state: AppState):
    
    try:
        timestamp_now = datetime.now(timezone.utc).timestamp()
        
        message = {
            "TYPE": "GROUP_UPDATE",
            "FROM": app_state.user_id,
            "GROUP_NAME": app_state.owned_groups[group_id].get("GROUP_NAME"),
            "GROUP_ID": group_id,
            "ADD": members_add, # comma separated values
            "REMOVE": members_remove,
            "TIMESTAMP": timestamp_now,
            "TOKEN": f'{app_state.user_id}|{timestamp_now}|group'
        }

        sock.sendto(build_message(message).encode('utf-8'), (app_state.broadcast_ip, globals.PORT))

        # get list of members then add or remove them depending on parameters
        member_list:list = app_state.owned_groups[group_id].get("MEMBERS")
        members_remove_list = members_remove.split(',')
        members_append_list = members_add.split(',')

        for member in members_remove_list:
            if (member in member_list):
                member_list.remove(member)
        for member in members_append_list:
            member_list.append(member)

        group_name = app_state.owned_groups[group_id].get("GROUP_NAME")
        print(f"The group \"{group_name}\" member list was updated." )

        pass
    except KeyError as e:
        print(f'\n[ERROR] | {e}', end='\n\n')
        