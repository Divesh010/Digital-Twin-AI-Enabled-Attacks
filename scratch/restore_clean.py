import re

def restore_and_clean(src, dest):
    with open(src, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()
    
    # Remove any corrupted emojis in section_header
    text = re.sub(r'section_header\((.*?),\s*".*?"\)', r'section_header(\1, "")', text)
    
    with open(dest, "w", encoding="utf-8") as f:
        f.write(text)

restore_and_clean(
    r"C:\Users\Dell\Documents\SmartCampusDigitalTwin\backups\dashboard_before_stabilization\pages\03_Security_Dashboard.py",
    r"C:\Users\Dell\Documents\SmartCampusDigitalTwin\src\dashboard\pages\03_Security_Dashboard.py"
)
restore_and_clean(
    r"C:\Users\Dell\Documents\SmartCampusDigitalTwin\backups\dashboard_before_stabilization\pages\05_Campus_Configuration.py",
    r"C:\Users\Dell\Documents\SmartCampusDigitalTwin\src\dashboard\pages\05_Campus_Configuration.py"
)
print("Restored and cleaned!")
