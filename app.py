import socket
import sys
from net_comms import get_local_ip
from utils import *

PORT = 50999

def main(display_name, user_name, avatar_source_file=None):
   print(get_local_ip())
   print(build_message({"lol": 123}))
   print(parse_message("lol: make me"))

if __name__ == "__main__":
    if len(sys.argv) < 3 or len(sys.argv) > 4:
        print("Usage: python app.py <display_name> <user_name> [avatar_source_file]")
        print("Example: python app.py 'Juan Tamad' juan")
        print("Example: python app.py 'Juan Tamad' juan juan_tamad.png")
        sys.exit(1)
    
    display_name = sys.argv[1]
    user_name = sys.argv[2]
    avatar_source_file = sys.argv[3] if len(sys.argv) == 4 else None
    main(display_name, user_name, avatar_source_file)
    