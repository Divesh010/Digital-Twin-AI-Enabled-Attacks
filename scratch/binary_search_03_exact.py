import os
import subprocess
import time

TARGET_FILE = r"C:\Users\Dell\Documents\SmartCampusDigitalTwin\src\dashboard\pages\03_Security_Dashboard.py"
ENV = os.environ.copy()
ENV["PYTHONPATH"] = "src"
ENV["TEST_TARGET"] = "Security Dashboard"
ENV["PYTHON_EXE"] = r"C:\Users\Dell\AppData\Local\Programs\Python\Python312\python.exe"

with open("backups/binary_search_baseline/03_Security_Dashboard.py", "r", encoding="utf-8") as f:
    LINES = f.readlines()

def run_test(name, code):
    print(f"\\n{'='*50}\\nRUNNING {name}\\n{'='*50}")
    with open(TARGET_FILE, "w", encoding="utf-8") as f:
        f.write(code)
        
    process = subprocess.Popen(
        ["npm.cmd", "--prefix", "desktop", "start"], 
        env=ENV, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    crashed = False
    for line in iter(process.stdout.readline, ''):
        line = line.strip()
        if line: print(line)
        if "[RENDER-GONE]" in line:
            crashed = True
            break
        if "[TEST] Sequence complete" in line or "Error executing JS" in line or "[FAIL-LOAD]" in line:
            break
    subprocess.run(["taskkill", "/F", "/T", "/PID", str(process.pid)], capture_output=True)
    time.sleep(2)
    return crashed

# Let's replace the problematic lines with `pass` so we don't get IndentationError!
suspicious = [
    ("NO_METRICS", "st.metric", "        pass\\n"),
    ("NO_DATAFRAME", "st.dataframe", "        pass\\n"),
    ("NO_PLOTLY", "st.plotly_chart", "        pass\\n"),
    ("NO_SELECTBOX", "st.selectbox", "    selected_location = attacked_locations[0] if len(attacked_locations)>0 else 'None'\\n"),
]

for test_name, trigger, replacement in suspicious:
    new_lines = []
    for line in LINES:
        if trigger in line:
            new_lines.append(replacement)
        else:
            new_lines.append(line)
    
    crashed = run_test(test_name, "".join(new_lines))
    if not crashed:
        print(f"\\n\\n*** FIX FOUND! Removing {trigger} PREVENTS THE CRASH! ***\\n\\n")
        break
    else:
        print(f"\\n[!] STILL CRASHED WITHOUT {trigger}\\n")
