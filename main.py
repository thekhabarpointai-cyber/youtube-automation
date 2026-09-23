import os
import urllib.request
import xml.etree.ElementTree as ET
import asyncio
import subprocess
import html
import re

from huggingface_hub import InferenceClient
import edge_tts


# =========================================================
# SETTINGS
# =========================================================

RSS_URL = "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en"

HF_TOKEN = os.environ.get("HF_TOKEN")

if not HF_TOKEN:
    raise SystemExit("ERROR: HF_TOKEN was not found.")

VOICE = "hi-IN-MadhurNeural"


# =========================================================
# STEP 1 — FETCH NEWS
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


item = items[0]

title = item.findtext(
    "title",
    default="आज की बड़ी खबर"
)

description = item.findtext(
    "description",
    default=""
)

link = item.findtext(
    "link",
    default=""
)

title = html.unescape(title)
description = html.unescape(description)

print("\nLatest news:")
print(title)


# =========================================================
# STEP 2 — FIND IMAGE URL
# =========================================================

print("\n========================================")
print("STEP 2: FINDING NEWS IMAGE")
print("========================================")

image_url = None

# Look for media:content / media:thumbnail
for child in item:

    tag = child.tag.lower()

    if "content" in tag or "thumbnail" in tag:

        url = child.attrib.get("url")

        if url:
            image_url = url
            break


# Also search the description for an image URL
if not image_url:

    image_match = re.search(
        r'https?://[^"\']+\.(?:jpg|jpeg|png|webp)',
        description,
        re.IGNORECASE
    )

    if image_match:
        image_url = image_match.group(0)


if image_url:

    print("News image found:")
    print(image_url)

    try:

        urllib.request.urlretrieve(
            image_url,
            "news.jpg"
        )

        print("News image downloaded successfully.")

    except Exception as e:

        print("Could not download RSS image.")
        print(e)
        image_url = None

else:

    print("No image was found in RSS.")


# =========================================================
# STEP 3 — GENERATE AI HINDI SCRIPT
# =========================================================

print("\n========================================")
print("STEP 3: GENERATING HINDI SCRIPT")
print("========================================")

client = InferenceClient(
    api_key=HF_TOKEN,
    provider="auto"
)


prompt = f"""
आप एक प्रोफेशनल भारतीय हिंदी न्यूज़ एंकर हैं।

इस खबर के आधार पर लगभग 45 से 60 सेकंड की
सरल और स्पष्ट हिंदी न्यूज़ स्क्रिप्ट लिखें।

खबर का शीर्षक:
{title}

उपलब्ध जानकारी:
{description}

निर्देश:

1. शुरुआत "नमस्कार दोस्तों!" से करें।
2. खबर का मुख्य विषय बताएं।
3. केवल उपलब्ध जानकारी का इस्तेमाल करें।
4. कोई तथ्य खुद से न बनाएं।
5. आसान बोलने वाली हिंदी इस्तेमाल करें।
6. स्क्रिप्ट 45-60 सेकंड की हो।
7. अंत में दर्शकों को चैनल सब्सक्राइब करने के लिए कहें।
8. Emoji का इस्तेमाल न करें।
9. केवल स्क्रिप्ट दें।
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
        f"ERROR: Hugging Face failed: {e}"
    )


print("\n========================================")
print("AI GENERATED HINDI SCRIPT")
print("========================================")

print(script)


with open(
    "script.txt",
    "w",
    encoding="utf-8"
) as file:

    file.write(script)


# =========================================================
# STEP 4 — GENERATE HINDI VOICE
# =========================================================

print("\n========================================")
print("STEP 4: GENERATING HINDI VOICE")
print("========================================")


async def generate_voice():

    communicate = edge_tts.Communicate(
        script,
        VOICE,
        rate="+0%",
        volume="+0%"
    )

    await communicate.save(
        "voice.mp3"
    )


try:

    asyncio.run(
        generate_voice()
    )

except Exception as e:

    raise SystemExit(
        f"ERROR: Voice generation failed: {e}"
    )


print("Hindi voice created successfully.")


# =========================================================
# STEP 5 — CREATE VIDEO
# =========================================================

print("\n========================================")
print("STEP 5: CREATING 9:16 NEWS VIDEO")
print("========================================")


OUTPUT_VIDEO = "output.mp4"


if image_url and os.path.exists("news.jpg"):

    print("Creating video with news image.")

    ffmpeg_command = [

        "ffmpeg",
        "-y",

        "-loop",
        "1",

        "-i",
        "news.jpg",

        "-i",
        "voice.mp3",

        "-vf",

        (
            "scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,"
            "drawbox=x=0:y=0:w=1080:h=230:color=black@0.75:t=fill,"
            "drawbox=x=0:y=1690:w=1080:h=230:color=black@0.75:t=fill,"
            "drawtext="
            "text='BREAKING NEWS':"
            "fontcolor=white:"
            "fontsize=70:"
            "x=(w-text_w)/2:"
            "y=75"
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

else:

    print("Creating video with black background.")

    ffmpeg_command = [

        "ffmpeg",
        "-y",

        "-f",
        "lavfi",

        "-i",
        "color=c=black:s=1080x1920",

        "-i",
        "voice.mp3",

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
        f"ERROR: FFmpeg failed: {e}"
    )


# =========================================================
# FINISHED
# =========================================================

print("\n========================================")
print("AUTOMATION COMPLETED")
print("========================================")

print(f"News       : {title}")
print("Script     : script.txt")
print("Voice      : voice.mp3")
print("Image      : news.jpg")
print("Video      : output.mp4")

print("\nSUCCESS!")
