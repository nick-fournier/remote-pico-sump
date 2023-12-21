import asyncio
import logging
from utils.clock import sync_time
from sensor import PicoSumpSensor
from microdot.microdot import Response
from microdot.microdot_asyncio import Microdot
from utils.connect import connect_to_network
from rotating_log import RotatingFileHandler

# Logging ------------------------------------------------------------------- #
# Create logger
logger = logging.getLogger('pico-sump')
logger.setLevel(logging.DEBUG)

# Create console handler and set level to debug
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.DEBUG)

# Create file handler and set level to error
# file_handler = logging.FileHandler("error.log", mode="w")
file_handler = RotatingFileHandler("logfile.log", maxBytes=10000, backupCount=0)
file_handler.setLevel(logging.DEBUG)

# Create a formatter
formatter = logging.Formatter("%(name)s - %(levelname)s - %(message)s")

# Add formatter to the handlers
stream_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

# Add handlers to logger
logger.addHandler(stream_handler)
logger.addHandler(file_handler)

# Server -------------------------------------------------------------------- #
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
    await SumpSensor.read_sensors(loop=False)
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


@server.route('/log', methods=['GET'])
async def log(request):
    def log_generator():
        with open('logfile.log', 'r') as f:
            for line in f:
                yield line + '<br>\n'
        
    return log_generator()


@server.route('/settings', methods=['POST', 'GET'])
async def setdepth(request):
    
    if request.method == 'GET':
        return SumpSensor.get_settings(), 200
    
    elif request.method == 'POST':
        validated = SumpSensor.get_settings()
        types = SumpSensor.types
        
        update_msg = 'Updated setings: '
        # Check for valid request, update validated dict
        for f in types.keys():        
            # Attempt to convert to correct type
            try:
                if request.form.get(f) is None:
                    raise ValueError                        
                validated[f] = types[f](request.form.get(f))
                update_msg += f'{f}={validated[f]}, '
                
            except:
                msg = f'Invalid request, field {f} is not of type {types[f]}. Settings not updated.'
                logger.error(msg)
                return msg, 400
            
        logger.info(update_msg)
            
        # Update the sensor settings
        await SumpSensor.update_settings(**request.form)
        
        msg = f"Succesfully updated settings."
        return msg, 200
    else:
        return 'Invalid request method', 400

@server.route('/data', methods = ['GET'])
async def api_all(request):    

    logger.info('Client requested data')
    
    return SumpSensor.get_current_data()


@server.route('/data/<from_timestamp>', methods = ['GET'])
async def api(request, from_timestamp):
    
    from_timestamp = request.args.get('from_timestamp')
    data = SumpSensor.get_current_data(from_timestamp)
    
    logger.info('Client requested data')
    
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
    
    logger.info('Setting up webserver...')
    
    await asyncio.gather(sensor_task, server_task)


# Run the webserver synchronously ------------------------------------------- #
try:
    asyncio.run(main())
    
finally:
    asyncio.new_event_loop()