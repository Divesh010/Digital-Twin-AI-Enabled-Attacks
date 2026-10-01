import re
import os
import shutil

def restore():
    base = r"C:\Users\Dell\Documents\SmartCampusDigitalTwin"
    shutil.copy2(os.path.join(base, "backups/dashboard_before_stabilization/styles.py"), os.path.join(base, "src/dashboard/styles.py"))
    shutil.copy2(os.path.join(base, "backups/dashboard_before_stabilization/pages/03_Security_Dashboard.py"), os.path.join(base, "src/dashboard/pages/03_Security_Dashboard.py"))
    shutil.copy2(os.path.join(base, "backups/dashboard_before_stabilization/pages/05_Campus_Configuration.py"), os.path.join(base, "src/dashboard/pages/05_Campus_Configuration.py"))

restore()

# Now patch 03 to cast dataframes to strings to bypass Intl.Locale crashes
base = r"C:\Users\Dell\Documents\SmartCampusDigitalTwin"
with open(os.path.join(base, "src/dashboard/pages/03_Security_Dashboard.py"), "r", encoding="utf-8", errors="ignore") as f:
    text = f.read()

# Replace st.dataframe(df) with st.dataframe(df.astype(str))
text = text.replace("st.dataframe(registry_df, width='stretch', hide_index=True)", "st.dataframe(registry_df.astype(str), width='stretch', hide_index=True)")
text = text.replace("st.dataframe(room_attacks[avail_cols], width='stretch')", "st.dataframe(room_attacks[avail_cols].astype(str), width='stretch')")
text = text.replace("st.dataframe(room_attacks[avail_cols], use_container_width=True)", "st.dataframe(room_attacks[avail_cols].astype(str), use_container_width=True)")

with open(os.path.join(base, "src/dashboard/pages/03_Security_Dashboard.py"), "w", encoding="utf-8") as f:
    f.write(text)

# And for 05, just replace st.number_input with st.text_input to bypass Intl.Locale crash!
with open(os.path.join(base, "src/dashboard/pages/05_Campus_Configuration.py"), "r", encoding="utf-8", errors="ignore") as f:
    text = f.read()

text = text.replace('st.number_input("Floors", min_value=1, max_value=20, value=2)', 'st.text_input("Floors", value="2")')
text = text.replace('st.number_input("Base Load (kW)", min_value=10, max_value=5000, value=100)', 'st.text_input("Base Load (kW)", value="100")')

with open(os.path.join(base, "src/dashboard/pages/05_Campus_Configuration.py"), "w", encoding="utf-8") as f:
    f.write(text)

print("Restored and patched!")
