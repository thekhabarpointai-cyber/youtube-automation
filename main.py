import urllib.request
import xml.etree.ElementTree as ET
import subprocess
import re
import os

RSS_URL = "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en"

print("Fetching latest Indian news...")

data = urllib.request.urlopen(RSS_URL, timeout=30).read()
root = ET.fromstring(data)

items = root.findall(".//item")

if not items:
    print("No news found.")
    raise SystemExit(1)

title = items[0].findtext("title", default="आज की बड़ी खबर")

script = f"""
नमस्कार दोस्तों!

आज की बड़ी खबर है — {title}

इस खबर से जुड़ी महत्वपूर्ण जानकारी सामने आई है।
हम आपको इस खबर के मुख्य अपडेट आसान भाषा में बताएंगे।

इस खबर से जुड़े नए अपडेट के लिए हमारे चैनल को सब्सक्राइब करें
और वीडियो को लाइक जरूर करें।

धन्यवाद!
"""

with open("script.txt", "w", encoding="utf-8") as file:
    file.write(script)

print("Hindi script created successfully!")

# Remove unsupported characters for the first audio test
safe_text = re.sub(r"[^\x00-\x7F]+", " ", script)
safe_text = " ".join(safe_text.split())

# Generate temporary speech using espeak
subprocess.run([
    "espeak",
    "-w",
    "voice.wav",
    safe_text
], check=True)

print("Voice generated successfully!")
