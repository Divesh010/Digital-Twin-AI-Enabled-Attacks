import os

file_path = r"C:\Users\Dell\Documents\SmartCampusDigitalTwin\src\dashboard\pages\03_Security_Dashboard.py"
with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
    content = f.read()

# Manual replacement
content = content.replace('section_header("CYBERSECURITY & FDI MONITORING", "dY>,?")', 'section_header("CYBERSECURITY & FDI MONITORING", "")')
content = content.replace('section_header("ATTACK REGISTRY", "dY\\"<")', 'section_header("ATTACK REGISTRY", "")')
content = content.replace('section_header("ATTACK ANALYSIS", "dY\\"Z")', 'section_header("ATTACK ANALYSIS", "")')
content = content.replace('section_header("ATTACK MAGNITUDE OVER TIME", "dY\\"^")', 'section_header("ATTACK MAGNITUDE OVER TIME", "")')
content = content.replace('dY', '') # Catch any remaining

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Cleaned!")
