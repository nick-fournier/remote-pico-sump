import machine
from clock import sync_time
from networking import connect_to_network
from server import open_socket, serve

# Connect to wifi
ip = connect_to_network()

# Sync the clock
sync_time()

# Main loop
try:
    if ip is not None:
        connection=open_socket(ip)
        serve(connection)
except KeyboardInterrupt:
    machine.reset()