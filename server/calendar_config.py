"""
Calendar configuration management
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def load_calendar_config():
    """Load calendar configuration from environment variables"""
    calendars = {}
    
    i = 1
    while True:
        cal_id = os.getenv(f'CALENDAR_{i}_ID')
        if not cal_id:
            break
        
        symbol = os.getenv(f'CALENDAR_{i}_SYMBOL', '●')
        name = os.getenv(f'CALENDAR_{i}_NAME', f'Calendar {i}')
        
        calendars[cal_id] = {
            'symbol': symbol,
            'name': name
        }
        i += 1
    
    # Fallback to original EMAIL if no calendars configured
    if not calendars:
        email = os.getenv('EMAIL')
        if email:
            calendars[email] = {
                'symbol': '●',
                'name': 'Primary'
            }
    
    return calendars