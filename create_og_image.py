#!/usr/bin/env python3
"""Create OG image for neptun.in.ua with NEPTUN logo and Ukraine map"""

import os

from PIL import Image, ImageDraw, ImageFont

# Image dimensions for Open Graph
WIDTH = 1200
HEIGHT = 630

# Colors - dark theme similar to the website
BG_COLOR = (26, 26, 26)  # #1a1a1a - dark background
ACCENT_COLOR = (255, 87, 34)  # Orange accent (like alerts)
TEXT_COLOR = (255, 255, 255)  # White text
SECONDARY_TEXT = (200, 200, 200)  # Gray text
MAP_COLOR = (70, 130, 180)  # Steel blue for Ukraine map
ALERT_RED = (244, 67, 54)  # Red for alert regions
DRONE_ORANGE = (255, 152, 0)  # Orange for drone paths

def draw_ukraine_shape(draw, x_offset, y_offset, scale=1.0):
    """Draw simplified Ukraine map shape"""
    # Simplified Ukraine polygon (approximate shape)
    ukraine_points = [
        (120, 100), (200, 80), (300, 70), (400, 90), (450, 120),
        (480, 180), (500, 250), (520, 300), (480, 350), (420, 380),
        (350, 400), (280, 390), (200, 370), (150, 320), (100, 280),
        (80, 220), (90, 160), (120, 100)
    ]

    # Scale and offset points
    scaled_points = [
        (int(x * scale + x_offset), int(y * scale + y_offset))
        for x, y in ukraine_points
    ]

    # Draw filled shape
    draw.polygon(scaled_points, fill=(50, 50, 50), outline=MAP_COLOR)

    return scaled_points

def draw_alert_regions(draw, x_offset, y_offset, scale=1.0):
    """Draw some alert regions on the map"""
    # Alert regions (eastern Ukraine - approximate positions)
    alert_regions = [
        [(400, 120), (450, 130), (460, 180), (430, 200), (390, 170)],  # Kharkiv
        [(420, 200), (480, 220), (490, 280), (450, 300), (410, 260)],  # Donetsk
        [(380, 300), (420, 310), (430, 360), (400, 380), (360, 350)],  # Zaporizhzhia
    ]

    for region in alert_regions:
        scaled = [(int(x * scale + x_offset), int(y * scale + y_offset)) for x, y in region]
        draw.polygon(scaled, fill=ALERT_RED, outline=ALERT_RED)

def draw_drone_paths(draw, x_offset, y_offset, scale=1.0):
    """Draw drone/shahed paths"""
    # Drone flight paths
    paths = [
        [(500, 200), (450, 220), (400, 250), (350, 280)],
        [(480, 300), (430, 280), (380, 260), (330, 250)],
        [(490, 250), (440, 260), (390, 270), (340, 290)],
    ]

    for path in paths:
        scaled = [(int(x * scale + x_offset), int(y * scale + y_offset)) for x, y in path]
        for i in range(len(scaled) - 1):
            draw.line([scaled[i], scaled[i+1]], fill=DRONE_ORANGE, width=3)

        # Draw drone icon at end of path
        if scaled:
            end = scaled[-1]
            draw.ellipse([end[0]-5, end[1]-5, end[0]+5, end[1]+5], fill=DRONE_ORANGE)

def create_og_image():
    """Create the Open Graph image"""
    # Create new image with dark background
    img = Image.new('RGB', (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Draw gradient overlay (subtle)
    for y in range(HEIGHT):
        alpha = int(30 * (1 - y / HEIGHT))
        draw.line([(0, y), (WIDTH, y)], fill=(255, 255, 255, alpha))

    # Redraw solid background
    img = Image.new('RGB', (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Draw Ukraine map on the right side
    map_scale = 0.8
    map_x_offset = 550
    map_y_offset = 80

    draw_ukraine_shape(draw, map_x_offset, map_y_offset, map_scale)
    draw_alert_regions(draw, map_x_offset, map_y_offset, map_scale)
    draw_drone_paths(draw, map_x_offset, map_y_offset, map_scale)

    # Try to load a nice font, fall back to default
    try:
        # Try system fonts
        font_paths = [
            "/System/Library/Fonts/Helvetica.ttc",
            "/System/Library/Fonts/SFNSDisplay.ttf",
            "/Library/Fonts/Arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]
        font_large = None
        font_medium = None
        font_small = None

        for font_path in font_paths:
            if os.path.exists(font_path):
                font_large = ImageFont.truetype(font_path, 80)
                font_medium = ImageFont.truetype(font_path, 36)
                font_small = ImageFont.truetype(font_path, 24)
                break

        if font_large is None:
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small = ImageFont.load_default()
    except:
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # Draw NEPTUN logo/text
    logo_text = "NEPTUN"
    draw.text((60, 150), logo_text, font=font_large, fill=TEXT_COLOR)

    # Draw orange underline
    draw.rectangle([60, 250, 350, 258], fill=ACCENT_COLOR)

    # Draw subtitle
    subtitle = "Карта шахедів онлайн"
    draw.text((60, 280), subtitle, font=font_medium, fill=TEXT_COLOR)

    # Draw second line
    subtitle2 = "Карта тривог України"
    draw.text((60, 330), subtitle2, font=font_medium, fill=SECONDARY_TEXT)

    # Draw features
    features = [
        "🔴 Тривоги в реальному часі",
        "🚀 Шахеди та ракети на мапі",
        "📍 Точний трекінг загроз"
    ]

    y_pos = 400
    for feature in features:
        draw.text((60, y_pos), feature, font=font_small, fill=SECONDARY_TEXT)
        y_pos += 35

    # Draw website URL
    draw.text((60, 550), "neptun.in.ua", font=font_medium, fill=ACCENT_COLOR)

    # Add some decorative elements
    # Draw small drone icons
    drone_positions = [(900, 150), (950, 200), (1000, 180)]
    for pos in drone_positions:
        draw.ellipse([pos[0]-8, pos[1]-8, pos[0]+8, pos[1]+8], fill=DRONE_ORANGE)
        # Draw propeller lines
        draw.line([pos[0]-12, pos[1], pos[0]+12, pos[1]], fill=DRONE_ORANGE, width=2)
        draw.line([pos[0], pos[1]-12, pos[0], pos[1]+12], fill=DRONE_ORANGE, width=2)

    # Save the image
    output_path = os.path.join(os.path.dirname(__file__), 'static', 'og-image.png')
    img.save(output_path, 'PNG', quality=95)
    print(f"OG image created: {output_path}")
    print(f"Image size: {WIDTH}x{HEIGHT}")

    return output_path

if __name__ == "__main__":
    create_og_image()
