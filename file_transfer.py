import base64
import os
import time
import uuid
import utils.globals as globals

from utils import build_message


def is_valid_token(token: str, expected_scope: str) -> bool:
    try:
        user_id, expiry_str, scope = token.split("|")
        expiry = int(expiry_str)
        return scope == expected_scope and time.time() <= expiry
    except Exception:
        return False


def handle_file_offer(message, app_state, sock, sender_ip):
    file_id = message["FILEID"]
    if not is_valid_token(message["TOKEN"], "file"):
        return

    if file_id in app_state.file_transfers or file_id in app_state.pending_file_offers:
        return

    app_state.pending_file_offers[file_id] = {
        "from": message["FROM"],
        "filename": message["FILENAME"],
        "filesize": int(message["FILESIZE"]),
        "filetype": message["FILETYPE"],
        "description": message.get("DESCRIPTION", ""),
        "timestamp": int(message["TIMESTAMP"]),
    }

    sender_name = message["FROM"].split("@")[0]
    print(f"\nUser {sender_name} is sending you a file: {message['FILENAME']} ({message['FILESIZE']} bytes)")
    print(f"Description: {message.get('DESCRIPTION', 'No description')}")
    print(f"To accept: accept_file('{file_id}')\n")


def accept_file(file_id):
    from utils.globals import app_state  # pull app_state if not passed
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

    print(f"Accepted file offer for {offer['filename']}")


def handle_file_chunk(message, app_state, sock, sender_ip):
    file_id = message["FILEID"]
    if file_id not in app_state.file_transfers:
        return

    if not is_valid_token(message["TOKEN"], "file"):
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

    if len(transfer["chunks"]) == total_chunks:
        assemble_file(file_id, app_state, sock)


def assemble_file(file_id, app_state, sock):
    transfer = app_state.file_transfers[file_id]
    filename = transfer["filename"]
    chunks = transfer["chunks"]
    total_chunks = transfer["total_chunks"]

    try:
        with open(filename, "wb") as f:
            for i in range(total_chunks):
                f.write(chunks[i])
    except Exception as e:
        print(f"Failed to write file: {e}")
        return

    print(f"\nFile transfer of {filename} is complete\n")

    send_file_received(sock, app_state.user_id, transfer["from"], file_id)
    del app_state.file_transfers[file_id]


def send_file_received(sock, from_id, to_id, file_id):
    message = {
        "TYPE": "FILE_RECEIVED",
        "FROM": from_id,
        "TO": to_id,
        "FILEID": file_id,
        "STATUS": "COMPLETE",
        "TIMESTAMP": str(int(time.time()))
    }
    ip = to_id.split("@")[1]
    sock.sendto(build_message(message).encode("utf-8"), (ip, globals.PORT))


def send_file(sock, app_state, to_user_id, filepath, description=""):
    if not os.path.isfile(filepath):
        print("File not found.")
        return

    filesize = os.path.getsize(filepath)
    filetype = "application/octet-stream"  # fallback
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

    to_ip = to_user_id.split("@")[1]
    sock.sendto(build_message(offer_msg).encode("utf-8"), (to_ip, globals.PORT))

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

    print(f"[SENT FILE] {filepath} ({filesize} bytes) to {to_user_id}")
