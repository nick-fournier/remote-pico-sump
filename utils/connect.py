import network
import time
import ubinascii
import ujson
from env import SSID, PASSWORD

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

def connect_to_network():
    
    print('Connecting to Network...')
    
    if wlan.isconnected():
        print(f'Already connected to network as {wlan.ifconfig()[0]}')
        ip = wlan.ifconfig()[0]
        mac = ubinascii.hexlify(wlan.config('mac'),':').decode()
        
        return {'ip': ip, 'mac': mac}
        
    # Connect to the network
    wlan.active(True)
    wlan.config(pm = 0xa11140)  # Disable power-save mode
    wlan.connect(ssid=SSID, key=PASSWORD)
    mac = ubinascii.hexlify(wlan.config('mac'),':').decode()
    
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
        print('wifi connection failed')
        raise RuntimeError('wifi connection failed')
    
    else:            
        ip = wlan.ifconfig()[0]
        print('Connected')
                
        time.sleep(2)
        print('IP: ', ip, 'MAC: ', mac)
    
    return {'ip': ip, 'mac': mac}
