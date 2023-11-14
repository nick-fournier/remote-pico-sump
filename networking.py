import network
import time
from env import SSID, PASSWORD


def connect_to_network():
    
    # Connect to the network
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid=SSID, key=PASSWORD)    
    
    # Wait for connect or fail
    wait = 10
    while wait > 0:
        if wlan.status() < 0 or wlan.status() >= 3:
            break
        wait -= 1
        print('waiting for connection...')
        time.sleep(2)
    
    # Handle connection error
    if wlan.status() != 3:
        raise RuntimeError('wifi connection failed')
    else:
        print('connected')
        
        ip = wlan.ifconfig()[0]
        print('IP: ', ip)
        
    return(ip)