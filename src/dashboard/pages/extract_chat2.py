import textwrap
import re

filepath = r'C:\Users\Dell\.gemini\antigravity\brain\bc03d45d-692b-46de-a0aa-0018faacacd5\.system_generated\steps\2\content.md'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

print(f"Total file size: {len(content)} bytes")

# Look at the structure - find all script tags
scripts = re.findall(r'<script[^>]*>(.*?)</script>', content[:100000], re.DOTALL)
print(f"\nFound {len(scripts)} script tags in first 100K")
for i, s in enumerate(scripts):
    if len(s) > 100:
        print(f"\nScript {i} (len={len(s)}): {s[:200]}...")

# Check if it's all just one giant JSON blob
# Look at the last 10K of the file for conversation content
last_chunk = content[-20000:]
print(f"\n=== LAST 20K ===")
print(last_chunk[:3000])

# Look for any human-readable text
# Find patterns like "Review Gemini response" from the title
title_match = re.search(r'Review Gemini', content)
if title_match:
    print(f"\nFound 'Review Gemini' at position {title_match.start()}")
    
# Search for key project-related words
for keyword in ['M.Tech', 'MTech', 'project', 'backend', 'frontend', 'React', 'Node', 'Flask', 'Django', 'database', 'MongoDB', 'MySQL', 'API']:
    matches = [(m.start(), content[max(0,m.start()-50):m.start()+100]) for m in re.finditer(keyword, content, re.IGNORECASE)]
    if matches:
        print(f"\n'{keyword}' found {len(matches)} times")
        for pos, ctx in matches[:2]:
            print(f"  at {pos}: ...{ctx}...")
