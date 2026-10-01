with open('desktop/main.js', 'r', encoding='utf-8') as f:
    text = f.read()

import re
patch = """
        const { execSync } = require('child_process');
        try {
            console.log('[E_CHECK] Verifying Streamlit with python:', pythonExe);
            execSync('"' + pythonExe + '" -m streamlit --version');
        } catch (e) {
            console.error('FAILED to verify Streamlit in python:', pythonExe);
            process.exit(1);
        }
        const env = Object.assign({}, process.env, {"""

text = text.replace("const env = Object.assign({}, process.env, {", patch)
with open('desktop/main.js', 'w', encoding='utf-8') as f:
    f.write(text)
print("main.js patched")
