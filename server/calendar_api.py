"""
Google Calendar API handling
"""
import os
import datetime
from googleapiclient.discovery import build
from google.oauth2 import service_account
from calendar_config import load_calendar_config

def fetch_calendar_events():
    """Fetches events from multiple Google Calendars for the next 4 days."""
    try:
        # Path to your service account credentials file
        credentials_path = os.getenv('GOOGLE_CREDENTIALS_PATH', 'credentials/kalender.json')
        
        if not os.path.exists(credentials_path):
            print(f"Google credentials file not found at: {credentials_path}")
            return {}
        
        # Create a service account credentials object
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=['https://www.googleapis.com/auth/calendar.readonly']
        )
        
        # Build the Google Calendar API service
        service = build('calendar', 'v3', credentials=credentials)
        
        # Load calendar configuration
        calendar_config = load_calendar_config()
        
        if not calendar_config:
            print("No calendars configured")
            return {}
        
        # Set time_min to today's date at 00:00:00
        today = datetime.date.today()
        time_min = today.isoformat() + 'T00:00:00Z'
        
        # Set time_max to the date 3 days from today (4 days total) at 23:59:59
        future_date = today + datetime.timedelta(days=3)
        time_max = future_date.isoformat() + 'T23:59:59Z'
        
        # Organize events by date
        organized_events = {
            today + datetime.timedelta(days=i): [] for i in range(4)
        }
        
        # Fetch events from each configured calendar
        for calendar_id, config in calendar_config.items():
            try:
                print(f"Fetching events from calendar: {config['name']} ({calendar_id})")
                
                events_result = service.events().list(
                    calendarId=calendar_id,
                    maxResults=20,
                    singleEvents=True,
                    orderBy='startTime',
                    timeMin=time_min,
                    timeMax=time_max,
                    timeZone='Europe/Copenhagen'
                ).execute()
                
                events = events_result.get('items', [])
                
                for event in events:
                    start = event['start'].get('dateTime', event['start'].get('date'))
                    
                    # Check if we have a full datetime or just a date
                    if 'T' in start:
                        # It's a datetime - parse it
                        event_date = datetime.datetime.fromisoformat(start.replace('Z', '+00:00')).date()
                        event_time = datetime.datetime.fromisoformat(start.replace('Z', '+00:00')).strftime("%H:%M")
                    else:
                        # It's just a date
                        event_date = datetime.date.fromisoformat(start)
                        event_time = "All day"
                    
                    # If the event is within our date range, add it to the organized events
                    for date in organized_events.keys():
                        if event_date == date:
                            organized_events[date].append({
                                'time': event_time,
                                'summary': event['summary'],
                                'description': event.get('description', ''),
                                'calendar_symbol': config['symbol'],
                                'calendar_name': config['name'],
                                'calendar_id': calendar_id
                            })
                            
            except Exception as e:
                print(f"Error fetching events from calendar {calendar_id}: {e}")
                continue
        
        # Sort events by time within each day
        for date in organized_events:
            organized_events[date].sort(key=lambda x: (
                x['time'] == "All day",  # All day events last
                x['time'] if x['time'] != "All day" else "23:59"
            ))
        
        return organized_events
        
    except Exception as e:
        print(f"Error fetching calendar events: {e}")
        return {}