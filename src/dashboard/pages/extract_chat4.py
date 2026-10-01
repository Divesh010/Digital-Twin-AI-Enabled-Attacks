import textwrap
import re
import json

filepath = r'C:\Users\Dell\.gemini\antigravity\brain\bc03d45d-692b-46de-a0aa-0018faacacd5\.system_generated\steps\2\content.md'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# The conversation data is in RSC (React Server Components) format
# Let's extract the large chunk starting from where conversation data begins
# based on author/role patterns around position 450K

# Extract from position 450K to end
conv_data = content[450000:]

# Try to find and decode the conversation messages
# The data appears to be escaped JSON strings

# Let's find all the text content by looking for substantial readable blocks
# Decode the double-escaped content  
decoded = conv_data.replace('\\\\n', '\n').replace('\\\\t', '\t').replace('\\\\"', '"').replace('\\\\', '\\')

# Now find blocks that look like conversation messages
output_file = r'C:\Users\Dell\.gemini\antigravity\brain\bc03d45d-692b-46de-a0aa-0018faacacd5\scratch\conversation_decoded.txt'

with open(output_file, 'w', encoding='utf-8') as out:
    # Find all message-like text blocks (sequences of readable text > 200 chars)
    # Look for paragraphs of English text
    blocks = re.findall(r'[A-Z][a-zA-Z0-9\s,.;:!?\-\(\)\/\*#\[\]_~`@\+=%&\$\'\{\}]{200,}', decoded)
    
    out.write(f"Found {len(blocks)} text blocks\n\n")
    for i, block in enumerate(blocks):
        out.write(f"\n{'='*80}\nBLOCK {i}\n{'='*80}\n")
        out.write(block[:3000] + '\n')

print(f"Found {len(blocks)} blocks, written to conversation_decoded.txt")
# Print first few for inspection
for i, b in enumerate(blocks[:5]):
    print(f"\nBlock {i} (len={len(b)}): {b[:200]}...")
