import os
import urllib.request
import xml.etree.ElementTree as ET
import asyncio
import subprocess
from huggingface_hub import InferenceClient
import edge_tts


# =========================================================
# SETTINGS
# =========================================================

RSS_URL = "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en"

HF_TOKEN = os.environ.get("HF_TOKEN")

if not HF_TOKEN:
    raise SystemExit("ERROR: HF_TOKEN was not found.")


# =========================================================
# STEP 1 — FETCH LATEST NEWS
# =========================================================

print("========================================")
print("STEP 1: FETCHING LATEST INDIAN NEWS")
print("========================================")

try:
    data = urllib.request.urlopen(
        RSS_URL,
        timeout=30
    ).read()

    root = ET.fromstring(data)

except Exception as e:
    raise SystemExit(f"ERROR: Could not fetch news: {e}")


items = root.findall(".//item")

if not items:
    raise SystemExit("ERROR: No news found.")


title = items[0].findtext(
    "title",
    default="आज की बड़ी खबर"
)

print("\nLatest news:")
print(title)


# =========================================================
# STEP 2 — GENERATE HINDI SCRIPT WITH AI
# =========================================================

print("\n========================================")
print("STEP 2: GENERATING HINDI SCRIPT")
print("========================================")

client = InferenceClient(
    api_key=HF_TOKEN,
    provider="auto"
)

prompt = f"""
आप एक प्रोफेशनल भारतीय हिंदी न्यूज़ एंकर हैं।

नीचे दी गई खबर के आधार पर लगभग 45 से 60 सेकंड
की सरल, स्पष्ट और आकर्षक हिंदी न्यूज़ स्क्रिप्ट लिखें।

खबर का शीर्षक:
{title}

निर्देश:

1. शुरुआत "नमस्कार दोस्तों!" से करें।
2. खबर का मुख्य विषय स्पष्ट बताएं।
3. केवल उपलब्ध खबर के आधार पर लिखें।
4. कोई तथ्य या आंकड़ा खुद से न बनाएं।
5. आसान और बोलने योग्य हिंदी का इस्तेमाल करें।
6. स्क्रिप्ट लगभग 45-60 सेकंड की हो।
7. अंत में दर्शकों से चैनल को सब्सक्राइब करने के लिए कहें।
8. Emoji का इस्तेमाल न करें।
9. केवल न्यूज़ स्क्रिप्ट दें।
"""

try:

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

    script = response.choices[0].message.content.strip()

except Exception as e:
    raise SystemExit(
        f"ERROR: Hugging Face AI failed: {e}"
    )


print("\n========================================")
print("AI GENERATED HINDI SCRIPT")
print("========================================\n")

print(script)


# =========================================================
# SAVE SCRIPT
# =========================================================

with open(
    "script.txt",
    "w",
    encoding="utf-8"
) as file:
    file.write(script)

print("\nScript saved as script.txt")


# =========================================================
# STEP 3 — GENERATE NATURAL HINDI VOICE
# =========================================================

print("\n========================================")
print("STEP 3: GENERATING HINDI VOICE")
print("========================================")


VOICE = "hi-IN-MadhurNeural"

VOICE_FILE = "voice.mp3"


async def generate_voice():

    communicate = edge_tts.Communicate(
        script,
        VOICE,
        rate="+0%",
        volume="+0%"
    )

    await communicate.save(VOICE_FILE)


try:

    asyncio.run(generate_voice())

except Exception as e:

    raise SystemExit(
        f"ERROR: Hindi voice generation failed: {e}"
    )


print("Hindi voice generated successfully!")
print(f"Voice file: {VOICE_FILE}")


# =========================================================
# STEP 4 — CREATE 9:16 NEWS VIDEO
# =========================================================

print("\n========================================")
print("STEP 4: CREATING 9:16 NEWS VIDEO")
print("========================================")


OUTPUT_VIDEO = "output.mp4"


ffmpeg_command = [
    "ffmpeg",
    "-y",

    # Background
    "-f",
    "lavfi",

    "-i",
    "color=c=black:s=1080x1920",

    # Voice
    "-i",
    VOICE_FILE,

    # Video settings
    "-vf",
    (
        "drawtext="
        "text='BREAKING NEWS':"
        "fontcolor=white:"
        "fontsize=90:"
        "x=(w-text_w)/2:"
        "y=500"
    ),

    "-c:v",
    "libx264",

    "-preset",
    "veryfast",

    "-c:a",
    "aac",

    "-b:a",
    "128k",

    "-shortest",

    "-pix_fmt",
    "yuv420p",

    OUTPUT_VIDEO
]


try:

    subprocess.run(
        ffmpeg_command,
        check=True
    )

except Exception as e:

    raise SystemExit(
        f"ERROR: Video generation failed: {e}"
    )


# =========================================================
# FINISHED
# =========================================================

print("\n========================================")
print("AUTOMATION COMPLETED SUCCESSFULLY")
print("========================================")

print(f"News title : {title}")
print("Script     : script.txt")
print("Voice      : voice.mp3")
print("Video      : output.mp4")

print("\n9:16 Hindi news video created successfully!")
