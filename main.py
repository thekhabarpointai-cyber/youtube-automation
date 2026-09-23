import urllib.request
import xml.etree.ElementTree as ET
import subprocess
from pathlib import Path

RSS_URL = "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en"

print("Fetching latest Indian news...")

data = urllib.request.urlopen(RSS_URL, timeout=30).read()
root = ET.fromstring(data)

items = root.findall(".//item")

if not items:
    raise SystemExit("No news found.")

title = items[0].findtext("title", default="आज की बड़ी खबर")

script = f"""
नमस्कार दोस्तों!

आज की बड़ी खबर है — {title}

इस खबर से जुड़ी महत्वपूर्ण जानकारी सामने आई है।
हम आपको इस खबर के मुख्य अपडेट आसान भाषा में बताएंगे।

ऐसी ही खबरों के लिए हमारे चैनल को सब्सक्राइब करें।

धन्यवाद!
"""

Path("script.txt").write_text(script, encoding="utf-8")

print("Script created.")

# Temporary voice test
subprocess.run(
    ["espeak", "-w", "voice.wav", "Namaskar dosto. Aaj ki badi khabar hai. " + title],
    check=True
)

print("Voice created.")

# Create 9:16 news video
subprocess.run([
    "ffmpeg",
    "-y",
    "-f", "lavfi",
    "-i", "color=c=black:s=1080x1920:d=20",
    "-i", "voice.wav",
    "-vf",
    "drawtext=text='BREAKING NEWS':fontcolor=white:fontsize=90:x=(w-text_w)/2:y=400,"
    "drawtext=text='DIGITAL NEWS':fontcolor=white:fontsize=55:x=(w-text_w)/2:y=600",
    "-c:v", "libx264",
    "-c:a", "aac",
    "-shortest",
    "-pix_fmt", "yuv420p",
    "output.mp4"
], check=True)

print("9:16 news video created successfully!")
