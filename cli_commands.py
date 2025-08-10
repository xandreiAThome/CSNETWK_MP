import random
from pprint import pprint
from follow import send_follow, send_unfollow
from dm import send_dm
from post import send_post
from like import send_like
from group import create_group, update_group, group_message
from tictactoe import move, send_invite, print_board, send_result


def get_cli_commands(sock, app_state, globals):

    def cmd_custom_dm_token():
        target_user = input("Enter target user id: \n")
        dm_content = input("Enter message content: \n")
        token = input("Enter custon token: \n")
        send_dm(sock, dm_content, target_user, app_state, token)

    def cmd_revoke_dm_token():
        message_id = input("Enter DM message_id to revoke token: \n")
        found = False
        for user_id, messages in app_state.dm_messages.items():
            for msg in messages:
                if (
                    msg.get("message_id") == message_id
                    or msg.get("MESSAGE_ID") == message_id
                ):
                    token = msg.get("token")
                    if not token:
                        print(f"No token found for message_id {message_id}.")
                        return
                    # Parse token to get expiry
                    try:
                        parts = token.split("|")
                        if len(parts) < 2:
                            print(f"Malformed token for message_id {message_id}.")
                            return
                        expiry = float(parts[1])
                        app_state.revoked_token[message_id] = expiry
                        print(
                            f"Revoked token for message_id {message_id} (expires at {expiry})."
                        )
                        found = True
                        return
                    except Exception as e:
                        print(f"Error parsing token: {e}")
                        return
        if not found:
            print(f"No DM message found with message_id {message_id}.")

    def cmd_help():
        print("\nAvailable commands:")
        for cmd in sorted(commands.keys()):
            print(f"- {cmd}")
        print()

    def cmd_verbose():
        globals.verbose = not globals.verbose
        print(f"Verbose mode {'enabled' if globals.verbose else 'disabled'}")

    def cmd_broadcast_verbose():
        globals.broadcast_verbose = not globals.broadcast_verbose
        print(
            f"Broadcast Verbose mode {'enabled' if globals.broadcast_verbose else 'disabled'}"
        )

    def cmd_follow():
        target_user_id = input("Enter target user id: \n")
        send_follow(sock, target_user_id, app_state)

    def cmd_unfollow():
        target_user_id = input("Enter target user id: \n")
        send_unfollow(sock, target_user_id, app_state)

    def cmd_check_followers():
        print()
        print(app_state.followers)
        print()

    def cmd_check_peers():
        print()
        pprint(app_state.peers)
        print()

    def cmd_check_following():
        print()
        pprint(app_state.following)
        print()

    def cmd_post():
        post_content = input("Enter post content: \n")
        send_post(sock, post_content, app_state)

    def cmd_dm():
        target_user = input("Enter target user id: \n")
        dm_content = input("Enter message content: \n")
        send_dm(sock, dm_content, target_user, app_state)

    def cmd_like():
        post_timestamp = input("Enter post timestamp: \n")
        send_like(sock, "LIKE", post_timestamp, app_state)

    def cmd_unlike():
        post_timestamp = input("Enter post timestamp: \n")
        send_like(sock, "UNLIKE", post_timestamp, app_state)

    def cmd_create_group():
        group_name = input("Enter group name: \n")
        members = input("Enter ids of members separated by commas: \n")
        create_group(sock, group_name, members, app_state)

    def cmd_update_group():
        group_id = input("Enter group id: \n")
        members_add = input("Enter ids of members separated by commas to ADD: \n")
        members_remove = input("Enter ids of members separated by commas to REMOVE: \n")
        update_group(sock, group_id, members_add, members_remove, app_state)

    def cmd_check_groups_owned():
        print()
        pprint(app_state.owned_groups)
        print()

    def cmd_check_groups():
        print("Groups owned:")
        pprint(app_state.owned_groups)
        print("Groups joined:")
        pprint(app_state.joined_groups)
        print()

    def cmd_check_received_posts():
        print("\n[RECEIVED POSTS]")
        pprint(app_state.received_posts)
        print()

    def cmd_check_sent_posts():
        print("\n[SENT POSTS]")
        pprint(app_state.sent_posts)
        print()

    def cmd_message_group():
        group_id = input("Enter group id: \n")
        if group_id in app_state.joined_groups or group_id in app_state.owned_groups:
            content = input("Enter message content: \n")
            group_message(sock, group_id, content, app_state)
        else:
            print("invalid group id. see groups using 'check_groups'")

    def cmd_invite_ttt():
        target_user_id = input("Enter target user ID:\n")
        game_id = f"g{random.randint(0, 255)}"
        symbol = "X"
        send_invite(sock, target_user_id, app_state, game_id, symbol)

    def cmd_move():
        with app_state.lock:
            games = list(app_state.active_games.items())
        if not games:
            print("No active games.")
            return
        print("\n[ACTIVE GAMES]")
        for i, (g_id, game) in enumerate(games):
            print(f"{i}) Game {g_id} vs {game['opponent']}")
        try:
            idx = int(input("Choose game #: "))
            game_id, game = games[idx]
        except (ValueError, IndexError):
            print("Invalid game #.")
            return
        if not game["my_turn"]:
            print("[INFO] Not your turn.")
            return
        while True:
            try:
                print(f'You are {game["symbol"]}')
                print_board(game["board"])
                pos = int(input("Enter position (0-8): "))
                if not (0 <= pos <= 8):
                    print("Out of range.")
                    continue
                if game["board"][pos] is not None:
                    print("Cell occupied.")
                    continue
                break
            except ValueError:
                print("Invalid input.")
        move(sock, game["opponent"], app_state, game_id, pos)
        print_board(game["board"])

    def cmd_forfeit():
        with app_state.lock:
            games = list(app_state.active_games.items())
        if not games:
            print("No active games.")
            return
        print("\n[ACTIVE GAMES]")
        for i, (g_id, game) in enumerate(games):
            print(f"{i}) Game {g_id} vs {game['opponent']}")
        try:
            idx = int(input("Choose game #: "))
            game_id, game = games[idx]
        except (ValueError, IndexError):
            print("Invalid game #.")
            return
        choice = input(f"Forfeit {game_id}?\n1. Yes\n2. No\nChoice: ").strip()
        if choice != "1":
            print("Cancelled.")
            return
        opponent = game["opponent"]
        print(f"[FORFEIT] You forfeited game {game_id}")
        send_result(sock, app_state, opponent, game_id, "FORFEIT")
        with app_state.lock:
            del app_state.active_games[game_id]

    def cmd_check_dm_messages():
        target_user_id = input("Enter user ID to view DM conversation: \n")

        if target_user_id not in app_state.dm_messages:
            print(f"No DM conversation found with {target_user_id}")
            print()
            return

        messages = app_state.dm_messages[target_user_id]
        print(f"\n[DM CONVERSATION WITH {target_user_id}]")

        for msg in messages:
            if globals.verbose:
                pprint(msg)
            else:
                timestamp = msg.get("timestamp", "Unknown time")
                direction = msg.get("direction", "unknown")
                content = msg.get("content", "")
                from_user = msg.get("from", "Unknown")

                if direction == "sent":
                    print(f"[{timestamp}] You: {content}")
                else:
                    print(f"[{timestamp}] {from_user}: {content}")
        print()

    def cmd_check_group_messages():
        target_group_id = input("Enter group ID to view group conversation: \n")

        if target_group_id not in app_state.group_messages:
            print(f"No group conversation found with group ID {target_group_id}")
            print()
            return

        messages = app_state.group_messages[target_group_id]
        group_name = "Unknown Group"
        if messages:
            group_name = messages[0].get("group_name", "Unknown Group")

        print(f"\n[GROUP CONVERSATION: {group_name} (ID: {target_group_id})]")

        for msg in messages:
            if globals.verbose:
                pprint(msg)
            else:
                timestamp = msg.get("timestamp", "Unknown time")
                direction = msg.get("direction", "unknown")
                content = msg.get("content", "")
                from_user = msg.get("from", "Unknown")

                if direction == "sent":
                    print(f"[{timestamp}] You: {content}")
                else:
                    print(f"[{timestamp}] {from_user}: {content}")
        print()

    commands = {
        # fmt: off
        "exit": lambda: "__exit__",
        "help": cmd_help,
        "verbose": cmd_verbose,
        "broadcast_verbose": cmd_broadcast_verbose,

        "follow": cmd_follow,
        "unfollow": cmd_unfollow,

        "check_followers": cmd_check_followers,
        "check_peers": cmd_check_peers,
        "check_following": cmd_check_following,
        "check_groups_owned": cmd_check_groups_owned,
        "check_groups": cmd_check_groups,
        "check_received_posts": cmd_check_received_posts,
        "check_sent_posts": cmd_check_sent_posts,
        "check_dm_messages": cmd_check_dm_messages,
        "check_group_messages": cmd_check_group_messages,

        "revoke_dm_token": cmd_revoke_dm_token,

        "post": cmd_post,
        "dm": cmd_dm,
        "like": cmd_like,
        "unlike": cmd_unlike,
        "custom_dm_token": cmd_custom_dm_token,

        "create_group": cmd_create_group,
        "update_group": cmd_update_group,
        "message_group": cmd_message_group,
        "group_message": cmd_message_group,
        
        "invite_ttt": cmd_invite_ttt,
        "move": cmd_move,
        "forfeit": cmd_forfeit,
    }
    return commands
