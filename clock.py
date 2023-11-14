import time
import ntptime
from machine import RTC

UTC_OFFSET = -8 # Pacific Standard Time (PST)

def get_datetime_string():

    # (tm_year, tm_mon, tm_mday, tm_hour, tm_min, tm_sec, tm_wday, tm_yday, tm_isdst)
    # (0      , 1     , 2      , 3      , 4     , 5     , 6      , 7      , 8)
    # now = time.localtime()
    now = time.localtime(time.time() + UTC_OFFSET * 3600)

    date_string = f"{now[1]}/{now[2]}/{now[0]} {now[3]:02d}:{now[4]:02d}:{now[5]:02d}"

    return date_string

def sync_time():
    # Set the time
    ntptime.host = "0.us.pool.ntp.org"

    try:
        print("Local time before synchronization: %s" %get_datetime_string())
        
        #make sure to have internet connection
        ntptime.settime()

        print("Local time after synchronization: %s" %get_datetime_string())
        
    except:
        print("Error syncing time")