import textwrap
import re
import json

filepath = r'C:\Users\Dell\.gemini\antigravity\brain\bc03d45d-692b-46de-a0aa-0018faacacd5\.system_generated\steps\2\content.md'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Try to find the JSON data embedded in the HTML
# Look for the script tag with conversation data
match = re.search(r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', content)
if match:
    print("Found __NEXT_DATA__")
    data = json.loads(match.group(1))
    print(json.dumps(data, indent=2)[:5000])
else:
    print("No __NEXT_DATA__ found")

# Try alternative: look for serverResponse or linearConversation
match2 = re.search(r'"linear_conversation"\s*:\s*\[', content)
if match2:
    print(f"\nFound linear_conversation at position {match2.start()}")
    # Extract a chunk around it
    chunk = content[match2.start():match2.start()+2000]
    print(chunk[:1000])
else:
    print("No linear_conversation found")

# Try to find conversation content in the HTML body text
match3 = re.search(r'"mapping"\s*:\s*\{', content)
if match3:
    print(f"\nFound mapping at position {match3.start()}")
else:
    print("No mapping found")

# Look for the actual rendered text content
# ChatGPT shared pages often have the text in article or div elements
text_matches = re.findall(r'<article[^>]*>(.*?)</article>', content, re.DOTALL)
print(f"\nFound {len(text_matches)} article elements")

# Look for prose/markdown content
prose_matches = re.findall(r'class="markdown[^"]*"[^>]*>(.*?)</div>', content[:500000], re.DOTALL)
print(f"Found {len(prose_matches)} markdown blocks")

# Look for any substantial text blocks
# Try finding text between specific markers
text_blocks = re.findall(r'"text"\s*:\s*"([^"]{50,})"', content[:500000])
print(f"\nFound {len(text_blocks)} text blocks")
for i, block in enumerate(text_blocks[:3]):
    decoded = block.encode().decode('unicode_escape', errors='replace')
    print(f"\nText block {i}: {decoded[:300]}...")
