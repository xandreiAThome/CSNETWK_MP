# globals.py
PORT = 50999
BROADCAST_INTERVAL = 1
MASK = "255.255.255.0"
TTL = 60
POST_TTL = 3600  # since for some reason POST TTL is strictly 3600 but specs hint that it's changeable at runtime?
verbose = False
broadcast_verbose = False
induce_loss = False
loss_rate = 0.3 # arbitrary chance to drop packets
