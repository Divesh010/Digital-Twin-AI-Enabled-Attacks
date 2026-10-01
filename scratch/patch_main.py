import os

with open('desktop/main.js', 'r', encoding='utf-8') as f:
    text = f.read()

# I will find the function and replace its body.
import re
text = re.sub(
    r'function getPythonExecutable\(\)\s*\{.*?\}',
    'function getPythonExecutable() {\\n    return process.env.PYTHON_EXE || "C:\\\\\\\\Users\\\\\\\\Dell\\\\\\\\AppData\\\\\\\\Local\\\\\\\\Programs\\\\\\\\Python\\\\\\\\Python312\\\\\\\\python.exe";\\n}',
    text,
    flags=re.DOTALL
)

with open('desktop/main.js', 'w', encoding='utf-8') as f:
    f.write(text)
print("main.js patched")
