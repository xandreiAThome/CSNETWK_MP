import base64
import os
import time
import uuid
import utils.globals as globals

from utils import build_message


def is_valid_token(token: str, expected_scope: str, expected_user: str = None) -> bool:
    try:
        user_id, expiry_str, scope = token.split("|")
        expiry = int(expiry_str)
        if expected_user and expected_user != user_id:
            return False
        return scope == expected_scope and time.time() <= expiry
    except Exception:
        return False


def handle_file_offer(message: dict, app_state, sock):
    file_id = message["FILEID"]
    if not is_valid_token(message["TOKEN"], "file", expected_user=message["FROM"].split("@")[0]):
        return

    if file_id in app_state.file_transfers or file_id in app_state.pending_file_offers:
        return

    filesize = int(message["FILESIZE"])

    app_state.pending_file_offers[file_id] = {
        "from": message["FROM"],
        "filename": message["FILENAME"],
        "filesize": filesize,
        "filetype": message["FILETYPE"],
        "description": message.get("DESCRIPTION", ""),
        "timestamp": int(message["TIMESTAMP"]),
    }

    if globals.verbose:
        print(f"[VERBOSE] Received FILE_OFFER for {message['FILENAME']} from {message['FROM']} (ID={file_id})")

    if filesize == 0:
        if globals.verbose:
            print(f"[VERBOSE] Zero-byte file detected, auto-accepting {message['FILENAME']}")
        app_state.file_transfers[file_id] = {
            "from": message["FROM"],
            "filename": message["FILENAME"],
            "chunks": {},
            "total_chunks": 0,
            "accepted_time": time.time()
        }
        assemble_file(file_id, app_state, sock)
        return

    sender_name = message["FROM"].split("@")[0]
    print(f"\nUser {sender_name} is sending you a file: {message['FILENAME']} ({filesize} bytes)")
    print(f"Description: {message.get('DESCRIPTION', 'No description')}")
    print("You can accept it using the 'accept_file' command in the CLI.\n")


def accept_file(file_id: str, app_state):
    if file_id not in app_state.pending_file_offers:
        print("No such file offer found.")
        return

    offer = app_state.pending_file_offers.pop(file_id)
    app_state.file_transfers[file_id] = {
        "from": offer["from"],
        "filename": offer["filename"],
        "chunks": {},
        "total_chunks": None,
        "accepted_time": time.time()
    }

    if globals.verbose:
        print(f"[VERBOSE] Accepted file offer {file_id} ({offer['filename']}) from {offer['from']}")

    print(f"Accepted file offer for {offer['filename']}")


def handle_file_chunk(message: dict, app_state, sock):
    file_id = message["FILEID"]
    if file_id not in app_state.file_transfers:
        return

    if not is_valid_token(message["TOKEN"], "file", expected_user=message["FROM"].split("@")[0]):
        return

    try:
        chunk_index = int(message["CHUNK_INDEX"])
        total_chunks = int(message["TOTAL_CHUNKS"])
        chunk_data = base64.b64decode(message["DATA"])
    except Exception:
        return

    transfer = app_state.file_transfers[file_id]
    transfer["chunks"][chunk_index] = chunk_data
    transfer["total_chunks"] = total_chunks

    if globals.verbose:
        print(f"[VERBOSE] Received chunk {chunk_index+1}/{total_chunks} for file {transfer['filename']} (ID={file_id})")

    if len(transfer["chunks"]) == total_chunks:
        assemble_file(file_id, app_state, sock)


def assemble_file(file_id: str, app_state, sock):
    transfer = app_state.file_transfers[file_id]
    filename = transfer["filename"]
    chunks = transfer["chunks"]
    total_chunks = transfer["total_chunks"]

    # Prevent overwriting existing files
    base_name, ext = os.path.splitext(filename)
    counter = 1
    while os.path.exists(filename):
        filename = f"{base_name}_{counter}{ext}"
        counter += 1

    try:
        with open(filename, "wb") as f:
            if total_chunks > 0:
                for i in range(total_chunks):
                    f.write(chunks[i])
            else:
                pass  # Explicitly handle zero-byte case
    except Exception as e:
        print(f"Failed to write file: {e}")
        return

    if globals.verbose:
        print(f"[VERBOSE] Assembled {total_chunks} chunks into file {filename}")

    print(f"\nFile transfer of {filename} is complete\n")

    send_file_received(sock, app_state, transfer["from"], file_id)
    del app_state.file_transfers[file_id]


def send_file_received(sock, app_state, to_id: str, file_id: str):
    message = {
        "TYPE": "FILE_RECEIVED",
        "FROM": app_state.user_id,
        "TO": to_id,
        "FILEID": file_id,
        "STATUS": "COMPLETE",
        "TIMESTAMP": str(int(time.time()))
    }

    if "@" not in to_id or len(to_id.split("@")) < 2:
        print(f"Invalid user ID format for recipient: {to_id}")
        return

    ip = to_id.split("@")[1]
    sock.sendto(build_message(message).encode("utf-8"), (ip, globals.PORT))

    if globals.verbose:
        print(f"[VERBOSE] Sent FILE_RECEIVED ack for file ID={file_id} to {to_id}")


def send_file(sock, app_state, to_user_id: str, filepath: str, description: str = ""):
    if not os.path.isfile(filepath):
        print("File not found.")
        return

    filesize = os.path.getsize(filepath)
    filetype = "application/octet-stream"  # default
    if filepath.endswith(".jpg") or filepath.endswith(".jpeg"):
        filetype = "image/jpeg"
    elif filepath.endswith(".png"):
        filetype = "image/png"
    elif filepath.endswith(".txt"):
        filetype = "text/plain"

    with open(filepath, "rb") as f:
        data = f.read()

    file_id = uuid.uuid4().hex[:8]
    timestamp = int(time.time())
    token = f"{app_state.user_id}|{timestamp + globals.POST_TTL}|file"

    offer_msg = {
        "TYPE": "FILE_OFFER",
        "FROM": app_state.user_id,
        "TO": to_user_id,
        "FILENAME": os.path.basename(filepath),
        "FILESIZE": filesize,
        "FILETYPE": filetype,
        "FILEID": file_id,
        "DESCRIPTION": description,
        "TIMESTAMP": timestamp,
        "TOKEN": token,
    }

    if "@" not in to_user_id or len(to_user_id.split("@")) < 2:
        print("Invalid user ID format. Expected format: username@ip_address")
        return
    to_ip = to_user_id.split("@")[1]
    sock.sendto(build_message(offer_msg).encode("utf-8"), (to_ip, globals.PORT))

    if globals.verbose:
        print(f"[VERBOSE] Sent FILE_OFFER for {filepath} ({filesize} bytes) to {to_user_id} (ID={file_id})")

    if filesize == 0:
        if globals.verbose:
            print(f"[VERBOSE] Zero-byte file detected, sending FILE_RECEIVED immediately.")
        send_file_received(sock, app_state, to_user_id, file_id)
        print(f"[SENT FILE] {filepath} (0 bytes) to {to_user_id}")
        return

    # Now send chunks
    chunk_size = globals.CHUNK_SIZE
    total_chunks = (len(data) + chunk_size - 1) // chunk_size

    for i in range(total_chunks):
        chunk_data = data[i * chunk_size: (i + 1) * chunk_size]
        chunk_msg = {
            "TYPE": "FILE_CHUNK",
            "FROM": app_state.user_id,
            "TO": to_user_id,
            "FILEID": file_id,
            "CHUNK_INDEX": i,
            "TOTAL_CHUNKS": total_chunks,
            "CHUNK_SIZE": len(chunk_data),
            "TOKEN": token,
            "DATA": base64.b64encode(chunk_data).decode("utf-8"),
        }
        sock.sendto(build_message(chunk_msg).encode("utf-8"), (to_ip, globals.PORT))

        if globals.verbose:
            print(f"[VERBOSE] Sent chunk {i+1}/{total_chunks} for file {filepath} (ID={file_id})")

    print(f"[SENT FILE] {filepath} ({filesize} bytes) to {to_user_id}")