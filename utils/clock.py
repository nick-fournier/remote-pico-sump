import utime
import ntptime

UTC_OFFSET = -8 # Pacific Standard Time (PST)
ntptime.host = "0.us.pool.ntp.org"


def get_datetime():
    # Get the current time
    return utime.time() + UTC_OFFSET * 3600

def datetime_to_string(datetime_seconds):    
    # Convert to a string
    dt = utime.localtime(datetime_seconds)
    date_string = f"{dt[0]}-{dt[1]}-{dt[3]} {dt[3]:02d}:{dt[4]:02d}:{dt[5]:02d} {UTC_OFFSET:+03d}:00"

    return date_string

def get_datetime_string():
    # Get the current time
    now = utime.localtime(utime.time() + UTC_OFFSET * 3600)
    
    # Convert to a string
    return datetime_to_string(now)

def string_to_datetime(datetime_string):    
    # Convert to a datetime object assuming format: "mm/dd/yyyy hh:mm:ss-UTC_OFFSET"
    try:
        strings = datetime_string.split(' ')
        date = strings[0].split('/')
        time = strings[1].split(':')
        # utc = strings[2].split('UTC')[1]
        
        # Make time [year, month, day, hour, minute, second]
        dt = tuple([int(date[2]), int(date[0]), int(date[1]), int(time[0]), int(time[1]), int(time[2]), 1, 1])                
        dt = utime.mktime(dt)
        
    except:
        dt = None
    
    return dt

def sync_time():
    # Set the time
    try:
        print("Local time before synchronization: %s" %get_datetime_string())
        
        #make sure to have internet connection
        ntptime.settime()

        print("Local time after synchronization: %s" %get_datetime_string())
        
    except:
        print("Error syncing time")