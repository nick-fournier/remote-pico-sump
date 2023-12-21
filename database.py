import micropg
import logging
from utils.connect import connect_to_network
from env import PG_HOST, PG_USER, PG_PASSWORD, PG_DATABASE

# Logging
logger = logging.getLogger('pico-sump')

# Connect to the network
connect_to_network()

# Database ------------------------------------------------------------------ #
class DatabaseAPI:
    def __init__(self, host, user, password, database):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        
    def connect(self):        
        conn = micropg.connect(
            host=self.host,
            user=self.user,
            password=self.password,
            database=self.database,
            use_ssl=False
        )
        conn.autocommit = True
        
        self.check_tables(conn)
        
        logger.info(f"Success: connected to database {self.database}")
        
        return conn
        
    def check_connection(self):
        
        logger.info(f"Checking connection to database {self.database}...")
        
        try:
            self.conn.cursor().execute("SELECT 1")
        
        except Exception as e:
            
            logger.warning(f"Connection to database {self.database} lost. Reconnecting...")
            
            self.conn = self.connect()
            
        return self.conn
        
    def check_tables(self, conn):
        # Add unique constraint to sump_id in the sump_settings table
        logger.info(f"Checking database tables...")
        
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS sump_settings (
                    sump_id VARCHAR(255) NOT NULL,
                    pit_depth FLOAT NOT NULL,
                    alarm_level FLOAT NOT NULL,
                    CONSTRAINT Sump_ID UNIQUE (sump_id)
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS sump_readings (
                    sump_id VARCHAR(255) NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    distance FLOAT NOT NULL
                )
                """
            )
            
            logger.info(f"Database tables OK")
            
        except Exception as e:
            
            logger.error(f"Failed to create tables in database {self.database}. {e}")
            
        return
    
        
    def update_settings(self, sump_id, pit_depth, alarm_level):
        try:
            conn = self.check_connection()
            cursor = conn.cursor()
            cmd = (
                f"""
                INSERT INTO sump_settings (sump_id, pit_depth, alarm_level)
                VALUES ('{sump_id}', {pit_depth}, {alarm_level})
                ON CONFLICT (sump_id)
                DO
                UPDATE SET pit_depth = {pit_depth}, alarm_level = {alarm_level}
                """
            )
            cursor.execute(cmd)
            
            logger.info(f"Set settings in database {self.database}")
            
        except Exception as e:
            
            logger.error(f"Failed to set settings in database {self.database}. {e}")
                        
        return
    
    async def log_data(self, sump_id, timestamp, distance):
        try:
            conn = self.check_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO sump_readings(sump_id, timestamp, distance) "
                "VALUES (%s, %s, %s)",
                (sump_id, timestamp, distance)
            )
            
            logger.info(f"Logged data to database {self.database}")
            
        except Exception as e:
            
            logger.error(f"Failed to log data to database {self.database}. {e}")
            
        return

# Instantiate the database class once for global use ------------------------- #
Database = DatabaseAPI(PG_HOST, PG_USER, PG_PASSWORD, PG_DATABASE)