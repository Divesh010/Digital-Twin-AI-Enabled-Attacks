import re

def clean_file(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()
    
    # Remove the corrupted second argument from section_header
    text = re.sub(r'section_header\((.*?),\s*".*?"\)', r'section_header(\1, "")', text)
    
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)

clean_file(r"C:\Users\Dell\Documents\SmartCampusDigitalTwin\src\dashboard\pages\03_Security_Dashboard.py")
clean_file(r"C:\Users\Dell\Documents\SmartCampusDigitalTwin\src\dashboard\pages\05_Campus_Configuration.py")
print("Cleaned 03 and 05")
