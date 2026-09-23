import urllib.request
import xml.etree.ElementTree as ET

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

print("\n===== GENERATED HINDI SCRIPT =====\n")
print(script)

with open("script.txt", "w", encoding="utf-8") as file:
    file.write(script)

print("==================================")
print("Hindi script created successfully!")
