import gc
import asyncio
from utils.clock import sync_time
from sensor import PicoSumpSensor
from microdot.microdot import Response
from microdot.microdot_asyncio import Microdot
from utils.connect import connect_to_network


gc.collect()
# Server
server = Microdot()
Response.default_content_type = 'text/html'


with open('./static/index.html', 'r') as f:
    html_string = f.read()
    
# with open('style.css', 'r') as f:
#     css_string = f.read()

with open('static/script.js', 'r') as f:
    js_string = f.read()

# Webserver routes
@server.route('/')
async def index(request):
    # serve the index.html file with javascript
    return html_string


# Static CSS/JSS
@server.route("/static/<path:path>")
def static(request, path):
    if ".." in path:
        # directory traversal is not allowed
        return "Not found", 404
    return js_string

@server.route('/reset', methods=['POST'])
async def reset(request):
    if request.method != 'POST':         
        return 'This is a POST URL only.', 400
    
    SumpSensor.reset()
    
    return 'Sensor cache reset', 200


@server.route('/settings', methods=['POST', 'GET'])
async def setdepth(request):
    
    if request.method == 'GET':
        return SumpSensor.get_settings(), 200
    
    elif request.method == 'POST':
        validated = SumpSensor.get_settings()
        types = SumpSensor.types
        # Check for valid request, update validated dict
        for f in types.keys():        
            # Attempt to convert to correct type
            try:
                if request.form.get(f) is None:
                    raise ValueError                        
                validated[f] = types[f](request.form.get(f))
                
            except:
                msg = f'Invalid request, field {f} is not of type {types[f]}. Settings not updated.'
                print(msg)
                return msg, 400
            
        
        msg = f"Updating settings for sump {request.form.get('sump_id')}, "
        msg += f"pit depth {request.form.get('pit_depth')}, "
        msg += f"alarm level {request.form.get('alarm_level')}"
        print(msg)
            
        # Update the sensor settings
        SumpSensor.update_settings(**request.form)
        
        msg = f"Succesfully updated settings."
        return msg, 200
    else:
        return 'Invalid request method', 400

@server.route('/data', methods = ['GET'])
async def api_all(request):    
    print('Client requested data')
    return SumpSensor.get_current_data()


@server.route('/data/<from_timestamp>', methods = ['GET'])
async def api(request, from_timestamp):
    
    from_timestamp = request.args.get('from_timestamp')
    data = SumpSensor.get_current_data(from_timestamp)
    
    print('Client requested data')
    return data


async def main():
    
    netinfo = connect_to_network()
    
    # Instantiate the webserver class
    global SumpSensor
    SumpSensor = PicoSumpSensor(netinfo)
            
    # Sync the clock
    sync_time()
    
    # Start the sensor reading task
    sensor_task = asyncio.create_task(SumpSensor.read_sensors())
    server_task = asyncio.create_task(server.start_server("0.0.0.0", port=80))
    
    print('Setting up webserver...')
    
    await asyncio.gather(sensor_task, server_task)


# --------------------------------------------------------------------------- #

# Run the webserver asynchronously
try:
    asyncio.run(main())
    
finally:
    asyncio.new_event_loop()