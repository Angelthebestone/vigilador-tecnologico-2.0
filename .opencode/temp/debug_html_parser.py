"""Debug HTML parser for branch files."""
import re
import sys
sys.path.insert(0, "src")

from vigilancia_multiagente.infra.prompts.loader import load_prompt

text = load_prompt("branches/avances")

# Direct regex test
print("Contains type=\"do\":", 'type="do"' in text)
print("Contains <rules:", "<rules" in text)
print("Contains </rules>:", "</rules>" in text)

idx = text.find("<rules")
print("Context around <rules:")
print(repr(text[idx:idx+250]))

print()
pattern = '<rules\\s+type="do"\\s*>(.*?)</rules>'
m = re.search(pattern, text, re.DOTALL)
print("Pattern 1 match:", m.group(0)[:100] if m else "NO MATCH")

# Simpler pattern
pattern2 = "<rules type=\"do\">(.*?)</rules>"
m2 = re.search(pattern2, text, re.DOTALL)
print("Pattern 2 match:", m2.group(0)[:100] if m2 else "NO MATCH")

# Even simpler
pattern3 = r"<rules[^>]*>(.*?)</rules>"
m3 = re.search(pattern3, text, re.DOTALL)
print("Pattern 3 (any rules) match:", m3.group(0)[:100] if m3 else "NO MATCH")
