import base64


def build_message(data: dict) -> str:
    """convert dict to key:value string with terminator"""
    return "\n".join(f"{k}: {v}" for k, v in data.items()) + "\n\n"


def parse_message(raw: str) -> dict:
    """Parse key:value string format to dict"""
    lines = raw.strip().split("\n")
    result = {}
    for line in lines:
        if ": " in line:
            key, value = line.split(": ", 1)
            result[key.strip()] = value.strip()
    return result


def encode_avatar_data(avatar_text: str) -> str:
    """Encode ASCII art text to base64 for transmission"""
    if not avatar_text:
        return ""
    return base64.b64encode(avatar_text.encode("utf-8")).decode("ascii")


def decode_avatar_data(avatar_base64: str) -> str:
    """Decode base64 avatar data back to ASCII art text"""
    if not avatar_base64:
        return ""
    try:
        return base64.b64decode(avatar_base64.encode("ascii")).decode("utf-8")
    except Exception:
        return ""  # Return empty string if decoding fails


def parse_token(token: str) -> dict:
    try:
        user_id, timestamp_ttl, scope = token.split("|")
        timestamp_ttl = float(timestamp_ttl)
    except ValueError as e:
        # ValueError covers both split() unpacking errors and float() conversion errors
        raise ValueError(f"Invalid token format: {token}") from e

    return {"USER_ID": user_id, "TIMESTAMP_TTL": timestamp_ttl, "SCOPE": scope}


def display_avatar(avatar_data: str):
    """Helper function to properly display ASCII art avatar"""
    if avatar_data:
        # Decode base64 avatar data back to ASCII art
        decoded_avatar = decode_avatar_data(avatar_data)
        if decoded_avatar:
            print("Avatar:")
            print(decoded_avatar)
        else:
            print("Avatar: [Unable to decode]")
    else:
        print("No avatar available")
