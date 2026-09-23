import os
import urllib.request
import xml.etree.ElementTree as ET
from huggingface_hub import InferenceClient

# =========================
# SETTINGS
# =========================

RSS_URL = "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en"

HF_TOKEN = os.environ.get("HF_TOKEN")

if not HF_TOKEN:
    raise SystemExit("HF_TOKEN was not found.")

# =========================
# GET LATEST NEWS
# =========================

print("Fetching latest Indian news...")

data = urllib.request.urlopen(RSS_URL, timeout=30).read()
root = ET.fromstring(data)

items = root.findall(".//item")

if not items:
    raise SystemExit("No news found.")

title = items[0].findtext(
    "title",
    default="आज की बड़ी खबर"
)

print("\nLatest news:")
print(title)

# =========================
# HUGGING FACE AI
# =========================

print("\nGenerating Hindi news script with AI...")

client = InferenceClient(
    api_key=HF_TOKEN,
    provider="auto"
)

prompt = f"""
आप एक प्रोफेशनल भारतीय हिंदी न्यूज़ एंकर हैं।

नीचे दी गई खबर के आधार पर लगभग 45 से 60 सेकंड की
सरल और आकर्षक हिंदी न्यूज़ स्क्रिप्ट लिखें।

खबर:
{title}

स्क्रिप्ट में:
1. शुरुआत "नमस्कार दोस्तों" से करें।
2. खबर का मुख्य विषय स्पष्ट बताएं।
3. आसान हिंदी का इस्तेमाल करें।
4. दर्शकों को महत्वपूर्ण जानकारी दें।
5. अंत में चैनल को सब्सक्राइब करने के लिए कहें।
6. कोई जानकारी खुद से न बनाएं।
7. स्क्रिप्ट में emoji का इस्तेमाल न करें।

केवल हिंदी न्यूज़ स्क्रिप्ट दें।
"""

response = client.chat.completions.create(
    model="openai/gpt-oss-120b",
    messages=[
        {
            "role": "user",
            "content": prompt
        }
    ],
    max_tokens=700
)

script = response.choices[0].message.content

# =========================
# SAVE SCRIPT
# =========================

with open("script.txt", "w", encoding="utf-8") as file:
    file.write(script)

print("\n==============================")
print("AI GENERATED HINDI SCRIPT")
print("==============================\n")
print(script)
print("\n==============================")
print("Script generated successfully!")
