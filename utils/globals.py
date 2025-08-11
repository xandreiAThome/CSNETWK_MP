# globals.py
PORT = 50999
BROADCAST_INTERVAL = 1
MASK = "255.255.255.0"
TTL = 60
POST_TTL = 3600  # POST TTL fixed at 3600 unless runtime change allowed
verbose = False
broadcast_verbose = False
CHUNK_SIZE = 256

# Packet loss simulation
induce_loss = False
loss_rate = 0.3  # default 30% drop chance
