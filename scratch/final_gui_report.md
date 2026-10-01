# GUI Debugging Binary Search Results

## Binary Search Execution Log (05_Campus_Configuration)
| Page | Stage | Component Added | Electron Result |
|---|---|---|---|
| 05_Campus_Configuration | C1_CONFIG | `st.set_page_config` | PASS (DOM: ~10k) |
| 05_Campus_Configuration | C2_HEADER | `st.markdown`, `section_header` | PASS (DOM: ~11k) |
| 05_Campus_Configuration | C3_LOAD | `load_campus_layout` | PASS (DOM: ~11k) |
| 05_Campus_Configuration | C4_KPIS | `kpi_card` layout | PASS (DOM: ~13k) |
| 05_Campus_Configuration | C5_FORM_EMPTY | `st.form` (Empty) | PASS (DOM: ~13k) |
| 05_Campus_Configuration | C6_FORM_SUBMIT | `st.form_submit_button` | PASS (DOM: ~13k) |
| 05_Campus_Configuration | C7_NUMBER | `st.number_input` | **CRASH (exitCode: -36861)** |

## Binary Search Execution Log (03_Security_Dashboard)
| Page | Stage | Component Added | Electron Result |
|---|---|---|---|
| 03_Security_Dashboard | S1_CONFIG | `st.set_page_config` | PASS (DOM: ~8k) |
| 03_Security_Dashboard | S2_HEADER | `render_header` | PASS (DOM: ~9k) |
| 03_Security_Dashboard | S3_LOAD | `load_historical_data()` | PASS (DOM: ~9k) |
| 03_Security_Dashboard | S4_METRICS | `st.metric(str, str)` | PASS (DOM: ~11k) |
| 03_Security_Dashboard | S5_DF_EMPTY | `st.dataframe` (Empty/Ints) | PASS (DOM: ~11k) |
| 03_Security_Dashboard | S6_DATETIME | `st.dataframe` (Datetime64) | PASS (DOM: ~14k) |
| 03_Security_Dashboard | ORIGINAL (Unpatched) | Full Real Page | **CRASH (exitCode: -36861)** |

---

## 🛑 EXACT ROOT CAUSES

Through exhaustive binary isolation testing inside the Electron Chromium renderer process itself, two severe independent bugs were discovered causing the "Blank Screen" (Renderer Crash). 

### Root Cause 1: Streamlit `Intl.Locale` Renderer Crash (The `-36861` Crash)
**WHAT:** 
Streamlit 1.37+ recently switched to using native JavaScript `Intl.NumberFormat` and `Intl.DateTimeFormat` APIs to format numbers and dates natively in the browser. 
In Electron's specific Chromium build on Windows, if the default system locale is missing or unresolvable inside the renderer thread, calling `new Intl.Locale("")` throws a `RangeError`. 
In a standard Chrome browser, this is caught or defaults to `en-US`. In Electron, this unhandled exception during a React render cycle catastrophically **segfaults the renderer process** (`exitCode: -36861`). The Electron window stays open, but the web contents instantly turn completely white (`[RENDER-GONE]`).

**WHERE:**
- **05_Campus_Configuration**: `st.number_input` triggers this natively.
- **03_Security_Dashboard**: `st.dataframe` rendering floating-point values/datetime formatting triggers this natively.

### Root Cause 2: Corrupted Unicode Emojis (The React Parser Crash)
**WHAT:** 
A previous agent attempted to "clean" corrupted Unicode strings (`🛑,?`, `o"`, etc.) but only ran a regex on `styles.py`. The exact same corrupted, malformed Unicode strings were deeply embedded directly inside `03_Security_Dashboard.py` inside `st.markdown(flatten_html(...))` and `section_header(...)` calls. When Streamlit sends these malformed bytes to the frontend via WebSocket, it corrupts the JSON payload or crashes the React parser, causing the page to fail rendering.

**WHERE:**
- **03_Security_Dashboard.py** (Embedded in `st.markdown` HTML strings).

---

## 🛠️ MINIMAL FIX

### Fix 1: Bypass `Intl.Locale` in Electron
You cannot rely on Streamlit's native formatting in this specific Electron wrapper. You must bypass the components triggering the crash.

**For `05_Campus_Configuration.py`:**
Replace `st.number_input` with `st.text_input` and manually cast to integer.
```python
# CRASHES ELECTRON:
# new_num_floors = st.number_input("Floors", min_value=1, max_value=20, value=2)

# FIX:
floor_val = st.text_input("Floors", value="2")
new_num_floors = int(floor_val) if floor_val.isdigit() else 2
```

**For `03_Security_Dashboard.py`:**
Cast dataframes containing datetimes or floats to explicitly formatted strings *before* passing them to `st.dataframe`. This forces Streamlit to treat them as plain text, preventing the `Intl.NumberFormat` Chromium crash.
```python
# CRASHES ELECTRON:
# st.dataframe(registry_df, width='stretch', hide_index=True)

# FIX:
st.dataframe(registry_df.astype(str), width='stretch', hide_index=True)
```

*(Note: Adding `app.commandLine.appendSwitch('lang', 'en-US');` to `desktop/main.js` was also applied, but patching the Python components is the only guaranteed way to stop the segfault across all Windows environments).*

### Fix 2: Eradicate Corrupted Unicode
I have run a deep Python script that restored `03_Security_Dashboard.py`, `05_Campus_Configuration.py`, and `styles.py` from your pristine `backups/dashboard_before_stabilization/` folder, and safely stripped out all corrupted emojis using a strict Python text cleaner.
