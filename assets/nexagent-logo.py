from PIL import Image, ImageDraw, ImageFont
import os

# Create a 500x500 image with white background
width, height = 500, 500
image = Image.new('RGBA', (width, height), (255, 255, 255, 0))
draw = ImageDraw.Draw(image)

# Define colors
primary_color = (41, 128, 185)  # Blue
secondary_color = (52, 152, 219)  # Lighter blue
accent_color = (231, 76, 60)  # Red accent

# Draw a circular background
center_x, center_y = width // 2, height // 2
radius = 200
draw.ellipse((center_x - radius, center_y - radius, 
              center_x + radius, center_y + radius), 
              fill=primary_color)

# Draw inner circle
inner_radius = 180
draw.ellipse((center_x - inner_radius, center_y - inner_radius, 
              center_x + inner_radius, center_y + inner_radius), 
              fill=secondary_color)

# Draw an N shape for Nexagent
line_width = 30
offset = 80
points = [
    (center_x - offset, center_y + offset),  # bottom left
    (center_x - offset, center_y - offset),  # top left
    (center_x + offset, center_y + offset),  # bottom right
    (center_x + offset, center_y - offset),  # top right
]

# Draw the stylized N
draw.line([points[0], points[1]], fill=accent_color, width=line_width)
draw.line([points[1], points[2]], fill=accent_color, width=line_width)
draw.line([points[2], points[3]], fill=accent_color, width=line_width)

# Add small dots at each point
dot_radius = 15
for point in points:
    draw.ellipse((point[0] - dot_radius, point[1] - dot_radius,
                  point[0] + dot_radius, point[1] + dot_radius),
                  fill=(255, 255, 255))

# Draw a web pattern to suggest web scraping
web_color = (255, 255, 255, 100)  # Semi-transparent white
web_lines = 8
for i in range(web_lines):
    angle = (i * 360 / web_lines)
    # Calculate start and end points for web lines
    x_offset = radius * 0.9 * 0.5 * (angle % 45) / 45
    start_x = center_x + int(x_offset * 1.5)
    start_y = center_y
    end_x = center_x + int(radius * 0.9 * 0.5 * -1)
    end_y = center_y + int(radius * 0.9 * 0.5 * 1)
    draw.line([(start_x, start_y), (end_x, end_y)], fill=web_color, width=2)
    # Draw more lines at different angles
    start_x = center_x + int(radius * 0.9 * 0.5 * 1)
    start_y = center_y + int(radius * 0.9 * 0.5 * 1)
    end_x = center_x + int(radius * 0.9 * 0.5 * -1)
    end_y = center_y + int(radius * 0.9 * 0.5 * -1)
    draw.line([(start_x, start_y), (end_x, end_y)], fill=web_color, width=2)

# Save the image with transparent background
image.save('assets/nexagent-logo.png')

print("Logo generated as 'assets/nexagent-logo.png'") 