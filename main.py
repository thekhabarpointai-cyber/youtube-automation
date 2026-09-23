```python
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

HF_TOKEN = os.environ.get("HF_TOKEN")

if not HF_TOKEN:
    raise SystemExit("ERROR: HF_TOKEN secret is missing.")

VOICE = "hi-IN-MadhurNeural"

CHANNEL_NAME = "digital info wallah"

OUTPUT_DIR = Path("generated_video")

OUTPUT_DIR.mkdir(exist_ok=True)

SCRIPT_FILE = OUTPUT_DIR / "script.txt"
VOICE_FILE = OUTPUT_DIR / "voice.mp3"
IMAGE_FILE = OUTPUT_DIR / "news.jpg"
SUBTITLE_FILE = OUTPUT_DIR / "subtitles.srt"
VIDEO_FILE = OUTPUT_DIR / "news_video.mp4"


# ============================================================
# STEP 1 — FETCH NEWS
# ============================================================

print("\n========================================")
print("STEP 1 — FETCHING NEWS")
print("========================================\n")


def fetch_news():

    headers = {
        "User-Agent": (
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        )
    }

    request = urllib.request.Request(
        RSS_URL,
        headers=headers
    )

    for attempt in range(3):

        try:

            print(f"Attempt {attempt + 1}/3")

            with urllib.request.urlopen(
                request,
                timeout=30
            ) as response:

                data = response.read()

            print("Google News connected.")

            return data

        except Exception as error:

            print("News request failed:")
            print(error)

            if attempt < 2:
                print("Waiting 10 seconds...")
                time.sleep(10)

    raise SystemExit(
        "ERROR: Could not fetch Google News."
    )


data = fetch_news()

root = ET.fromstring(data)

items = root.findall(".//item")

if not items:
    raise SystemExit(
        "ERROR: No news articles found."
    )

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

# Remove HTML tags
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

print("\nNEWS TITLE:")
print(title)


# ============================================================
# STEP 2 — FIND IMAGE
# ============================================================

print("\n========================================")
print("STEP 2 — FINDING NEWS IMAGE")
print("========================================\n")


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


if not image_url:

    match = re.search(
        r'https?://[^"\']+\.(?:jpg|jpeg|png|webp)',
        description,
        re.IGNORECASE
    )

    if match:
        image_url = match.group(0)


if image_url:

    try:

        print("Downloading news image...")

        request = urllib.request.Request(
            image_url,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        with urllib.request.urlopen(
            request,
            timeout=30
        ) as response:

            image_data = response.read()

        with open(
            IMAGE_FILE,
            "wb"
        ) as file:

            file.write(image_data)

        print("Image downloaded.")

    except Exception as error:

        print("Image download failed:")
        print(error)

        image_url = None


if not image_url:

    print("No usable news image found.")


# ============================================================
# STEP 3 — GENERATE HINDI SCRIPT
# ============================================================

print("\n========================================")
print("STEP 3 — GENERATING HINDI SCRIPT")
print("========================================\n")


client = InferenceClient(
    api_key=HF_TOKEN,
    provider="auto"
)


prompt = f"""
आप एक प्रोफेशनल भारतीय हिंदी न्यूज़ एंकर हैं।

नीचे दी गई खबर के आधार पर लगभग 45 से 60 सेकंड
की हिंदी न्यूज़ स्क्रिप्ट लिखें।

खबर का शीर्षक:
{title}

खबर की उपलब्ध जानकारी:
{description}

नियम:

1. शुरुआत "नमस्कार दोस्तों!" से करें।
2. खबर का मुख्य विषय साफ बताएं।
3. केवल दी गई जानकारी का इस्तेमाल करें।
4. कोई तथ्य खुद से न बनाएं।
5. आसान और बोलने वाली हिंदी लिखें।
6. स्क्रिप्ट लगभग 45 से 60 सेकंड की हो।
7. अंत में "ऐसी ही खबरों के लिए चैनल को सब्सक्राइब करें" कहें।
8. Emoji का इस्तेमाल न करें।
9. कोई heading या explanation न दें।
10. केवल पूरी न्यूज़ स्क्रिप्ट दें।
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


print("Hindi script created.")

print("\nSCRIPT:")
print(script)


# ============================================================
# STEP 4 — GENERATE HINDI VOICE
# ============================================================

print("\n========================================")
print("STEP 4 — GENERATING HINDI VOICE")
print("========================================\n")


async def generate_voice():

    communicator = edge_tts.Communicate(
        script,
        VOICE,
        rate="+0%",
        volume="+0%"
    )

    await communicator.save(
        str(VOICE_FILE)
    )


asyncio.run(
    generate_voice()
)


print("Hindi voice created.")


# ============================================================
# STEP 5 — GET AUDIO DURATION
# ============================================================

print("\n========================================")
print("STEP 5 — CHECKING AUDIO DURATION")
print("========================================\n")


duration_command = [
    "ffprobe",
    "-v",
    "error",
    "-show_entries",
    "format=duration",
    "-of",
    "default=noprint_wrappers=1:nokey=1",
    str(VOICE_FILE)
]


duration_result = subprocess.run(
    duration_command,
    capture_output=True,
    text=True,
    check=True
)


audio_duration = float(
    duration_result.stdout.strip()
)

print(
    f"Voice duration: {audio_duration:.2f} seconds"
)


# ============================================================
# STEP 6 — CREATE SUBTITLES
# ============================================================

print("\n========================================")
print("STEP 6 — CREATING SUBTITLES")
print("========================================\n")


def split_text(text, words_per_line=8):

    words = text.split()

    lines = []

    current = []

    for word in words:

        current.append(word)

        if len(current) >= words_per_line:

            lines.append(
                " ".join(current)
            )

            current = []

    if current:
        lines.append(
            " ".join(current)
        )

    return lines


def format_time(seconds):

    hours = int(seconds // 3600)

    minutes = int(
        (seconds % 3600) // 60
    )

    secs = int(
        seconds % 60
    )

    milliseconds = int(
        (seconds - int(seconds)) * 1000
    )

    return (
        f"{hours:02d}:"
        f"{minutes:02d}:"
        f"{secs:02d},"
        f"{milliseconds:03d}"
    )


lines = split_text(script)

line_duration = audio_duration / max(
    len(lines),
    1
)


with open(
    SUBTITLE_FILE,
    "w",
    encoding="utf-8"
) as file:

    for index, line in enumerate(lines):

        start = index * line_duration

        end = min(
            (index + 1) * line_duration,
            audio_duration
        )

        file.write(
            f"{index + 1}\n"
        )

        file.write(
            f"{format_time(start)} --> "
            f"{format_time(end)}\n"
        )

        file.write(
            f"{line}\n\n"
        )


print("Subtitles created.")


# ============================================================
# STEP 7 — CREATE VIDEO
# ============================================================

print("\n========================================")
print("STEP 7 — CREATING 9:16 VIDEO")
print("========================================\n")


if image_url and IMAGE_FILE.exists():

    video_input = str(IMAGE_FILE)

    filter_complex = (
        "[0:v]"
        "scale=1080:1920:"
        "force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        "zoompan="
        "z='min(zoom+0.0003,1.12)':"
        "x='iw/2-(iw/zoom/2)':"
        "y='ih/2-(ih/zoom/2)':"
        "d=1:"
        "s=1080x1920:"
        "fps=30,"
        f"trim=duration={audio_duration},"
        "setpts=PTS-STARTPTS,"
        "drawbox="
        "x=0:y=0:w=1080:h=210:"
        "color=black@0.78:t=fill,"
        "drawtext="
        "text='BREAKING NEWS':"
        "fontcolor=white:"
        "fontsize=64:"
        "x=(w-text_w)/2:"
        "y=65,"
        "drawbox="
        "x=0:y=1660:w=1080:h=260:"
        "color=black@0.82:t=fill,"
        "drawtext="
        "text='digital info wallah':"
        "fontcolor=white:"
        "fontsize=42:"
        "x=(w-text_w)/2:"
        "y=1690,"
        "subtitles="
        f"{SUBTITLE_FILE}:"
        "force_style="
        "'FontSize=22,"
        "PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00000000,"
        "Outline=2,"
        "Alignment=2,"
        "MarginV=110'"
    )

    ffmpeg_command = [

        "ffmpeg",
        "-y",

        "-loop",
        "1",

        "-i",
        video_input,

        "-i",
        str(VOICE_FILE),

        "-filter_complex",
        filter_complex,

        "-map",
        "0:v",

        "-map",
        "1:a",

        "-t",
        str(audio_duration),

        "-c:v",
        "libx264",

        "-preset",
        "veryfast",

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

    print("Using black background.")

    ffmpeg_command = [

        "ffmpeg",
        "-y",

        "-f",
        "lavfi",

        "-i",
        "color=c=black:s=1080x1920:r=30",

        "-i",
        str(VOICE_FILE),

        "-vf",

        (
            "drawbox="
            "x=0:y=0:w=1080:h=210:"
            "color=black@0.8:t=fill,"
            "drawtext="
            "text='BREAKING NEWS':"
            "fontcolor=white:"
            "fontsize=64:"
            "x=(w-text_w)/2:"
            "y=65,"
            "drawtext="
            "text='digital info wallah':"
            "fontcolor=white:"
            "fontsize=42:"
            "x=(w-text_w)/2:"
            "y=1690,"
            "subtitles="
            f"{SUBTITLE_FILE}:"
            "force_style="
            "'FontSize=22,"
            "PrimaryColour=&H00FFFFFF,"
            "OutlineColour=&H00000000,"
            "Outline=2,"
            "Alignment=2,"
            "MarginV=110'"
        ),

        "-t",
        str(audio_duration),

        "-map",
        "0:v",

        "-map",
        "1:a",

        "-c:v",
        "libx264",

        "-preset",
        "veryfast",

        "-c:a",
        "aac",

        "-b:a",
        "128k",

        "-pix_fmt",
        "yuv420p",

        "-shortest",

        str(VIDEO_FILE)
    ]


# ============================================================
# STEP 8 — RENDER
# ============================================================

print("Rendering video...")

subprocess.run(
    ffmpeg_command,
    check=True
)


# ============================================================
# STEP 9 — VERIFY VIDEO
# ============================================================

print("\n========================================")
print("VERIFYING VIDEO")
print("========================================\n")


if not VIDEO_FILE.exists():

    raise SystemExit(
        "ERROR: Video was not created."
    )


video_size = VIDEO_FILE.stat().st_size

if video_size < 10000:

    raise SystemExit(
        "ERROR: Video file is too small."
    )


print(
    f"Video created successfully."
)

print(
    f"Video file: {VIDEO_FILE}"
)

print(
    f"Video size: {video_size / (1024 * 1024):.2f} MB"
)


# ============================================================
# FINISHED
# ============================================================

print("\n========================================")
print("        SUCCESS")
print("========================================")

print(
    "\nGenerated files:"
)

for file in OUTPUT_DIR.iterdir():

    print(
        f" - {file.name}"
    )

print(
    "\nYour video is ready:"
)

print(
    str(VIDEO_FILE)
)
```
