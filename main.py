import asyncio
import logging
import utils.connect as connection
from logging.handlers import MemoryHandler
from utils.clock import sync_time
from sensor import PicoSumpSensor
from microdot import Response
from microdot.microdot_asyncio import Microdot

# Logging ------------------------------------------------------------------- #
# Create logger
logger = logging.getLogger('pico-sump')
logger.setLevel(logging.DEBUG)

# Create console handler and set level to debug
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.DEBUG)

# Create memory handler and set capacity to 100 entries
memory_handler = MemoryHandler(capacity=100, flushLevel=logging.ERROR)

# Create a formatter
formatter = logging.Formatter("%(name)s - %(levelname)s - %(message)s")

# Add formatter to the handlers
stream_handler.setFormatter(formatter)
memory_handler.setFormatter(formatter)

# Add handlers to logger
logger.addHandler(stream_handler)
logger.addHandler(memory_handler)

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
    
    # output = ''
    # for record in memory_handler.buffer:
    #     output += formatter.format(record) + '\n'
    
    # return output, 200
    
    def log_generator():
        for log_msg in memory_handler.buffer:
            yield log_msg + '\n <br>'
        
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
    
    connection.check_network()
    
    netinfo = connection.get_netinfo()
        
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