"""
AI image generation using ImageRouter.io
"""
import os
import requests
import datetime
from calendar_api import fetch_calendar_events
from llm_handler import llm

def draw_calendar_animal_imagerouter():
    """Create a PNG based on calendar events using ImageRouter.io API"""
    try:
        # Fetch today's events
        calendar_events = fetch_calendar_events()
        today = datetime.date.today()
        
        # Get events for today
        todays_events = calendar_events.get(today, [])
        
        if not todays_events:
            # No events - create a relaxed animal
            prompt = "Create a pencil drawn cute and relaxed cat in Winnie the Pooh style with only the colors red, black and white. The cat should look peaceful and happy with no obligations."
        else:
            # Has events - create an animal that reflects the day's activity
            event_count = len(todays_events)
            event_summary = "; ".join([f"{event['time']}: {event['summary']}" for event in todays_events[:3]])
            
            if event_count <= 2:
                mood = "happy and organized"
            elif event_count <= 4:
                mood = "busy but cheerful"
            else:
                mood = "overwhelmed but determined"
            
            prompt = f"Create a pencil drawn cute animal in Winnie the Pooh style with only the colors red, black and white. The animal should look {mood} and reflect a day with one of these activities: {event_summary}"
        
        return generate_image_with_imagerouter(prompt, "calendar_animal.png")
        
    except Exception as e:
        print(f"Error in draw_calendar_animal_imagerouter: {e}")
        return "assets/dog.png"

def draw_llm_animal_imagerouter():
    """Create a PNG based on the daily LLM-generated fact using ImageRouter.io"""
    try:
        # Get the daily fact from LLM
        daily_fact = llm()
        
        # Analyze the content of the fact to create better prompts
        fact_lower = daily_fact.lower()
        
        # Determine animal and activity based on the fact content
        if any(word in fact_lower for word in ['honning', 'honey', 'bi', 'bee']):
            animal_activity = "happy bee wearing a red bow tie, surrounded by hexagonal honey patterns"
        elif any(word in fact_lower for word in ['elefant', 'elephant']):
            animal_activity = "wise elephant with red ears, touching the ground with its trunk"
        elif any(word in fact_lower for word in ['delfin', 'dolphin']):
            animal_activity = "playful dolphin with a red hat, jumping through water waves"
        elif any(word in fact_lower for word in ['fugl', 'bird', 'kolibri', 'hummingbird']):
            animal_activity = "tiny hummingbird with red wings, hovering near a flower"
        elif any(word in fact_lower for word in ['kat', 'cat']):
            animal_activity = "curious cat with red collar, eyes wide and glowing"
        elif any(word in fact_lower for word in ['pingvin', 'penguin']):
            animal_activity = "cheerful penguin wearing a red scarf, flippers spread wide"
        elif any(word in fact_lower for word in ['ugle', 'owl']):
            animal_activity = "scholarly owl with red glasses, perched on a book"
        elif any(word in fact_lower for word in ['løb', 'run', 'hurtig', 'fast']):
            animal_activity = "speedy rabbit with red running shoes, mid-leap"
        elif any(word in fact_lower for word in ['vand', 'water', 'hav', 'ocean']):
            animal_activity = "friendly whale with a red spout, swimming peacefully"
        elif any(word in fact_lower for word in ['træ', 'tree', 'gren', 'branch']):
            animal_activity = "curious squirrel with a red acorn, sitting on a tree branch"
        else:
            # Default educational animal
            animal_activity = "wise bear wearing red professor glasses, pointing at something interesting"
        
        # Create a prompt based on the fact content
        prompt = f"""Create a simple educational illustration using ONLY these exact colors: pure red (#FF0000), pure black (#000000), and pure white (#FFFFFF). NO other colors allowed.

                    Draw a {animal_activity} in a simple Winnie the Pooh art style. The animal should look educational and whimsical, illustrating this fun fact: "{daily_fact[:100]}..."

                    Important requirements for e-ink display:
                    - Use ONLY solid red, black, and white areas
                    - No gradients, no gray tones, no color mixing
                    - Clean, simple shapes with bold black outlines
                    - Red used for clothing, accessories, or key details
                    - White background with high contrast
                    - Educational and child-friendly appearance

                    The illustration should make the fun fact come alive and be easily understood by children."""
                            
        return generate_image_with_imagerouter(prompt, "llm_animal.png")
        
    except Exception as e:
        print(f"Error in draw_llm_animal_imagerouter: {e}")
        return "assets/dog.png"

def generate_image_with_imagerouter(prompt, filename):
    """Generic function to generate images using ImageRouter.io"""
    # ImageRouter.io API configuration
    url = "https://api.imagerouter.io/v1/openai/images/generations"
    
    # Try primary model first, then fallback
    models = [
            "google/gemini-2.0-flash-exp",
            "HiDream-ai/HiDream-I1-Dev"
    ]
    
    for model in models:
        try:
            print(f"Trying model: {model} for {filename}")
            
            payload = {
                "prompt": prompt,
                "model": model,
            }
            
            headers = {
                "Authorization": f"Bearer {os.getenv('IMAGEROUTER_API_KEY')}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(url, json=payload, headers=headers)
            result = response.json()
            
            if response.status_code == 200 and 'data' in result and len(result['data']) > 0:
                # Get the image URL from the response
                image_url = result['data'][0]['url']
                print(f"Generated image URL: {image_url}")
                
                # Download and save the image
                image_response = requests.get(image_url)
                
                if image_response.status_code == 200:
                    # Create output directory if it doesn't exist
                    os.makedirs("output", exist_ok=True)
                    
                    # Save the image
                    full_path = f"output/{filename}"
                    with open(full_path, "wb") as f:
                        f.write(image_response.content)
                    
                    print(f"Image saved as: {full_path}")
                    return full_path
                else:
                    print(f"Failed to download image: {image_response.status_code}")
                    continue
            else:
                print(f"API error with {model}: {result}")
                continue
                
        except Exception as e:
            print(f"Error with model {model}: {e}")
            continue
    
    # If all models fail, return fallback
    print(f"All ImageRouter models failed for {filename}, using fallback image")
    return "assets/dog.png"

def draw_dynamic_animal(mode="auto"):
    """
    Create a PNG based on calendar events or LLM content using ImageRouter.io
    mode: "events", "llm", or "auto" (chooses based on day of week)
    """
    if mode == "auto":
        # Alternate based on day of week or other logic
        today = datetime.date.today()
        mode = "events" if today.weekday() % 2 == 0 else "llm"
    
    if mode == "events":
        return draw_calendar_animal_imagerouter()
    elif mode == "llm":
        return draw_llm_animal_imagerouter()
    else:
        raise ValueError("Mode must be 'events', 'llm', or 'auto'")