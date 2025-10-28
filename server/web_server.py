#!/usr/bin/env python3
"""
Web server to serve calendar images for ESP32 eink display
Automatically regenerates calendar at midnight
"""

import os
import schedule
import time
import threading
from datetime import datetime
from flask import Flask, send_file, jsonify, request
import logging

# Import our modular components
from main import generate_illustrated_calendar
from llm_handler import llm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration - CHANGED TO BMP
CALENDAR_IMAGE_PATH = "output/illustrated_calendar.bmp"
STATIC_DIR = "output"
HOST = "0.0.0.0"
PORT = 8000

# Ensure output directory exists
os.makedirs(STATIC_DIR, exist_ok=True)

def generate_new_calendar():
    """Generate a new calendar image"""
    try:
        logger.info("Starting calendar generation...")
        generate_illustrated_calendar(filename=CALENDAR_IMAGE_PATH)
        logger.info(f"Calendar generated successfully: {CALENDAR_IMAGE_PATH}")
        return True
    except Exception as e:
        logger.error(f"Error generating calendar: {e}")
        return False

def scheduled_calendar_generation():
    """Function to run scheduled calendar generation"""
    logger.info("Midnight calendar generation triggered")
    success = generate_new_calendar()
    if success:
        logger.info("Scheduled calendar generation completed successfully")
    else:
        logger.error("Scheduled calendar generation failed")

@app.route('/calendar.png')  # Keep URL same for ESP32 compatibility
def serve_calendar():
    """Serve the current calendar image (BMP format)"""
    try:
        if not os.path.exists(CALENDAR_IMAGE_PATH):
            logger.warning("Calendar image not found, generating new one...")
            generate_new_calendar()
        
        if os.path.exists(CALENDAR_IMAGE_PATH):
            # Add headers for ESP32 compatibility - CHANGED MIMETYPE TO BMP
            response = send_file(
                CALENDAR_IMAGE_PATH, 
                mimetype='image/bmp',  # Changed from image/png to image/bmp
                as_attachment=False,
                download_name='calendar.bmp'  # Changed from .png to .bmp
            )
            # Add cache control headers
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            return response
        else:
            return "Calendar image not available", 404
            
    except Exception as e:
        logger.error(f"Error serving calendar: {e}")
        return f"Error serving calendar: {str(e)}", 500

@app.route('/calendar')
def serve_calendar_alt():
    """Alternative endpoint for calendar image"""
    return serve_calendar()

@app.route('/status')
def status():
    """Status endpoint for health checks"""
    calendar_exists = os.path.exists(CALENDAR_IMAGE_PATH)
    file_age = None
    
    if calendar_exists:
        file_stat = os.stat(CALENDAR_IMAGE_PATH)
        file_age = time.time() - file_stat.st_mtime
    
    return jsonify({
        "status": "running",
        "calendar_exists": calendar_exists,
        "calendar_path": CALENDAR_IMAGE_PATH,
        "file_age_seconds": file_age,
        "last_modified": datetime.fromtimestamp(os.stat(CALENDAR_IMAGE_PATH).st_mtime).isoformat() if calendar_exists else None,
        "server_time": datetime.now().isoformat()
    })

@app.route('/refresh')
def refresh_calendar():
    """Manually trigger calendar refresh"""
    client_ip = request.remote_addr
    logger.info(f"Manual refresh requested from {client_ip}")
    
    success = generate_new_calendar()
    
    if success:
        return jsonify({
            "status": "success",
            "message": "Calendar refreshed successfully",
            "timestamp": datetime.now().isoformat()
        })
    else:
        return jsonify({
            "status": "error",
            "message": "Failed to refresh calendar",
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/info')
def info():
    """ESP32-friendly endpoint with basic info"""
    calendar_exists = os.path.exists(CALENDAR_IMAGE_PATH)
    return jsonify({
        "calendar_available": calendar_exists,
        "calendar_url": "/calendar.png",  # URL stays same for ESP32
        "last_update": datetime.fromtimestamp(os.stat(CALENDAR_IMAGE_PATH).st_mtime).isoformat() if calendar_exists else None
    })

@app.route('/')
def index():
    """Simple index page"""
    calendar_exists = os.path.exists(CALENDAR_IMAGE_PATH)
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Calendar Server</title>
        <meta charset="utf-8">
    </head>
    <body>
        <h1>Calendar Server (BMP Format)</h1>
        <p>Server time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p>Calendar status: {'Available' if calendar_exists else 'Not available'}</p>
        <p>Format: BMP (uncompressed, ESP32-compatible)</p>
        
        {'<p><a href="/calendar.png">View Calendar Image</a></p>' if calendar_exists else ''}
        
        <h2>Endpoints:</h2>
        <ul>
            <li><a href="/calendar.png">/calendar.png</a> - Calendar image (BMP format for ESP32)</li>
            <li><a href="/status">/status</a> - Server status (JSON)</li>
            <li><a href="/refresh">/refresh</a> - Manual refresh</li>
            <li><a href="/info">/info</a> - ESP32-friendly info</li>
            <li><a href="/debug/llm">/debug/llm</a> - Test LLM function</li>
            <li><a href="/debug/env">/debug/env</a> - Check environment variables</li>
        </ul>
        
        <p><button onclick="location.href='/refresh'">Refresh Calendar Now</button></p>
        
        {'<h2>Current Calendar:</h2><img src="/calendar.png" style="max-width: 100%; border: 1px solid #ccc;">' if calendar_exists else ''}
    </body>
    </html>
    """
    return html

@app.route('/debug/llm')
def debug_llm():
    """Debug endpoint to test LLM function"""
    try:
        logger.info("Testing LLM function via debug endpoint")
        result = llm()
        
        return jsonify({
            "status": "success",
            "llm_result": result,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"LLM debug error: {e}")
        return jsonify({
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__,
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/debug/env')
def debug_env():
    """Debug endpoint to check environment variables (safe)"""
    env_vars = {}
    
    # Check calendar configuration
    i = 1
    while os.getenv(f'CALENDAR_{i}_ID'):
        env_vars[f'CALENDAR_{i}_ID'] = os.getenv(f'CALENDAR_{i}_ID')
        env_vars[f'CALENDAR_{i}_SYMBOL'] = os.getenv(f'CALENDAR_{i}_SYMBOL', 'NOT_SET')
        env_vars[f'CALENDAR_{i}_NAME'] = os.getenv(f'CALENDAR_{i}_NAME', 'NOT_SET')
        i += 1
    
    # Check API keys (masked for security)
    for key in ['OPENROUTER_API_KEY', 'IMAGEROUTER_API_KEY']:
        value = os.getenv(key)
        if value:
            env_vars[key] = f"{value[:10]}...{value[-4:] if len(value) > 4 else 'SHORT'}"
        else:
            env_vars[key] = "NOT_SET"
    
    # Check other important vars
    env_vars['GOOGLE_CREDENTIALS_PATH'] = os.getenv('GOOGLE_CREDENTIALS_PATH', 'NOT_SET')
    env_vars['SECONDARY_ILLUSTRATION'] = os.getenv('SECONDARY_ILLUSTRATION', 'NOT_SET')
    
    return jsonify({
        "environment_variables": env_vars,
        "timestamp": datetime.now().isoformat()
    })

def run_scheduler():
    """Run the scheduler in a separate thread"""
    logger.info("Starting scheduler thread...")
    
    # Schedule calendar generation at midnight
    schedule.every().day.at("00:00").do(scheduled_calendar_generation)
    
    # For testing - you can uncomment this to generate every minute
    # schedule.every(1).minutes.do(scheduled_calendar_generation)
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

def initialize_calendar():
    """Generate initial calendar if it doesn't exist"""
    if not os.path.exists(CALENDAR_IMAGE_PATH):
        logger.info("No existing calendar found, generating initial calendar...")
        generate_new_calendar()
    else:
        logger.info("Existing calendar found, using current version")

if __name__ == "__main__":
    logger.info("Starting Calendar Server...")
    
    # Generate initial calendar
    initialize_calendar()
    
    # Start scheduler in background thread
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    logger.info(f"Calendar server starting on http://{HOST}:{PORT}")
    logger.info(f"ESP32 can fetch calendar from: http://your-server-ip:{PORT}/calendar.png")
    
    # Start Flask server
    app.run(host=HOST, port=PORT, debug=False)