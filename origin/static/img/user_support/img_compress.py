# compress.py
import sys
from PIL import Image

def compress(filepath, quality=10):#quality determine compression level
    img = Image.open(filepath)
    
    # Convert to RGB if needed
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')
    
    # Resize if wider than 1200px
    if img.width > 1200:
        ratio = 1200 / img.width
        new_height = int(img.height * ratio)
        img = img.resize((1200, new_height), Image.LANCZOS)
    
    # Overwrite original
    img.save(filepath, 'JPEG', quality=quality, optimize=True, progressive=True)
    
    # Show size
    import os
    size_kb = os.path.getsize(filepath) / 1024
    print(f"Compressed: {filepath} ({size_kb:.0f}KB)")

if __name__ == '__main__':
    for path in sys.argv[1:]:
        compress(path)