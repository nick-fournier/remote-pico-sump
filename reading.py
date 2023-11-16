import machine
from machine import Pin
import utime

# Temperature Sensor
sensor_temp = machine.ADC(4)
conversion = 3.4 / 65535

# Distance Sensor
trigger = Pin(4, Pin.OUT)
echo = Pin(5, Pin.IN)

 
def get_temperature(verbose = False):
    
    adc_volt = sensor_temp.read_u16() * conversion
    temperature_celcius = 27 - (adc_volt - 0.706) / 0.001721
    
    if verbose == True:
        print("The temperature is ", temperature_celcius, "degrees Celsius")
    
    return temperature_celcius

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
   