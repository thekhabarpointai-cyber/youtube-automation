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

print("\nLatest news:\n")

for i, item in enumerate(items[:5], start=1):
    title = item.findtext("title", default="No title")
    print(f"{i}. {title}")

print("\nNews collection successful!")
