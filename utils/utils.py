def build_message(data: dict) -> str:
    """ convert dict to key:value string with terminator """
    return '\n'.join(f"{k}: {v}" for k, v in data.items()) + "\n\n"

def parse_message(raw: str) -> dict:
    """ Parse key:value string format to dict """
    lines = raw.strip().split('\n')
    result = {}
    for line in lines:
        if ': ' in line:
            key, value = line.split(': ', 1)
            result[key.strip()] = value.strip()
    return result