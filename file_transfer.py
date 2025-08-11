import base64
import os
import time
import uuid
import threading
import utils.globals as globals
from utils import build_message
from ack import send_ack, send_with_ack


def is_valid_token(token: str, expected_scope: str, expected_user: str = None) -> bool:
    try:
        user_id, expiry_str, scope = token.split("|")
        expiry = int(expiry_str)
        if expected_user and expected_user != user_id:
            return False
        return scope == expected_scope and time.time() <= expiry
    except Exception:
        return False


def handle_file_offer(message, app_state, sock):
    print(f"[DEBUG] handle_file_offer called with file_id={message.get('FILEID')}")
    file_id = message["FILEID"]
    sender_user = message["FROM"].split("@")[0]

    if not is_valid_token(message["TOKEN"], "file"):
        print("[DEBUG] Invalid token:", message["TOKEN"])
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

    print(
        f"\nUser {sender_user} is sending you a file: {message['FILENAME']} ({message['FILESIZE']} bytes)"
    )
    print(f"Description: {message.get('DESCRIPTION', 'No description')}")
    print(f"To see current file offers, run cmd accept_file\n")


def accept_file(file_id, app_state, sock):
    if file_id not in app_state.pending_file_offers:
        print("No such file offer found.")
        return

    offer = app_state.pending_file_offers.pop(file_id)
    app_state.file_transfers[file_id] = {
        "from": offer["from"],
        "filename": offer["filename"],
        "chunks": {},
        "total_chunks": None,
        "accepted_time": time.time(),
    }

    print(f"Accepted file offer for {offer['filename']}")

    # Send FILE_ACCEPTED back to sender to signal readiness
    from_id = app_state.user_id
    to_id = offer["from"]
    file_accepted_msg = {
        "TYPE": "FILE_ACCEPTED",
        "FROM": from_id,
        "TO": to_id,
        "FILEID": file_id,
        "TIMESTAMP": str(int(time.time())),
    }
    # Extract IP from to_id
    if "@" not in to_id or len(to_id.split("@")) < 2:
        print(f"Invalid user ID format for recipient: {to_id}")
        return
    to_ip = to_id.split("@")[1]
    sock.sendto(build_message(file_accepted_msg).encode("utf-8"), (to_ip, globals.PORT))
    print(f"[SENT] FILE_ACCEPTED for file_id={file_id} to {to_id}")


def handle_file_chunk(message, app_state, sock, sender_ip):
    # Send ACK for received chunk using FILEID
    from utils.globals import verbose

    file_id = message["FILEID"]

    # Ensure CHUNK_INDEX is present
    if "CHUNK_INDEX" not in message:
        print(f"[ERROR] FILE_CHUNK missing CHUNK_INDEX field")
        return

    chunk_index = int(message["CHUNK_INDEX"])
    ack_id = f"{file_id}_chunk_{chunk_index}"

    if verbose:
        print(
            f"[DEBUG] Received FILE_CHUNK with FILEID: {file_id}, chunk: {chunk_index}"
        )

    send_ack(sock, ack_id, sender_ip, app_state)

    if file_id not in app_state.file_transfers:
        print(f"[DEBUG] Chunk received for unknown file_id={file_id}, ignoring.")
        return

    if not is_valid_token(message["TOKEN"], "file"):
        print("[DEBUG] Invalid token in file chunk, ignoring.")
        return

    try:
        total_chunks = int(message["TOTAL_CHUNKS"])
        chunk_data = base64.b64decode(message["DATA"])
    except Exception as e:
        print(f"[DEBUG] Exception decoding chunk data: {e}")
        return

    transfer = app_state.file_transfers[file_id]
    transfer["chunks"][chunk_index] = chunk_data
    transfer["total_chunks"] = total_chunks

    if verbose:
        print(
            f"[DEBUG] Received chunk {chunk_index + 1}/{total_chunks} for file '{transfer['filename']}' (file_id={file_id})"
        )
        print(
            f"[DEBUG] Total chunks received so far: {len(transfer['chunks'])}/{total_chunks}"
        )

    if len(transfer["chunks"]) == total_chunks:
        print(f"[DEBUG] All chunks received for file_id={file_id}, assembling file.")
        assemble_file(file_id, app_state, sock)
    else:
        missing_chunks = [i for i in range(total_chunks) if i not in transfer["chunks"]]
        if verbose and missing_chunks:
            print(f"[DEBUG] Still missing chunks: {missing_chunks}")


def assemble_file(file_id, app_state, sock):
    transfer = app_state.file_transfers[file_id]
    filename = transfer["filename"]
    chunks = transfer["chunks"]
    total_chunks = transfer["total_chunks"]

    save_dir = "received_files"
    if globals.verbose:
        print(f"[DEBUG] Checking if directory '{save_dir}' exists...")
    try:
        os.makedirs(save_dir, exist_ok=True)
        if globals.verbose:
            print(f"[DEBUG] Directory '{save_dir}' is ready.")
    except Exception as e:
        print(f"[ERROR] Could not create directory '{save_dir}': {e}")
        return

    base_name, ext = os.path.splitext(filename)
    filepath = os.path.join(save_dir, filename)
    counter = 1
    while os.path.exists(filepath):
        filepath = os.path.join(save_dir, f"{base_name}_{counter}{ext}")
        counter += 1

    try:
        with open(filepath, "wb") as f:
            for i in range(total_chunks):
                f.write(chunks[i])
        print(f"\n[INFO] File transfer complete. File saved as: {filepath}\n")
    except Exception as e:
        print(f"[ERROR] Failed to write file: {e}")
        return

    send_file_received(sock, app_state.user_id, transfer["from"], file_id)
    del app_state.file_transfers[file_id]


def send_file_received(sock, from_id, to_id, file_id):
    message = {
        "TYPE": "FILE_RECEIVED",
        "FROM": from_id,
        "TO": to_id,
        "FILEID": file_id,
        "STATUS": "COMPLETE",
        "TIMESTAMP": str(int(time.time())),
    }

    if "@" not in to_id or len(to_id.split("@")) < 2:
        print(f"Invalid user ID format for recipient: {to_id}")
        return

    ip = to_id.split("@")[1]
    sock.sendto(build_message(message).encode("utf-8"), (ip, globals.PORT))


def handle_file_received(message, app_state):
    """
    Handler for FILE_RECEIVED message. Called when the sender receives confirmation that the file was received.
    """
    from utils.globals import verbose

    print("[FILE_RECEIVED] Message fields:")
    for key, value in message.items():
        print(f"  {key}: {value}")


def send_file(sock, app_state, to_user_id, filepath, description=""):
    if not os.path.isfile(filepath):
        print("File not found.")
        return

    filesize = os.path.getsize(filepath)
    filetype = "application/octet-stream"  # fallback
    if filepath.endswith((".jpg", ".jpeg")):
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

    # Save file data for later chunk sending after acceptance
    with app_state.lock:
        app_state.pending_file_sends[file_id] = {
            "sock": sock,
            "to_user_id": to_user_id,
            "to_ip": to_ip,
            "data": data,
            "token": token,
            "filesize": filesize,
            "filepath": filepath,
        }

    print(f"[SENT FILE OFFER] {filepath} ({filesize} bytes) to {to_user_id}")
    print(f"Waiting for FILE_ACCEPTED to send chunks...")


def send_file_chunks_thread(send_info, app_state, file_id, to_user_id):
    """
    Thread function to send file chunks without blocking the main message loop
    """
    sock = send_info["sock"]
    to_ip = send_info["to_ip"]
    data = send_info["data"]
    token = send_info["token"]
    filesize = send_info["filesize"]

    chunk_size = globals.CHUNK_SIZE
    total_chunks = (len(data) + chunk_size - 1) // chunk_size

    print(f"[SENDING CHUNKS] for file_id={file_id} to {to_user_id}")

    for i in range(total_chunks):
        chunk_data = data[i * chunk_size : (i + 1) * chunk_size]
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
        if globals.verbose:
            print(f"\n[SEND >]")
            print(f"Message Type : FILE_CHUNK")
            print(f"Timestamp    : {int(time.time())}")
            print(f"From         : {app_state.user_id}")
            print(f"To           : {to_user_id}")
            print(f"To IP        : {to_ip}")
            print(f"File Name    : {send_info['filepath']}")
            print(f"File ID      : {file_id}")
            print(f"Chunk        : {i + 1}/{total_chunks}")
            print(f"Chunk Size   : {len(chunk_data)} bytes")
            print(f"Status       : SENT\n")
        send_with_ack(sock, chunk_msg, app_state, to_ip)

        # Add small delay between chunks to prevent overwhelming the receiver
        time.sleep(0.2)

    print(f"[SENT FILE] {send_info['filepath']} ({filesize} bytes) to {to_user_id}")

    # Remove from pending sends after done
    with app_state.lock:
        if file_id in app_state.pending_file_sends:
            del app_state.pending_file_sends[file_id]


def handle_file_accepted(message, app_state):
    file_id = message.get("FILEID")
    from_id = message.get("FROM")
    if file_id is None or from_id is None:
        return

    with app_state.lock:
        if file_id not in app_state.pending_file_sends:
            print(f"[WARN] Received FILE_ACCEPTED for unknown file_id={file_id}")
            return

        send_info = app_state.pending_file_sends[
            file_id
        ].copy()  # Copy to avoid thread conflicts

    # Start chunk sending in a separate thread
    thread = threading.Thread(
        target=send_file_chunks_thread,
        args=(send_info, app_state, file_id, from_id),
        daemon=True,
    )
    thread.start()
    print(f"[INFO] Started file chunk sending thread for file_id={file_id}")
