import re

def full_clean(src, dest):
    with open(src, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()
    
    # Replace the section headers
    text = re.sub(r'section_header\((.*?),\s*".*?"\)', r'section_header(\1, "")', text)
    
    # Replace other known emojis/corrupted blocks
    text = text.replace('dY>,?', '!')
    text = text.replace('o"', 'OK')
    text = text.replace('+\'', '->')
    
    # Just to be absolutely safe, remove all characters with ord() > 127
    clean_text = "".join(c for c in text if ord(c) < 128)
    
    with open(dest, "w", encoding="utf-8") as f:
        f.write(clean_text)

full_clean(
    r"C:\Users\Dell\Documents\SmartCampusDigitalTwin\backups\dashboard_before_stabilization\pages\03_Security_Dashboard.py",
    r"C:\Users\Dell\Documents\SmartCampusDigitalTwin\src\dashboard\pages\03_Security_Dashboard.py"
)
full_clean(
    r"C:\Users\Dell\Documents\SmartCampusDigitalTwin\backups\dashboard_before_stabilization\pages\05_Campus_Configuration.py",
    r"C:\Users\Dell\Documents\SmartCampusDigitalTwin\src\dashboard\pages\05_Campus_Configuration.py"
)

# And style.py
full_clean(
    r"C:\Users\Dell\Documents\SmartCampusDigitalTwin\backups\dashboard_before_stabilization\styles.py",
    r"C:\Users\Dell\Documents\SmartCampusDigitalTwin\src\dashboard\styles.py"
)

print("Full clean done")
