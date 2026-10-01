import re
import os
import shutil

def restore():
    base = r"C:\Users\Dell\Documents\SmartCampusDigitalTwin"
    shutil.copy2(os.path.join(base, "backups/dashboard_before_stabilization/styles.py"), os.path.join(base, "src/dashboard/styles.py"))
    shutil.copy2(os.path.join(base, "backups/dashboard_before_stabilization/pages/03_Security_Dashboard.py"), os.path.join(base, "src/dashboard/pages/03_Security_Dashboard.py"))
    shutil.copy2(os.path.join(base, "backups/dashboard_before_stabilization/pages/05_Campus_Configuration.py"), os.path.join(base, "src/dashboard/pages/05_Campus_Configuration.py"))

def clean(filepath):
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()
    
    # 1. section_header corrupted args
    text = re.sub(r'section_header\((.*?),\s*".*?"\)', r'section_header(\1, "")', text)
    
    # 2. specific HTML strings with emojis (e.g. <div>dY>...</div> or >...<)
    text = re.sub(r'>dY.*?</', '></', text)
    text = text.replace('o"', '')
    text = text.replace('+\'', '')
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(text)

restore()
base = r"C:\Users\Dell\Documents\SmartCampusDigitalTwin"
clean(os.path.join(base, "src/dashboard/pages/03_Security_Dashboard.py"))
clean(os.path.join(base, "src/dashboard/pages/05_Campus_Configuration.py"))
clean(os.path.join(base, "src/dashboard/styles.py"))

print("Restored and carefully cleaned!")
