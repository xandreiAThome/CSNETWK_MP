import socket
import sys

def main(host_addr, host_port, dest_addr, dest_port):
   print("hi")

if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: python app.py <display_name> <user_name> <avatar_source_file>")
        print("Example: python app.py 'Juan Tamad' juan juan_tamad.png")
        sys.exit(1)
    
    display_name = sys.argv[1]
    user_name = int(sys.argv[2])
    avatar_source_file = sys.argv[3]
    main(display_name, user_name, avatar_source_file)
    