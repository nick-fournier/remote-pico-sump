import network
import time
import ubinascii
import ujson
import logging
from env import SSID, PASSWORD

logger = logging.getLogger('pico-sump')

try:
    with open('settings.json', 'r') as f:
        settings = ujson.loads(f.read())
        network.hostname(settings['sump_id'])
    del settings
    
except:
    network.hostname('Uknown Sump')

# Wifi connection
# network.hostname(SETTINGS['SUMP_ID'])
wlan = network.WLAN(network.STA_IF)

def get_netinfo():
    return {'ip': wlan.ifconfig()[0], 'mac': ubinascii.hexlify(wlan.config('mac'),':').decode()}

def check_network():
    # Check if connected to network
    if wlan.isconnected():
        return
    else:
        return connect_to_network()
        

def connect_to_network():
    # Connect to the network
    logger.info('Connecting to Network...')
    
    if wlan.isconnected():
        logger.info(f'Already connected to network as {wlan.ifconfig()[0]}')        
        return
        
    # Connect to the network
    wlan.active(True)
    wlan.config(pm = 0xa11140)  # Disable power-save mode
    wlan.connect(ssid=SSID, key=PASSWORD)
    
    # Wait for connect or fail
    wait = 10
    while wait > 0:
        if wlan.status() < 0 or wlan.status() >= 3:
            break
        wait -= 1
        logger.info('waiting for connection...')
        time.sleep(2)

    # Handle connection error
    if wlan.status() != 3:
        raise RuntimeError('wifi connection failed')
    
    else:            
        ip = wlan.ifconfig()[0]
        logger.info('Connected to network as %s', ip)
                
        time.sleep(2)
    
    return
