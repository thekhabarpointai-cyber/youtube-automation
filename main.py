import os
import re
import html
import time
import asyncio
import subprocess
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

from huggingface_hub import InferenceClient
import edge_tts


# ============================================================
# SETTINGS
# ============================================================

RSS_URL = (
    "https://news.google.com/rss"
    "?hl=en-IN"
    "&gl=IN"
    "&ceid=IN:en"
)

HF_TOKEN = os.getenv("HF_TOKEN")

if not HF_TOKEN:
    raise SystemExit("ERROR: HF_TOKEN secret is missing.")

VOICE = "hi-IN-MadhurNeural"
CHANNEL_NAME = "digital info wallah"

OUTPUT_DIR = Path("generated_video")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SCRIPT_FILE = OUTPUT_DIR / "script.txt"
VOICE_FILE = OUTPUT_DIR / "voice.mp3"
IMAGE_FILE = OUTPUT_DIR / "news.jpg"
VIDEO_FILE = OUTPUT_DIR / "news_video.mp4"


# ============================================================
# FETCH NEWS
# ============================================================

print("========================================")
print("1. FETCHING NEWS")
print("========================================")

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    )
}

request = urllib.request.Request(
    RSS_URL,
    headers=headers
)

data = None

for attempt in range(3):

    try:
        print(f"Attempt {attempt + 1}/3")

        with urllib.request.urlopen(
            request,
            timeout=30
        ) as response:
            data = response.read()

        break

    except Exception as error:

        print(error)

        if attempt < 2:
            time.sleep(10)


if data is None:
    raise SystemExit("ERROR: Could not download Google News RSS.")


root = ET.fromstring(data)

items = root.findall(".//item")

if not items:
    raise SystemExit("ERROR: No news articles found.")


item = items[0]

title = html.unescape(
    item.findtext(
        "title",
        default="आज की बड़ी खबर"
    )
)

description = html.unescape(
    item.findtext(
        "description",
        default=""
    )
)

description = re.sub(
    r"<[^>]+>",
    " ",
    description
)

description = re.sub(
    r"\s+",
    " ",
    description
).strip()


print()
print("NEWS:")
print(title)


# ============================================================
# FIND IMAGE
# ============================================================

print()
print("========================================")
print("2. FINDING NEWS IMAGE")
print("========================================")

image_url = None

for child in item:

    tag = child.tag.lower()

    if (
        "content" in tag
        or "thumbnail" in tag
    ):

        url = child.attrib.get("url")

        if url:
            image_url = url
            break


if image_url:

    try:

        image_request = urllib.request.Request(
            image_url,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        with urllib.request.urlopen(
            image_request,
            timeout=30
        ) as response:

            image_data = response.read()

        with open(
            IMAGE_FILE,
            "wb"
        ) as file:

            file.write(image_data)

        print("News image downloaded.")

    except Exception as error:

        print("Image download failed:")
        print(error)

        image_url = None


if not image_url:
    print("No news image available.")


# ============================================================
# GENERATE HINDI SCRIPT
# ============================================================

print()
print("========================================")
print("3. GENERATING HINDI SCRIPT")
print("========================================")

client = InferenceClient(
    api_key=HF_TOKEN,
    provider="auto"
)

prompt = f"""
आप एक प्रोफेशनल हिंदी न्यूज़ एंकर हैं।

इस खबर के आधार पर लगभग 45 से 60 सेकंड की
सरल और आकर्षक हिंदी न्यूज़ स्क्रिप्ट लिखें।

शीर्षक:
{title}

जानकारी:
{description}

नियम:

- शुरुआत "नमस्कार दोस्तों!" से करें।
- केवल दी गई जानकारी का इस्तेमाल करें।
- कोई तथ्य खुद से न बनाएं।
- आसान बोलने वाली हिंदी लिखें।
- स्क्रिप्ट 45 से 60 सेकंड की रखें।
- अंत में चैनल को सब्सक्राइब करने के लिए कहें।
- Emoji न इस्तेमाल करें।
- केवल स्क्रिप्ट लिखें।
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

script = (
    response
    .choices[0]
    .message
    .content
    .strip()
)

with open(
    SCRIPT_FILE,
    "w",
    encoding="utf-8"
) as file:

    file.write(script)

print()
print("SCRIPT CREATED:")
print(script)


# ============================================================
# GENERATE HINDI VOICE
# ============================================================

print()
print("========================================")
print("4. GENERATING HINDI VOICE")
print("========================================")


async def create_voice():

    voice = edge_tts.Communicate(
        script,
        VOICE
    )

    await voice.save(
        str(VOICE_FILE)
    )


asyncio.run(
    create_voice()
)

print("Voice created.")


# ============================================================
# GET AUDIO DURATION
# ============================================================

print()
print("========================================")
print("5. CHECKING AUDIO LENGTH")
print("========================================")

probe = subprocess.run(
    [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(VOICE_FILE)
    ],
    capture_output=True,
    text=True,
    check=True
)

duration = float(
    probe.stdout.strip()
)

print(
    f"Audio duration: {duration:.2f} seconds"
)


# ============================================================
# CREATE VIDEO
# ============================================================

print()
print("========================================")
print("6. CREATING 9:16 VIDEO")
print("========================================")


if IMAGE_FILE.exists():

    print("Using news image.")

    video_filter = (
        "scale=1080:1920:"
        "force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        "setsar=1,"
        "drawbox="
        "x=0:y=0:w=1080:h=190:"
        "color=black@0.75:t=fill,"
        "drawtext="
        "text='BREAKING NEWS':"
        "fontcolor=white:"
        "fontsize=60:"
        "x=(w-text_w)/2:"
        "y=55,"
        "drawbox="
        "x=0:y=1680:w=1080:h=240:"
        "color=black@0.80:t=fill,"
        "drawtext="
        f"text='{CHANNEL_NAME}':"
        "fontcolor=white:"
        "fontsize=42:"
        "x=(w-text_w)/2:"
        "y=1725"
    )

    command = [
        "ffmpeg",
        "-y",

        "-loop",
        "1",

        "-i",
        str(IMAGE_FILE),

        "-i",
        str(VOICE_FILE),

        "-vf",
        video_filter,

        "-t",
        str(duration),

        "-map",
        "0:v:0",

        "-map",
        "1:a:0",

        "-c:v",
        "libx264",

        "-preset",
        "veryfast",

        "-crf",
        "23",

        "-c:a",
        "aac",

        "-b:a",
        "128k",

        "-pix_fmt",
        "yuv420p",

        "-shortest",

        str(VIDEO_FILE)
    ]

else:

    print("No image found.")
    print("Using black background.")

    video_filter = (
        "drawbox="
        "x=0:y=0:w=1080:h=190:"
        "color=black@0.8:t=fill,"
        "drawtext="
        "text='BREAKING NEWS':"
        "fontcolor=white:"
        "fontsize=60:"
        "x=(w-text_w)/2:"
        "y=55,"
        "drawtext="
        f"text='{CHANNEL_NAME}':"
        "fontcolor=white:"
        "fontsize=42:"
        "x=(w-text_w)/2:"
        "y=1725"
    )

    command = [
        "ffmpeg",
        "-y",

        "-f",
        "lavfi",

        "-i",
        "color=c=black:s=1080x1920:r=30",

        "-i",
        str(VOICE_FILE),

        "-vf",
        video_filter,

        "-t",
        str(duration),

        "-map",
        "0:v:0",

        "-map",
        "1:a:0",

        "-c:v",
        "libx264",

        "-preset",
        "veryfast",

        "-crf",
        "23",

        "-c:a",
        "aac",

        "-b:a",
        "128k",

        "-pix_fmt",
        "yuv420p",

        "-shortest",

        str(VIDEO_FILE)
    ]


print("Rendering video...")

subprocess.run(
    command,
    check=True
)


# ============================================================
# VERIFY
# ============================================================

print()
print("========================================")
print("7. VERIFYING VIDEO")
print("========================================")


if not VIDEO_FILE.exists():
    raise SystemExit(
        "ERROR: Video was not created."
    )


size = VIDEO_FILE.stat().st_size

print(
    f"Video created: {VIDEO_FILE}"
)

print(
    f"Video size: {size / 1024 / 1024:.2f} MB"
)

if size < 10000:
    raise SystemExit(
        "ERROR: Video file is too small."
    )


print()
print("========================================")
print("SUCCESS")
print("========================================")

print()
print("Generated files:")

for file in OUTPUT_DIR.iterdir():

    print(
        file
    )
