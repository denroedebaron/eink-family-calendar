"""
Weather handling and icon generation
"""
import requests
import math

def fetch_weather_forecast(days=4):
    """Fetch weather forecast for the next few days."""
    try:
        # Using Open-Meteo free weather API which doesn't require authentication
        response = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": 55.68,  # Copenhagen latitude
                "longitude": 12.57,  # Copenhagen longitude
                "daily": "temperature_2m_max,temperature_2m_min,weathercode",
                "timezone": "Europe/Copenhagen",
                "forecast_days": days
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            forecast = []
            
            for i in range(days):
                weather_code = data['daily']['weathercode'][i]
                min_temp = round(data['daily']['temperature_2m_min'][i])
                max_temp = round(data['daily']['temperature_2m_max'][i])
                
                forecast.append({
                    'weather_code': weather_code,
                    'min_temp': min_temp,
                    'max_temp': max_temp
                })
            
            return forecast
        else:
            print(f"Error fetching weather: Status code {response.status_code}")
            return None
            
    except Exception as e:
        print(f"Error fetching weather: {e}")
        return None

def create_weather_icon(draw, x, y, weather_code, size=30):
    """Draw a custom weather icon based on the weather code."""
    # Define colors
    sun_color = (255, 204, 0)  # Yellow
    cloud_color = (200, 200, 200)  # Light gray
    rain_color = (68, 114, 196)  # Blue
    snow_color = (255, 255, 255)  # White
    fog_color = (180, 180, 180)  # Gray
    thunder_color = (255, 153, 0)  # Orange
    outline_color = (100, 100, 100)  # Dark gray
    
    center_x = x + size // 2
    center_y = y + size // 2
    radius = size // 3
    
    # Clear sky (0) or Mainly clear (1)
    if weather_code in [0, 1]:
        # Draw sun
        draw.ellipse([(center_x - radius, center_y - radius),
                       (center_x + radius, center_y + radius)],
                      fill=sun_color, outline=outline_color, width=1)
        
        # Draw rays
        ray_length = radius * 0.7
        for angle in range(0, 360, 45):
            rad = math.radians(angle)
            start_x = center_x + radius * math.cos(rad)
            start_y = center_y + radius * math.sin(rad)
            end_x = center_x + (radius + ray_length) * math.cos(rad)
            end_y = center_y + (radius + ray_length) * math.sin(rad)
            draw.line([(start_x, start_y), (end_x, end_y)], fill=sun_color, width=2)
    
    # Partly cloudy (2)
    elif weather_code == 2:
        # Draw small sun in the top left
        small_radius = radius * 0.7
        small_x = center_x - radius * 0.5
        small_y = center_y - radius * 0.5
        draw.ellipse([(small_x - small_radius, small_y - small_radius),
                       (small_x + small_radius, small_y + small_radius)],
                      fill=sun_color, outline=outline_color, width=1)
        
        # Draw cloud in the bottom right
        cloud_x = center_x + radius * 0.3
        cloud_y = center_y + radius * 0.3
        cloud_radius = radius * 0.8
        
        # Main cloud shape
        draw.ellipse([(cloud_x - cloud_radius, cloud_y - cloud_radius * 0.7),
                       (cloud_x + cloud_radius, cloud_y + cloud_radius * 0.7)],
                      fill=cloud_color, outline=outline_color, width=1)
        
        # Additional cloud puffs
        draw.ellipse([(cloud_x - cloud_radius * 0.8, cloud_y - cloud_radius * 1.0),
                       (cloud_x - cloud_radius * 0.2, cloud_y - cloud_radius * 0.4)],
                      fill=cloud_color, outline=outline_color, width=1)
        draw.ellipse([(cloud_x + cloud_radius * 0.2, cloud_y - cloud_radius * 1.0),
                       (cloud_x + cloud_radius * 0.8, cloud_y - cloud_radius * 0.4)],
                      fill=cloud_color, outline=outline_color, width=1)
    
    # Overcast (3)
    elif weather_code == 3:
        # Draw a large cloud
        cloud_radius = radius * 1.2
        
        # Main cloud shape
        draw.ellipse([(center_x - cloud_radius, center_y - cloud_radius * 0.6),
                       (center_x + cloud_radius, center_y + cloud_radius * 0.6)],
                      fill=cloud_color, outline=outline_color, width=1)
        
        # Additional cloud puffs
        draw.ellipse([(center_x - cloud_radius * 0.8, center_y - cloud_radius * 1.0),
                       (center_x - cloud_radius * 0.2, center_y - cloud_radius * 0.4)],
                      fill=cloud_color, outline=outline_color, width=1)
        draw.ellipse([(center_x + cloud_radius * 0.2, center_y - cloud_radius * 1.0),
                       (center_x + cloud_radius * 0.8, center_y - cloud_radius * 0.4)],
                      fill=cloud_color, outline=outline_color, width=1)
        draw.ellipse([(center_x - cloud_radius * 0.4, center_y + cloud_radius * 0.2),
                       (center_x + cloud_radius * 0.4, center_y + cloud_radius * 0.8)],
                      fill=cloud_color, outline=outline_color, width=1)
    
    # Fog (45, 48)
    elif weather_code in [45, 48]:
        # Draw fog lines
        line_width = radius * 1.6
        line_height = radius * 0.3
        line_spacing = radius * 0.5
        
        for i in range(3):
            y_pos = center_y - line_spacing + i * line_spacing
            draw.rectangle([(center_x - line_width / 2, y_pos - line_height / 2),
                             (center_x + line_width / 2, y_pos + line_height / 2)],
                            fill=fog_color, outline=outline_color, width=1)
    
    # Rain (51-67) - includes drizzle and rain
    elif weather_code in range(51, 68):
        # Draw a cloud
        cloud_radius = radius * 1.0
        draw.ellipse([(center_x - cloud_radius, center_y - radius * 0.8),
                       (center_x + cloud_radius, center_y - radius * 0.2)],
                      fill=cloud_color, outline=outline_color, width=1)
        
        # Draw rain drops
        drop_length = radius * 0.5
        for i in range(3):
            drop_x = center_x - radius + i * radius
            start_y = center_y
            end_y = center_y + drop_length
            draw.line([(drop_x, start_y), (drop_x, end_y)], fill=rain_color, width=2)
    
    # Snow (71-77)
    elif weather_code in range(71, 78):
        # Draw a cloud
        cloud_radius = radius * 1.0
        draw.ellipse([(center_x - cloud_radius, center_y - radius * 0.8),
                       (center_x + cloud_radius, center_y - radius * 0.2)],
                      fill=cloud_color, outline=outline_color, width=1)
        
        # Draw snowflakes
        flake_radius = radius * 0.15
        for i in range(3):
            flake_x = center_x - radius + i * radius
            flake_y = center_y + radius * 0.5
            
            # Simple snowflake (circle)
            draw.ellipse([(flake_x - flake_radius, flake_y - flake_radius),
                           (flake_x + flake_radius, flake_y + flake_radius)],
                          fill=snow_color, outline=outline_color, width=1)
            
            # Cross lines for snowflake
            line_length = flake_radius * 1.2
            draw.line([(flake_x - line_length, flake_y), (flake_x + line_length, flake_y)],
                      fill=snow_color, width=1)
            draw.line([(flake_x, flake_y - line_length), (flake_x, flake_y + line_length)],
                      fill=snow_color, width=1)
            
            # Diagonal lines
            draw.line([(flake_x - line_length * 0.7, flake_y - line_length * 0.7),
                        (flake_x + line_length * 0.7, flake_y + line_length * 0.7)],
                      fill=snow_color, width=1)
            draw.line([(flake_x - line_length * 0.7, flake_y + line_length * 0.7),
                        (flake_x + line_length * 0.7, flake_y - line_length * 0.7)],
                      fill=snow_color, width=1)
    
    # Thunderstorm (95-99)
    elif weather_code in range(95, 100):
        # Draw a dark cloud
        cloud_radius = radius * 1.0
        dark_cloud = (150, 150, 150)  # Darker gray
        draw.ellipse([(center_x - cloud_radius, center_y - radius * 0.8),
                       (center_x + cloud_radius, center_y - radius * 0.2)],
                      fill=dark_cloud, outline=outline_color, width=1)
        
        # Draw lightning bolt
        lightning_coords = [
            (center_x, center_y - radius * 0.2),
            (center_x - radius * 0.3, center_y + radius * 0.3),
            (center_x, center_y + radius * 0.1),
            (center_x, center_y + radius * 0.7)
        ]
        draw.polygon(lightning_coords, fill=thunder_color, outline=outline_color, width=1)
    
    # Rain/snow showers (80-86)
    elif weather_code in range(80, 87):
        # Draw partially visible sun
        sun_radius = radius * 0.5
        sun_x = center_x - radius * 0.5
        sun_y = center_y - radius * 0.5
        draw.ellipse([(sun_x - sun_radius, sun_y - sun_radius),
                       (sun_x + sun_radius, sun_y + sun_radius)],
                      fill=sun_color, outline=outline_color, width=1)
        
        # Draw cloud
        cloud_x = center_x + radius * 0.3
        cloud_y = center_y
        cloud_radius = radius * 0.8
        draw.ellipse([(cloud_x - cloud_radius, cloud_y - cloud_radius * 0.6),
                       (cloud_x + cloud_radius, cloud_y + cloud_radius * 0.2)],
                      fill=cloud_color, outline=outline_color, width=1)
        
        # Draw rain or snow depending on the code
        if weather_code in range(80, 83):  # Rain showers
            # Draw rain drops
            for i in range(2):
                drop_x = cloud_x - radius * 0.3 + i * radius * 0.6
                start_y = cloud_y + cloud_radius * 0.2
                end_y = cloud_y + cloud_radius * 0.6
                draw.line([(drop_x, start_y), (drop_x, end_y)], fill=rain_color, width=2)
        else:  # Snow showers
            flake_radius = radius * 0.1
            for i in range(2):
                flake_x = cloud_x - radius * 0.3 + i * radius * 0.6
                flake_y = cloud_y + cloud_radius * 0.4
                draw.ellipse([(flake_x - flake_radius, flake_y - flake_radius),
                               (flake_x + flake_radius, flake_y + flake_radius)],
                              fill=snow_color, outline=outline_color, width=1)
    
    # Unknown or not specified
    else:
        # Draw a question mark
        draw.text((center_x - radius * 0.5, center_y - radius * 0.5), "?", fill=(0, 0, 0))