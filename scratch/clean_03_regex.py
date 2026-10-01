import re

file_path = r"C:\Users\Dell\Documents\SmartCampusDigitalTwin\src\dashboard\pages\03_Security_Dashboard.py"
with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
    text = f.read()

# Replace section_header("Title", "CORRUPTED_STRING") with section_header("Title", "")
text = re.sub(r'section_header\((.*?),\s*".*?"\)', r'section_header(\1, "")', text)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(text)
print("Regex cleaned!")
