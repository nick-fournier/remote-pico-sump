import gc
import asyncio
import logging
from machine import Pin, ADC
from database import Database
from utils import clock#, statistics
import utils.connect as connection
import utime
import ujson


# Settings ------------------------------------------------------------------ #
gc.threshold(gc.mem_free() // 4 + gc.mem_alloc())

# Temperature Sensor
sensor_temp = ADC(4)
conversion = 3.4 / 65535

# Distance Sensor
trigger = Pin(0, Pin.OUT)
echo = Pin(1, Pin.IN)

# logging
logger = logging.getLogger('pico-sump')

# Webserver ----------------------------------------------------------------- #
class PicoSumpSensor:
    
    # Set values
    sump_id = "Unknown" # Sump ID
    alarm_level = 0     # Target water level    
    pit_depth = 0       # User set reference depth if different from max measured.
    heartbeat = 5       # Seconds between readings
    log_rate = 1 * 60   # Seconds between log entries
    db_logging = True   # Toggle database logging on/off

    # Current values
    timestamp = None    # Current timestamp
    distance = 0        # Current distance
    water_level = 0     # Current water level (pit_depth - distance)
    
    # Statistics
    threshold = 999     # Threshold for triggering data log, in cm

    # Sensor data
    stack = []          # List of tuples of (timestamp, distance) to analyze from
    
    # Main program requires about 185kb of memory
    # This leaves about 80kb for the stack minus whatever is used by momemtary web requests
    # 1 hour of data or 500 readings, whichever is less
    max_stacklength = min(3600 / heartbeat, 500)
    
    # Specify the types of the settings to be validated
    types = {
        'sump_id': str,
        'pit_depth': float,
        'alarm_level': float,
        'heartbeat': int,
        'log_rate': int,
        'db_toggle': bool,
        'threshold': float,
        }

    
    def __init__(self, netinfo) -> None:
        self.netinfo = netinfo
    
        # Load the config file
        try:
            with open('saved_settings.json', 'r') as f:
                self.set_values(**ujson.loads(f.read()))
                
        except:    
            # No config file found, create one from default settings
            settings = {
                'sump_id': self.sump_id,
                'alarm_level': self.alarm_level,
                'pit_depth': self.pit_depth,
                'heartbeat': self.heartbeat,
                'log_rate': self.log_rate,
                'db_logging': self.db_logging,
                'threshold': self.threshold
            }
            with open('saved_settings.json', 'w') as f:
                f.write(ujson.dumps(settings))
        
    @staticmethod
    def get_adc_temperature(verbose = False):
    
        adc_volt = sensor_temp.read_u16() * conversion
        temperature_celcius = 27 - (adc_volt - 0.706) / 0.001721
        
        if verbose == True:
            logger.info("The temperature is %s degrees Celsius", temperature_celcius)
        
        return temperature_celcius
    
    @staticmethod
    def get_distance(verbose = False):
        
        try:
            trigger.low()
        
            utime.sleep_us(2)
            trigger.high()
        
            utime.sleep_us(5)
            trigger.low()
        
            signaloff = 0
            signalon = 0
        
            while echo.value() == 0:
                signaloff = utime.ticks_us()
            
            while echo.value() == 1:
                signalon = utime.ticks_us()
                
            timepassed = signalon - signaloff
            distance = (timepassed * 0.0343) / 2
        except:
            distance = -999
        
        if verbose == True:
            logger.info("The distance from object is %s cm", distance)
        
        return distance
    
    def set_values(self, **kwargs):
        msg = "Updated settings: "
        # Validate date types
        for key, value in kwargs.items():
            if key in self.types:
                value = self.types[key](value)

            setattr(self, key, value)
            
            msg += f"{key}={value}, "
   
    def get_current_data(self, from_timestamp = None, stream = True):  
        
        # If given a timestamp, convert to datetime object
        # and return only data after that timestamp     
        if from_timestamp:
            from_time = clock.string_to_datetime(from_timestamp)
        else:
            from_time = 0
            
        # If streaming, create a generator to stream the data
        if stream:
            def readings_generator():
                for t, d in self.stack:
                    if t > from_time:
                        timestamp = clock.datetime_to_string(t)
                        yield f"[{timestamp}, {d}]" + "\n"
                        
            return readings_generator()
        
        # If not streaming, return the data stack as a list
        else:
            readings = []
            for t, d in self.stack:
                if t > from_time:
                    timestamp = clock.datetime_to_string(t)
                    readings.append((timestamp, d))
                    
            return readings
            
    def get_settings(self):
        return {
            'sump_id': self.sump_id,
            'pit_depth': self.pit_depth,
            'alarm_level': self.alarm_level,
            'heartbeat': self.heartbeat,
            'log_rate': self.log_rate,
            'threshold': self.threshold,
        }
        
    def update_stack(self):
        # Add to the web data stack
        self.stack.append((self.timestamp, self.distance))
        stacklength = len(self.stack)
        
        # Fixed length stack -- pop off the oldest value if too long
        if stacklength > self.max_stacklength:
            self.stack.pop(0)
            
        return
    
    async def update_settings(self, **settings):
        
        settings_out = self.get_settings()
        
        # Update the settings dictionary
        for key, value in settings.items():
            setattr(self, key, value)
            settings_out[key] = value
        
        # Save the settings to a file
        with open('saved_settings.json', 'w') as f:
            f.write(ujson.dumps(settings_out))
            
        # Update the local settings
        self.set_values(**settings)
        
        # Update the database
        Database.update_settings(
            sump_id=self.sump_id, 
            pit_depth=self.pit_depth,
            alarm_level=self.alarm_level
        )

    def reset(self):
        # Remove all but latest reading from stack
        self.stack = []
        gc.collect()
    
    async def read_sensors(self, loop = True):
        iter = 0
        
        while True:
            
            # Check for network connection
            connection.check_network()
            
            # Get temp reading & convert to Fahrenheit            
            self.distance = self.get_distance()
            self.timestamp = clock.get_datetime()
            self.water_level = self.pit_depth - self.distance
            
            change = self.distance - self.stack[-1][1] if self.stack else 0
            
            # Print to console
            mem_free = 100 * (1 - (gc.mem_free() / 1024 / 264)) # type: ignore
            timestamp_str = clock.datetime_to_string(self.timestamp)
            
            msg = [  
                f'{timestamp_str}',
                f'ID: {self.sump_id},',
                f'Distance: {self.distance:.2f} cm,',
                f'Memory use: {mem_free:.0f}%',
                f'IP: {self.netinfo["ip"]}',
            ]
            
            if not loop:
                msg.append('Single reading request.')
            
            logger.info(' '.join(msg))
            
            # Update the data stack
            self.update_stack()
            
            # Log to database if change > threshold
            if change > self.threshold:
                logger.info(f"Detected change > {self.threshold} cm. Logging to database.")
            
            # Log data to database if true
            if change > self.threshold or iter * self.heartbeat >= self.log_rate:  
                timestamp_str = clock.datetime_to_string(self.timestamp)
                
                await Database.log_data(
                    sump_id=self.sump_id,
                    timestamp=timestamp_str,
                    distance=self.distance
                )
                iter = 0
            
            gc.collect()
            
            # If single reading requested, return
            if not loop:
                return
            
            await asyncio.sleep(self.heartbeat)
            iter += 1
