"""
Font handling and Unicode support
"""
import os
import platform
from PIL import ImageFont

def get_unicode_font():
    """Get Unicode fonts optimized for Docker containers"""
    found_fonts = {}
    
    # Check for environment variables (set in Docker)
    env_regular = os.getenv('FONT_REGULAR')
    env_bold = os.getenv('FONT_BOLD')
    
    if env_regular and os.path.exists(env_regular):
        found_fonts["regular"] = env_regular
        print(f"Using environment font (regular): {env_regular}")
    
    if env_bold and os.path.exists(env_bold):
        found_fonts["bold"] = env_bold
        print(f"Using environment font (bold): {env_bold}")
    
    # If environment fonts are set and working, return them
    if found_fonts:
        return found_fonts
    
    # Docker/Linux-optimized font paths (common in containers)
    docker_font_paths = [
        # DejaVu fonts (most reliable for Unicode)
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
        # Liberation fonts
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/liberation/LiberationSans-Bold.ttf",
        # Noto fonts
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
        "/usr/share/fonts/noto/NotoSans-Regular.ttf",
        "/usr/share/fonts/noto/NotoSans-Bold.ttf",
    ]
    
    system = platform.system()
    
    # Add system-specific paths if not in Docker
    if system == "Darwin":  # macOS (for local development)
        docker_font_paths.extend([
            "/System/Library/Fonts/Arial.ttf",
            "/System/Library/Fonts/ArialBold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
        ])
    elif system == "Windows":
        docker_font_paths.extend([
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
        ])
    
    # Check which fonts exist
    for path in docker_font_paths:
        if os.path.exists(path):
            filename = os.path.basename(path).lower()
            if ("bold" in filename or "bd" in filename) and "bold" not in found_fonts:
                found_fonts["bold"] = path
                print(f"Found bold font: {path}")
            elif "bold" not in filename and "bd" not in filename and "regular" not in found_fonts:
                found_fonts["regular"] = path
                print(f"Found regular font: {path}")
    
    # Try font-config command (common in Linux containers)
    if not found_fonts:
        try:
            import subprocess
            # Try to find DejaVu Sans using fc-match
            result = subprocess.run(['fc-match', '-f', '%{file}', 'DejaVu Sans'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout.strip():
                font_path = result.stdout.strip()
                if os.path.exists(font_path):
                    found_fonts["regular"] = font_path
                    print(f"Found font via fc-match: {font_path}")
                    
                    # Try to find bold version
                    bold_result = subprocess.run(['fc-match', '-f', '%{file}', 'DejaVu Sans:weight=bold'], 
                                               capture_output=True, text=True, timeout=5)
                    if bold_result.returncode == 0 and bold_result.stdout.strip():
                        bold_path = bold_result.stdout.strip()
                        if os.path.exists(bold_path):
                            found_fonts["bold"] = bold_path
                            print(f"Found bold font via fc-match: {bold_path}")
        except:
            pass
    
    return found_fonts

def load_fonts():
    """Load fonts with fallback handling"""
    # Try to get Unicode fonts (regular and bold)
    font_paths = get_unicode_font()
    
    fonts_loaded = False
    fonts = {}
    
    if font_paths:
        try:
            # Try to use the found system fonts
            regular_font_path = font_paths.get("regular", font_paths.get("bold", ""))
            bold_font_path = font_paths.get("bold", font_paths.get("regular", ""))
            
            if regular_font_path:
                # Test font loading with a small size first
                test_font = ImageFont.truetype(regular_font_path, 12)
                
                # If successful, load all font sizes
                fonts['big'] = ImageFont.truetype(regular_font_path, 48)
                fonts['title'] = ImageFont.truetype(regular_font_path, 36)
                fonts['month'] = ImageFont.truetype(bold_font_path if bold_font_path else regular_font_path, 24)
                fonts['day'] = ImageFont.truetype(regular_font_path, 24)
                fonts['time'] = ImageFont.truetype(regular_font_path, 14)
                fonts['event'] = ImageFont.truetype(bold_font_path if bold_font_path else regular_font_path, 14)
                fonts['description'] = ImageFont.truetype(regular_font_path, 10)
                fonts['speech'] = ImageFont.truetype(regular_font_path, 12)
                fonts['weather'] = ImageFont.truetype(regular_font_path, 11)
                
                fonts_loaded = True
                print(f"Successfully loaded fonts: regular={regular_font_path}, bold={bold_font_path}")
                
        except Exception as e:
            print(f"Error loading TrueType fonts: {e}")
            fonts_loaded = False
    
    # If TrueType fonts failed, try alternative approaches
    if not fonts_loaded:
        try:
            # Try to load a basic TrueType font using a more generic approach
            system = platform.system()
            
            basic_font_path = None
            if system == "Darwin":  # macOS
                # Try Helvetica which should be available on all macOS systems
                basic_font_path = "/System/Library/Fonts/Helvetica.ttc"
                if not os.path.exists(basic_font_path):
                    basic_font_path = "/System/Library/Fonts/Arial.ttf"
            elif system == "Windows":
                basic_font_path = "C:/Windows/Fonts/arial.ttf"
            elif system == "Linux":
                basic_font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
            
            if basic_font_path and os.path.exists(basic_font_path):
                fonts['big'] = ImageFont.truetype(basic_font_path, 48)
                fonts['title'] = ImageFont.truetype(basic_font_path, 36)
                fonts['month'] = ImageFont.truetype(basic_font_path, 24)
                fonts['day'] = ImageFont.truetype(basic_font_path, 24)
                fonts['time'] = ImageFont.truetype(basic_font_path, 14)
                fonts['event'] = ImageFont.truetype(basic_font_path, 14)
                fonts['description'] = ImageFont.truetype(basic_font_path, 10)
                fonts['speech'] = ImageFont.truetype(basic_font_path, 12)
                fonts['weather'] = ImageFont.truetype(basic_font_path, 11)
                
                fonts_loaded = True
                print(f"Successfully loaded basic font: {basic_font_path}")
                
        except Exception as e:
            print(f"Error loading basic font: {e}")
            fonts_loaded = False
    
    # Final fallback to default fonts
    if not fonts_loaded:
        print("All font loading attempts failed. Using PIL default fonts - Danish characters may not display correctly")
        default_font = ImageFont.load_default()
        fonts['big'] = default_font
        fonts['title'] = default_font
        fonts['month'] = default_font
        fonts['day'] = default_font
        fonts['time'] = default_font
        fonts['event'] = default_font
        fonts['description'] = default_font
        fonts['speech'] = default_font
        fonts['weather'] = default_font
    
    return fonts