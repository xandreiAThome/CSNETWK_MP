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


def parse_token(token: str) -> dict:
    try:
        user_id, timestamp_ttl, scope = token.split("|")
        timestamp_ttl = float(timestamp_ttl)
    except ValueError as e:
        # ValueError covers both split() unpacking errors and float() conversion errors
        raise ValueError(f"Invalid token format: {token}") from e

    return {"USER_ID": user_id, "TIMESTAMP_TTL": timestamp_ttl, "SCOPE": scope}
