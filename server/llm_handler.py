"""
LLM integration for generating fun facts
"""
import os
import requests
import random
import datetime
from calendar_api import fetch_calendar_events

def clean_markdown_text(text):
    """Remove markdown formatting from text"""
    # Remove **bold** formatting
    text = text.replace('**', '')
    # Remove *italic* formatting
    text = text.replace('*', '')
    # Remove other common markdown elements if needed
    text = text.replace('_', '')
    return text.strip()

def llm() -> str:
    """Generate a fun fact using OpenRouter API with direct HTTP requests"""
    try:
        # Fetch today's events
        calendar_events = fetch_calendar_events()
        today = datetime.date.today()
        
        # Get events for today
        todays_events = calendar_events.get(today, [])
        if not todays_events:
            general_topics = ["et mærkeligt dyr", "en sjov ting fra rummet", "en hemmelighed om vand", "en rekord om legetøj"]
            random_topic = random.choice(general_topics)

            prompt = (
                f"Du er en fantasifuld historiefortæller for børn. Fortæl kun et meget kort, muntert og fantasifuldt fun fact for børn på maksimalt 1-2 linjer om **{random_topic}**. "
                "Fakta skal sætte gang i tanker og leg. Start direkte med fakta, ikke med 'Her er et fun fact'. "
                "Brug ikke markdown formatting."
            )        
 
        else:
            # Has events - pick just one event for a focused fact
            first_event = todays_events[0]['summary']
            prompt = (
            f"Du er en fantasifuld historiefortæller for børn. Opgaven er: '{first_event}'. "
            "Skriv kun et meget kort, muntert og fantasifuldt fun fact for børn på maksimalt 1-2 linjer. "
            "Fakta skal sætte gang i tanker og leg, og bør relateres til det sjove eller mærkelige ved emnet. "
            "Start direkte med fakta uden indledning som 'Vidste du' eller 'Her er et fun fact'. "
            "Brug ikke markdown formatting."
        )
        # Check if API key exists
        api_key = os.getenv('OPENROUTER_API_KEY')
        if not api_key:
            print("Warning: OPENROUTER_API_KEY not found")
            return get_fallback_fun_fact()
        
        # Use direct HTTP requests to avoid OpenAI client version issues
        url = "https://openrouter.ai/api/v1/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "Calendar Generator",
        }
        
        # Try different models
        models_to_try = [
            "google/gemma-3-27b-it:free",
            "meta-llama/llama-3.2-3b-instruct:free",
            "microsoft/phi-3-mini-128k-instruct:free"
        ]
        
        for model in models_to_try:
            try:
                print(f"Trying LLM model: {model}")
                
                data = {
                    "model": model,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                }
                
                response = requests.post(url, headers=headers, json=data, timeout=30)
                
                if response.status_code == 200:
                    result = response.json()
                    message = result['choices'][0]['message']['content']
                    # Clean markdown formatting
                    cleaned_message = clean_markdown_text(message)
                    print(f"LLM success with {model}: {cleaned_message}")
                    return cleaned_message
                else:
                    print(f"Model {model} failed: {response.status_code} - {response.text}")
                    continue
                    
            except Exception as model_error:
                print(f"Model {model} error: {model_error}")
                continue
        
        # All models failed
        print("All LLM models failed, using fallback")
        return get_fallback_fun_fact()
        
    except Exception as e:
        print(f"Error in LLM generation: {e}")
        return get_fallback_fun_fact()

def get_fallback_fun_fact() -> str:
    """Provide a fallback fun fact when LLM fails"""
    fallback_facts = [
        "Vidste du at elefanter kan 'høre' med deres fødder? De føler vibrationer i jorden!",
        "En gruppe flamingoer kaldes en 'flamboyance' - hvor flot er det ikke?",
        "Kolibrier er de eneste fugle der kan flyve baglæns!",
        "Delfiner giver sig selv navne ved at lave unikke fløjtelyde!",
        "Bier kommunikerer ved at danse - de viser retning og afstand til blomster!",
        "Kattes øjne lyser i mørket fordi de har et spejl bag øjnene!",
        "Pingviner kan springe næsten 3 meter op af vandet!",
        "En gruppe ugler kaldes en 'parliament' - som et parlament!"
    ]
    
    selected_fact = random.choice(fallback_facts)
    print(f"Using fallback fun fact: {selected_fact}")
    return selected_fact