import machine
from machine import Pin
import utime

# Temperature Sensor
sensor_temp = machine.ADC(4)
conversion_factor = 3.3 / (65535)

# Distance Sensor
trigger = Pin(4, Pin.OUT)
echo = Pin(5, Pin.IN)

 
def get_temperature():
    
    temperature_value = sensor_temp.read_u16() * conversion_factor 
    temperature_Celcius = 27 - (temperature_value - 0.706)/0.00172169/ 8 
    utime.sleep(2)
    
    print("The temperature is ", temperature_Celcius, "degrees Celsius")
    
    return temperature_Celcius

def get_distance():
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
    print("The distance from object is ", distance, "cm")
    
    return distance
   