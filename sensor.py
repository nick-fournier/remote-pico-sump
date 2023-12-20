import gc
import asyncio
import machine
from machine import Pin
from database import Database
from utils import clock, statistics
import utime
import ujson


# Settings ------------------------------------------------------------------ #
gc.threshold(gc.mem_free() // 4 + gc.mem_alloc())

# Heartbeat rate
heartbeat = 60          # Seconds
log_rate = 15 * 60      # Seconds (15 Minutes), max time between log entries

# Temperature Sensor
sensor_temp = machine.ADC(4)
conversion = 3.4 / 65535

# Distance Sensor
trigger = Pin(0, Pin.OUT)
echo = Pin(1, Pin.IN)

# Webserver ----------------------------------------------------------------- #
class PicoSumpSensor:
    
    # Set values
    sump_id = "Unknown" # Sump ID
    alarm_level = 0   # Target water level    
    pit_depth = 0     # User set reference depth if different from max measured.

    # Current values
    timestamp = None    # Current timestamp
    distance = 0        # Current distance
    water_level = 0     # Current water level (pit_depth - distance)
    
    # Statistics
    stdev = 0           # Standard deviation of distance readings in the stack
    mean = 0            # Mean of distance readings in the stack

    # Sensor data
    stack = []          # List of tuples of (timestamp, distance) to analyze from
    
    # Main program requires about 175kb of memory, leaving about 90kb for the stack
    # 1 hour of data or 500 readings, whichever is less
    max_stacklength = min(3600 / heartbeat, 500)
    
    # Specify the types of the settings to be validated
    types = {'sump_id': str, 'pit_depth': float, 'alarm_level': float}
    
    mem_baseline = None

    
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
                'pit_depth': self.pit_depth
            }
            with open('saved_settings.json', 'w') as f:
                f.write(ujson.dumps(settings))
        
    @staticmethod
    def get_adc_temperature(verbose = False):
    
        adc_volt = sensor_temp.read_u16() * conversion
        temperature_celcius = 27 - (adc_volt - 0.706) / 0.001721
        
        if verbose == True:
            print("The temperature is ", temperature_celcius, "degrees Celsius")
        
        return temperature_celcius
    
    @staticmethod
    def get_distance(verbose = False):
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
        
        if verbose == True:
            print("The distance from object is ", distance, "cm")
        
        return distance
    
    def set_values(self, **kwargs):
        # Validate date types
        for key, value in kwargs.items():
            if key in self.types:
                value = self.types[key](value)
            setattr(self, key, value)
            print(f"Successfuly set {key} to {value}")
   
    def get_current_data(self, from_timestamp = None, stream = True):  
        
        # If given a timestamp, convert to datetime object
        # and return only data after that timestamp     
        if from_timestamp:
            from_time = clock.string_to_datetime(from_timestamp)
        else:
            from_time = 0
        
        # If not streaming, return the data stack as a list
        if not stream:
            readings = []
            for t, d in self.stack:
                if t > from_time:
                    timestamp = clock.datetime_to_string(t)
                    readings.append((timestamp, d))
                    
            return readings
        
        # Create a generator to stream the data
        else:            
            def readings_generator():
                for t, d in self.stack:
                    if t > from_time:
                        timestamp = clock.datetime_to_string(t)
                        yield f"[{timestamp}, {d}]" + "\n"
            
            return readings_generator()
            
    def get_settings(self):
        return {
            'sump_id': self.sump_id,
            'pit_depth': self.pit_depth,
            'alarm_level': self.alarm_level
        }
    
        
    def update_stack(self):
        # Add to the web data stack
        self.stack.append((self.timestamp, self.distance))
        stacklength = len(self.stack)
        
        # Fixed length stack -- pop off the oldest value if too long
        if stacklength > self.max_stacklength:
            self.stack.pop(0)
            
        return
    
    def update_settings(self, **settings):
        
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
        self.stack = []
        gc.collect()
    
    async def read_sensors(self, loop = True):
        iter = 0
        
        while True:
            # Get temp reading & convert to Fahrenheit            
            self.distance = self.get_distance()
            self.timestamp = clock.get_datetime()
            self.water_level = self.pit_depth - self.distance
            
            # Default to current reading if no stack
            mean = self.distance
            stdev = 0
                        
            # Calculate statistics
            distances = [d for _, d in self.stack]
            if len(distances) > 1:
                stdev = statistics.stdev(distances)
                mean = statistics.mean(distances)
                                        
            # If single reading requested, return
            if not loop:
                return
            
            # Print to console
            mem_free = 100 * (1 - (gc.mem_free() / 1024 / 264)) # type: ignore
            timestamp_str = clock.datetime_to_string(self.timestamp)
            
            msg = [  
                f'{timestamp_str}',
                f'ID: {self.sump_id}, ',
                f'Distance: {self.distance:.2f} cm, ',
                f'Memory use: {mem_free:.0f}%'
            ]
            print(' '.join(msg))
            
            # Update the data stack
            self.update_stack()            
            
            # Check if logging interval reached or value exceeds 95% threshold (68-95-99.7 Empirical rule)
            # The logging threshold have sufficient data to avoid premature logging before the std dev is stable.
            stdev_threshold = (
                self.distance > (mean + 2 * stdev) or
                self.distance < (mean - 2 * stdev)
            ) and len(distances) > len(self.stack) * heartbeat >= log_rate
            
            if stdev_threshold:
                print(f"Detected significant change. Logging to database.")
            
            # Log data to database if true
            if stdev_threshold or iter * heartbeat >= log_rate:  
                timestamp_str = clock.datetime_to_string(self.timestamp)
                
                await Database.log_data(
                    sump_id=self.sump_id,
                    timestamp=timestamp_str,
                    distance=self.distance
                )
                iter = 0
            
            gc.collect()
            await asyncio.sleep(heartbeat)
            iter += 1
                
