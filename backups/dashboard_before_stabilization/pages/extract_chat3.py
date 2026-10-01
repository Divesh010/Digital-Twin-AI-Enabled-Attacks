import textwrap
import re
import json

filepath = r'C:\Users\Dell\.gemini\antigravity\brain\bc03d45d-692b-46de-a0aa-0018faacacd5\.system_generated\steps\2\content.md'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# The conversation data seems to be in a large JSON structure
# Let's look for the "linear_conversation" or message text patterns
# Based on the MTech matches, the text appears around position 500K+

# Extract text around identified content areas
# Let's find all readable text between escaped quotes

# Find the area with conversation messages
# Looking for patterns like: "content":{"content_type":"text","parts":["..."]}
# In the encoded form: \\\"parts\\\":[\\\"...\\\"]

# Better approach: find the serialized conversation data
# ChatGPT stores it in RSC format or initial state JSON

# Let's search for the actual message content area more broadly
start_pos = 450000  # Around where we found conversation content

# Search for message-like patterns
# The text seems to be encoded with \\n for newlines
chunk_size = 50000
output_file = r'C:\Users\Dell\.gemini\antigravity\brain\bc03d45d-692b-46de-a0aa-0018faacacd5\scratch\conversation_raw.txt'

with open(output_file, 'w', encoding='utf-8') as out:
    # Find all substantial text strings in the content
    # Pattern: text between escaped quotes that's longer than 100 chars
    pattern = r'(?:parts|text|message|content)(?:\\\\"|")\s*(?::\\s*)?(?:\\\\"|"|\[\\\\"|:\[\")(.{100,?})(?:\\\\"|"\]|"\])'
    
    # Simpler: just find all long strings that look like conversation text
    # Look for sequences of readable text
    pos = 0
    msg_count = 0
    while pos < len(content):
        # Find the next occurrence of common conversation markers
        for marker in ['MTech', 'energy', 'smart grid', 'cybersecurity', 'attack', 'dataset', 'prediction', 'neural', 'LSTM', 'model', 'anomaly']:
            idx = content.find(marker, pos, pos + 100000)
            if idx >= 0:
                # Extract surrounding context
                start = max(0, idx - 500)
                end = min(len(content), idx + 2000)
                snippet = content[start:end]
                # Decode the escaped content
                try:
                    decoded = snippet.encode('utf-8').decode('unicode_escape', errors='replace')
                except:
                    decoded = snippet
                out.write(f"\n{'='*80}\n")
                out.write(f"Found '{marker}' at position {idx}\n")
                out.write(f"{'='*80}\n")
                out.write(decoded + '\n')
                msg_count += 1
                pos = idx + 100
                break
        else:
            pos += 100000

print(f"Extracted {msg_count} context snippets")

# Now let's try a different approach - find the RSC payload
# Look for the conversation title pattern
title_match = re.search(r'Review Gemini response', content)
if title_match:
    print(f"Title at: {title_match.start()}")

# Find where the actual conversation data starts (after all the statsig config)
# Let's look for patterns like message author role
for pattern_str in [r'"author"', r'\\\"author\\\"', r'"role"', r'\\\"role\\\"']:
    matches = list(re.finditer(re.escape(pattern_str) if '\\' not in pattern_str else pattern_str, content))
    if matches:
        print(f"Pattern '{pattern_str}' found {len(matches)} times, first at {matches[0].start()}")
