#!/usr/bin/env python3
"""
Main calendar generator with multi-calendar support and symbol-based differentiation
"""

from PIL import Image, ImageDraw
import datetime
import os
import subprocess

# Import our modular components
from calendar_api import fetch_calendar_events
from llm_handler import llm, clean_markdown_text
from image_generator import draw_dynamic_animal
from weather_handler import fetch_weather_forecast, create_weather_icon
from font_handler import load_fonts

def generate_illustrated_calendar(filename="output/illustrated_calendar.png", width=800, height=480): 
    """Generates an illustrated calendar image with Danish day names and LLM speech bubble."""
    
    # Create output directory if it doesn't exist
    os.makedirs("output", exist_ok=True)
    
    # First, fetch calendar events
    try:
        calendar_events = fetch_calendar_events()
        print(f"Fetched calendar events: {calendar_events}")
    except Exception as e:
        print(f"Error fetching calendar events: {e}")
        calendar_events = {}
    
    # Fetch weather forecast
    try:
        weather_forecast = fetch_weather_forecast()
        print(f"Fetched weather forecast: {weather_forecast}")
    except Exception as e:
        print(f"Error fetching weather forecast: {e}")
        weather_forecast = None
    
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)
    
    # Load fonts
    fonts = load_fonts()
    
    # Define Danish day and month names with proper Unicode characters
    danish_days = {
        0: "Mandag",     # Monday
        1: "Tirsdag",    # Tuesday
        2: "Onsdag",     # Wednesday
        3: "Torsdag",    # Thursday
        4: "Fredag",     # Friday
        5: "Lørdag",     # Saturday
        6: "Søndag"      # Sunday
    }
    
    danish_months = {
        1: "Januar",     # January
        2: "Februar",    # February
        3: "Marts",      # March
        4: "April",      # April
        5: "Maj",        # May
        6: "Juni",       # June
        7: "Juli",       # July
        8: "August",     # August
        9: "September",  # September
        10: "Oktober",   # October
        11: "November",  # November
        12: "December"   # December
    }
    
    # Get Today's Date
    today = datetime.date.today()
    
    # Add current month to top left corner
    month_name = danish_months.get(today.month, str(today.month)).upper()
    month_x = 20
    month_y = 20
    draw.text((month_x, month_y), month_name, font=fonts['month'], fill="black")
    
    # --- Red Top Line ---
    red_color = (255, 0, 0)
    red_line_y = 60
    draw.line([(10, red_line_y), (width - 10, red_line_y)], fill=red_color, width=3)
    
    # Get Today's Date and Calculate Following Days
    days_to_show = 4
    dates = [today + datetime.timedelta(days=i) for i in range(days_to_show)]
    
    base_x_offset = 150
    y_offset = red_line_y - 35
    cell_width = 160
    
    # Draw Dates and Days of the Week - Horizontal
    for i, date in enumerate(dates):
        # Get weekday as integer (0-6, where 0 is Monday)
        weekday = date.weekday()
        day_name = danish_days.get(weekday, str(weekday))
        day_text = f"{day_name} {date.day}."
        draw.text((base_x_offset + i * cell_width, y_offset), day_text, font=fonts['day'], fill="black")
    
    # Add weather forecasts under the red line
    weather_y = red_line_y + 10
    weather_box_color = (240, 240, 240)  # Light grey
    weather_box_outline = (180, 180, 180)  # Darker grey for outline
    
    # Define fallback weather data in case API fails
    fallback_codes = [2, 3, 61, 1]  # Example weather codes
    fallback_temps = [
        {"min_temp": 2, "max_temp": 11},
        {"min_temp": 5, "max_temp": 9},
        {"min_temp": 4, "max_temp": 12},
        {"min_temp": 3, "max_temp": 10}
    ]
    
    if weather_forecast:
        for i, day_weather in enumerate(weather_forecast):
            x_pos = base_x_offset + i * cell_width
            
            # Draw grey box around weather info
            weather_box_width = cell_width - 20
            weather_box_height = 24
            draw.rectangle(
                [(x_pos - 5, weather_y - 5),
                 (x_pos + weather_box_width, weather_y + weather_box_height)],
                fill=weather_box_color,
                outline=weather_box_outline,
                width=1
            )
            
            # Draw custom weather icon
            create_weather_icon(draw, x_pos, weather_y, day_weather['weather_code'], size=18)
            
            # Draw temperature range
            temp_text = f"{day_weather['min_temp']}° - {day_weather['max_temp']}°"
            draw.text((x_pos + 24, weather_y + 6), temp_text, font=fonts['weather'], fill="black")
    else:
        # Use fallback weather data
        for i in range(days_to_show):
            x_pos = base_x_offset + i * cell_width
            
            # Draw grey box around weather info
            weather_box_width = cell_width - 20
            weather_box_height = 24
            draw.rectangle(
                [(x_pos - 5, weather_y - 5),
                 (x_pos + weather_box_width, weather_y + weather_box_height)],
                fill=weather_box_color,
                outline=weather_box_outline,
                width=1
            )
            
            # Draw custom weather icon using fallback data
            create_weather_icon(draw, x_pos, weather_y, fallback_codes[i], size=18)
            
            # Draw temperature range
            temp_text = f"{fallback_temps[i]['min_temp']}° - {fallback_temps[i]['max_temp']}°"
            draw.text((x_pos + 24, weather_y + 6), temp_text, font=fonts['weather'], fill="black")
    
    # Event Entries - Create a list to track vertical positions for each day column
    y_offset_bottoms = [red_line_y + 55] * days_to_show  # Start a bit lower, below the weather info
    
    # Calculate the middle point for divider lines - adjusted back for 600px height
    divider_line_length = (height - red_line_y - 150) // 2  # Adjusted for 600px canvas
    
    # Draw shortened vertical dividers between days
    for i in range(1, days_to_show):
        draw.line([(base_x_offset + i * cell_width - 10, red_line_y + 10),
                   (base_x_offset + i * cell_width - 10, red_line_y + 10 + divider_line_length)],
                  fill="lightgray", width=1)
    
    def draw_event(date_index, time, event_title, calendar_symbol="●"):
        """Modified draw_event function to include calendar symbols"""
        x_pos = base_x_offset + date_index * cell_width
        
        # Skip if we're running out of vertical space - adjusted back for 600px
        if y_offset_bottoms[date_index] > height - 150:
            return
        
        # Calculate strict column boundaries
        column_left = x_pos
        column_right = x_pos + cell_width - 15  # Leave margin for column separator
        max_column_width = column_right - column_left
        
        # Prepend the calendar symbol to the event title
        symbolized_title = f"{calendar_symbol} {event_title}"
        
        # Calculate the combined text with better spacing
        time_width = 0
        if time.strip():  # Only calculate width if there's actually a time
            time_width = draw.textlength(time + " ", font=fonts['time'])
            # Ensure time fits within column
            if time_width > max_column_width:
                time_width = max_column_width
                # Truncate time if too long
                truncated_time = time
                while draw.textlength(truncated_time + "... ", font=fonts['time']) > max_column_width and len(truncated_time) > 0:
                    truncated_time = truncated_time[:-1]
                draw.text((column_left, y_offset_bottoms[date_index]), truncated_time + "... ", font=fonts['time'], fill="black")
            else:
                draw.text((column_left, y_offset_bottoms[date_index]), time + " ", font=fonts['time'], fill="black")
        
        # Calculate available width for event text (strictly within column)
        available_width = max_column_width - time_width - 5  # Small padding
        if available_width < 50:  # If too narrow, put event text on next line
            time_width = 0
            available_width = max_column_width - 5
        
        # Wrap symbolized event title with strict width limits
        words = symbolized_title.split()
        lines = []
        current_line = []
        
        for word in words:
            # Test if adding this word would exceed column width
            test_line = ' '.join(current_line + [word])
            text_width = draw.textlength(test_line, font=fonts['event'])
            
            if text_width <= available_width and len(current_line) < 6:  # Max 6 words per line
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    # Single word is too long, truncate it
                    truncated_word = word
                    while draw.textlength(truncated_word + "...", font=fonts['event']) > available_width and len(truncated_word) > 3:
                        truncated_word = truncated_word[:-1]
                    lines.append(truncated_word + "..." if len(truncated_word) < len(word) else word)
        
        if current_line:
            lines.append(' '.join(current_line))
        
        # Draw event title lines with strict positioning
        current_y = y_offset_bottoms[date_index]
        
        for i, line in enumerate(lines[:2]):  # Limit to 2 lines max
            # Calculate text position
            if i == 0 and time_width > 0:
                # First line on same line as time
                text_x = column_left + time_width
            else:
                # Subsequent lines start at column left
                text_x = column_left
                if i > 0:
                    current_y += 16  # Move to next line
            
            # Double-check that text doesn't exceed column boundary
            text_width = draw.textlength(line, font=fonts['event'])
            if text_x + text_width > column_right:
                # Truncate line to fit within column
                truncated_line = line
                while text_x + draw.textlength(truncated_line + "...", font=fonts['event']) > column_right and len(truncated_line) > 3:
                    words_in_line = truncated_line.split()
                    if len(words_in_line) > 1:
                        truncated_line = ' '.join(words_in_line[:-1])
                    else:
                        truncated_line = truncated_line[:-1]
                line = truncated_line + ("..." if len(truncated_line) < len(line) else "")
            
            draw.text((text_x, current_y), line, font=fonts['event'], fill="black")
        
        # Add truncation indicator if text was cut off (positioned within column)
        if len(lines) > 2:
            indicator_x = min(column_right - 15, text_x + draw.textlength(line, font=fonts['event']) + 5)
            draw.text((indicator_x, current_y), "...", font=fonts['event'], fill="gray")
        
        # Update y position for next event with better spacing
        lines_drawn = min(len(lines), 2)
        spacing = 16 + (lines_drawn - 1) * 16 + 6  # Consistent spacing
        y_offset_bottoms[date_index] += spacing
    
    # Display calendar events with symbols
    for i, date in enumerate(dates):
        if date in calendar_events and calendar_events[date]:
            for event in calendar_events[date][:3]:  # Limit to 3 events per day
                draw_event(i, event['time'], event['summary'], event.get('calendar_symbol', '●'))
        else:
            # If no events, show a placeholder
            #draw_event(i, "", "No events", "○")  # Empty circle for no events
            draw_event(i, "", "", "") # Empty circle for no events
    
    # Get LLM response and clean markdown
    try:
        joke_response = llm()
        # Clean any markdown formatting
        joke_response = clean_markdown_text(joke_response)
    except Exception as e:
        joke_response = f"Could not get fun fact: {str(e)}"
    
    # Position for the speech bubble and illustration - adjusted back for 600px
    grey_line_end_y = red_line_y + 10 + divider_line_length
    
    # New positioning - speech bubble first, then illustration below it  
    bubble_x = 50
    bubble_y = grey_line_end_y + 20  # Less space from divider for 600px
    bubble_width = 350
    bubble_height = 100  # Smaller bubble for 600px
    bubble_radius = 15
    
    # Colors for the grey speech bubble
    bubble_fill = (240, 240, 240)  # Light grey
    bubble_outline = (180, 180, 180)  # Darker grey
    
    # Position for illustration - it will be below the speech bubble
    illustration_x = 120
    illustration_y = bubble_y + bubble_height + 20  # Less space for 600px height
    illustration_width = 180  # Slightly smaller illustration
    illustration_height = 180
    
    # Generate dynamic animal using ImageRouter.io (try events mode first, then LLM mode)
    animal_image_path = draw_dynamic_animal("events")
    
    # Load the dynamically generated illustration
    try:
        illustration = Image.open(animal_image_path)
        illustration = illustration.resize((illustration_width, illustration_height))
        
        # CRITICAL: Convert to RGB to remove any alpha channel
        if illustration.mode != 'RGB':
            illustration = illustration.convert('RGB')
        
        img.paste(illustration, (illustration_x, illustration_y))
    except FileNotFoundError:
        draw.text((illustration_x, illustration_y), "Illustration not found", font=fonts['description'], fill="red")
    except Exception as e:
        draw.text((illustration_x, illustration_y), f"Error loading image: {e}", font=fonts['description'], fill="red")
    
    # Wrap text for the speech bubble with better sizing
    def wrap_text(text, font, max_width):
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            text_width = draw.textlength(test_line, font=font)
            if text_width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    # Word is too long, split it
                    lines.append(word)
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines
    
    # Calculate optimal speech bubble size based on content
    temp_wrapped = wrap_text(joke_response, fonts['speech'], bubble_width - 40)  # Account for padding
    needed_height = len(temp_wrapped) * 16 + 40  # Line height + padding
    
    # Adjust bubble height if needed (minimum 80, maximum 160)
    bubble_height = max(80, min(160, needed_height))
    
    # Draw speech bubble with adjusted size
    draw.rounded_rectangle(
        [(bubble_x, bubble_y), (bubble_x + bubble_width, bubble_y + bubble_height)],
        radius=bubble_radius,
        fill=bubble_fill,
        outline=bubble_outline,
        width=2
    )
    
    # Add speech triangle pointer
    pointer_x = illustration_x + illustration_width // 2
    draw.polygon(
        [(pointer_x - 20, bubble_y + bubble_height),
         (pointer_x, bubble_y + bubble_height + 20),
         (pointer_x + 20, bubble_y + bubble_height)],
        fill=bubble_fill,
        outline=bubble_outline
    )
    
    # Draw wrapped text in the speech bubble with proper spacing
    wrapped_joke = wrap_text(joke_response, fonts['speech'], bubble_width - 40)  # More padding
    line_y = bubble_y + 15  # Start with padding from top
    line_height = 16  # Consistent line height
    
    max_lines = (bubble_height - 30) // line_height  # Calculate max lines that fit
    
    for i, line in enumerate(wrapped_joke):
        if i >= max_lines - 1 and i < len(wrapped_joke) - 1:
            # If this is the last line we can fit and there are more lines, add ellipsis
            truncated_line = line
            while draw.textlength(truncated_line + "...", font=fonts['speech']) > bubble_width - 40 and len(truncated_line) > 0:
                words = truncated_line.split()
                if len(words) > 1:
                    truncated_line = ' '.join(words[:-1])
                else:
                    truncated_line = truncated_line[:-1]
            draw.text((bubble_x + 20, line_y), truncated_line + "...", font=fonts['speech'], fill="black")
            break
        elif i < max_lines:
            draw.text((bubble_x + 20, line_y), line, font=fonts['speech'], fill="black")
            line_y += line_height
        else:
            break

    # Optional secondary illustration (now with more room at bottom)
    if os.getenv('SECONDARY_ILLUSTRATION') != "False":
        # Bottom illustration for decoration (placeholder for second pencil-drawn dog)
        illustration_2_path = "assets/dog.png"  # Replace with actual path
        try:
            illustration_2 = Image.open(illustration_2_path)
            illustration_2 = illustration_2.resize((200, 200))
            
            # Convert to RGB to remove any alpha channel
            if illustration_2.mode != 'RGB':
                illustration_2 = illustration_2.convert('RGB')
            
            img.paste(illustration_2, (width - 220, height - 220))
        except FileNotFoundError:
            # If second illustration is missing, it's not critical
            pass
        except Exception as e:
            # If there's an error, just skip it
            pass

    #img.save(filename)
    # Save with PNGdec-compatible format
    # Save with PNGdec-compatible format
    bmp_filename = filename.replace('.png', '.bmp')
    img.save(bmp_filename, 'BMP')
    print(f"Illustrated calendar saved to {bmp_filename}")
    

if __name__ == "__main__":
    generate_illustrated_calendar()