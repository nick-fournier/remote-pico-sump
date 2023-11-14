import socket
import json
import time
from clock import get_datetime_string
from reading import get_temperature
from reading import get_distance
from webpage import webpage

def serve(connection):
    while True:
        client = connection.accept()[0]
        request = client.recv(1024)
        request = str(request)
        try:
            request = request.split()[1]
        except IndexError:
            pass
        
        # Get the current time     
        date_string = get_datetime_string()
        
        readings = {
            'timestamp': date_string,
            'temperature': get_distance(),
            'distance': get_temperature()
        }      
        
        verbose_readings = {
            '/temperature?': f'The temperature is {readings["temperature"]: .2f} degrees Celsius',
            '/distance?': f'The distance is {readings["distance"]: .2f} cm'
        }
        
            
        if 'json' in request:
            html = json.dumps(readings)
            html = 'HTTP/1.0 200 OK\n\n' + html
                      
        elif request in verbose_readings.keys():
            value = verbose_readings[request]
            html=webpage(value)
            
        else:            
            value = '<br>'.join(verbose_readings.values())
            value += f'<br> at {readings["timestamp"]}'        
            
            html=webpage(value)
        
        client.send(html)
        client.close()
 
def open_socket(ip):
    # Open a socket
    address = (ip, 80)
    connection = socket.socket()
    connection.bind(address)
    connection.listen(1)
    print(connection)
    return(connection)