import re

def restore_and_clean_styles(src, dest):
    with open(src, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()
    
    # Remove any corrupted emojis in HTML or strings
    # The corrupted pattern usually contains "dY" followed by weird chars
    # We will just strip them out manually or using a broad regex
    text = re.sub(r'dY[^"\'<]*', '', text)
    
    with open(dest, "w", encoding="utf-8") as f:
        f.write(text)

restore_and_clean_styles(
    r"C:\Users\Dell\Documents\SmartCampusDigitalTwin\backups\dashboard_before_stabilization\styles.py",
    r"C:\Users\Dell\Documents\SmartCampusDigitalTwin\src\dashboard\styles.py"
)
print("Restored and cleaned styles!")
