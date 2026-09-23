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

print("STEP 1: Fetching latest Indian news...")

data = urllib.request.urlopen(
    RSS_URL,
    timeout=30
).read()

root = ET.fromstring(data)

items = root.findall(".//item")

if not items:
    raise SystemExit("ERROR: No news found.")

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

print("News:")
print(title)


# =========================================================
# STEP 2 — FIND NEWS IMAGE
# =========================================================

print("\nSTEP 2: Finding news image...")

image_url = None

for child in item:

    tag = child.tag.lower()

    if "content" in tag or "thumbnail" in tag:

        url = child.attrib.get("url")

        if url:
            image_url = url
            break


if not image_url:

    image_match = re.search(
        r'https?://[^"\']+\.(?:jpg|jpeg|png|webp)',
        description,
        re.IGNORECASE
    )

    if image_match:
        image_url = image_match.group(0)


if image_url:

    try:

        urllib.request.urlretrieve(
            image_url,
            "news.jpg"
        )

        print("News image downloaded.")

    except Exception as e:

        print("Image download failed:")
        print(e)

        image_url = None

else:

    print("No news image found.")


# =========================================================
# STEP 3 — AI NEWS SCRIPT
# =========================================================

print("\nSTEP 3: Generating Hindi news script...")

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

नियम:

1. शुरुआत "नमस्कार दोस्तों!" से करें।
2. खबर का मुख्य विषय स्पष्ट बताएं।
3. केवल उपलब्ध जानकारी का उपयोग करें।
4. कोई तथ्य खुद से न बनाएं।
5. आसान बोलने वाली हिंदी इस्तेमाल करें।
6. स्क्रिप्ट 45 से 60 सेकंड की हो।
7. अंत में चैनल को सब्सक्राइब करने के लिए कहें।
8. Emoji का इस्तेमाल न करें।
9. केवल स्क्रिप्ट दें।
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

script = response.choices[0].message.content.strip()

with open(
    "script.txt",
    "w",
    encoding="utf-8"
) as file:
    file.write(script)

print("Hindi script generated.")


# =========================================================
# STEP 4 — GENERATE HINDI VOICE
# =========================================================

print("\nSTEP 4: Generating Hindi voice...")


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


asyncio.run(
    generate_voice()
)

print("Hindi voice generated.")


# =========================================================
# STEP 5 — CREATE SUBTITLE FILE
# =========================================================

print("\nSTEP 5: Creating Hindi subtitles...")


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


subtitle_lines = split_text(
    script,
    words_per_line=8
)


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


# Approximate timing based on number of lines
duration_per_line = 3.5


with open(
    "subtitles.srt",
    "w",
    encoding="utf-8"
) as subtitle_file:

    for i, line in enumerate(
        subtitle_lines
    ):

        start = i * duration_per_line

        end = (
            (i + 1)
            * duration_per_line
        )

        subtitle_file.write(
            f"{i + 1}\n"
        )

        subtitle_file.write(
            f"{format_time(start)} --> "
            f"{format_time(end)}\n"
        )

        subtitle_file.write(
            f"{line}\n\n"
        )


print("Hindi subtitles created.")


# =========================================================
# STEP 6 — CREATE FINAL 9:16 VIDEO
# =========================================================

print("\nSTEP 6: Creating final 9:16 video...")


if image_url and os.path.exists(
    "news.jpg"
):

    video_input = "news.jpg"

    ffmpeg_command = [

        "ffmpeg",
        "-y",

        "-loop",
        "1",

        "-i",
        video_input,

        "-i",
        "voice.mp3",

        "-vf",

        (
            "scale=1080:1920:"
            "force_original_aspect_ratio=increase,"
            "crop=1080:1920,"
            "drawbox="
            "x=0:y=0:"
            "w=1080:h=220:"
            "color=black@0.75:t=fill,"
            "drawtext="
            "text='BREAKING NEWS':"
            "fontcolor=white:"
            "fontsize=70:"
            "x=(w-text_w)/2:"
            "y=70,"
            "subtitles=subtitles.srt:"
            "force_style="
            "'FontName=DejaVu Sans,"
            "FontSize=22,"
            "PrimaryColour=&H00FFFFFF,"
            "OutlineColour=&H00000000,"
            "Outline=2,"
            "Alignment=2,"
            "MarginV=180'"
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

        "output.mp4"
    ]

else:

    print(
        "No image available. "
        "Using black background."
    )

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
            "y=400,"
            "subtitles=subtitles.srt:"
            "force_style="
            "'FontSize=22,"
            "PrimaryColour=&H00FFFFFF,"
            "OutlineColour=&H00000000,"
            "Outline=2,"
            "Alignment=2,"
            "MarginV=180'"
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

        "output.mp4"
    ]


subprocess.run(
    ffmpeg_command,
    check=True
)


# =========================================================
# FINISHED
# =========================================================

print("\n================================")
print("AUTOMATION COMPLETED")
print("================================")

print("script.txt       created")
print("voice.mp3        created")
print("subtitles.srt    created")
print("output.mp4       created")

print("\n9:16 Hindi news video with captions is ready!")
