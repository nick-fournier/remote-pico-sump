import time
import ntptime

UTC_OFFSET = -8 # Pacific Standard Time (PST)
ntptime.host = "0.us.pool.ntp.org"

def get_datetime_string():
    # Get the current time
    now = time.localtime(time.time() + UTC_OFFSET * 3600)
    
    # Convert to a string
    date_string = f"{now[1]}/{now[2]}/{now[0]} {now[3]:02d}:{now[4]:02d}:{now[5]:02d}"

    return date_string

def sync_time():
    # Set the time
    try:
        print("Local time before synchronization: %s" %get_datetime_string())
        
        #make sure to have internet connection
        ntptime.settime()

        print("Local time after synchronization: %s" %get_datetime_string())
        
    except:
        print("Error syncing time")