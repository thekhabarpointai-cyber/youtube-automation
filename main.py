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
CHANNEL_NAME = "digital info wallah"

OUTPUT = "output.mp4"


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
    raise SystemExit("No news found.")

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

print("NEWS:")
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
# STEP 3 — AI HINDI SCRIPT
# =========================================================

print("\nSTEP 3: Generating Hindi news script...")

client = InferenceClient(
    api_key=HF_TOKEN,
    provider="auto"
)

prompt = f"""
आप एक प्रोफेशनल भारतीय हिंदी न्यूज़ एंकर हैं।

इस खबर के आधार पर 45 से 60 सेकंड की
सरल और आकर्षक हिंदी न्यूज़ स्क्रिप्ट लिखें।

खबर:
{title}

जानकारी:
{description}

नियम:

1. शुरुआत "नमस्कार दोस्तों!" से करें।
2. खबर का मुख्य विषय स्पष्ट बताएं।
3. केवल उपलब्ध जानकारी का इस्तेमाल करें।
4. कोई तथ्य खुद से न बनाएं।
5. आसान बोलने वाली हिंदी इस्तेमाल करें।
6. स्क्रिप्ट 45 से 60 सेकंड की हो।
7. अंत में चैनल को सब्सक्राइब करने के लिए कहें।
8. Emoji इस्तेमाल न करें।
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
) as f:
    f.write(script)

print("Hindi script generated.")


# =========================================================
# STEP 4 — HINDI VOICE
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
# STEP 5 — SUBTITLES
# =========================================================

print("\nSTEP 5: Creating subtitles...")


def split_text(text, words_per_line=7):

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

    secs = int(seconds % 60)

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

duration_per_line = 3.5

with open(
    "subtitles.srt",
    "w",
    encoding="utf-8"
) as f:

    for i, line in enumerate(lines):

        start = i * duration_per_line

        end = (
            (i + 1)
            * duration_per_line
        )

        f.write(
            f"{i + 1}\n"
        )

        f.write(
            f"{format_time(start)} --> "
            f"{format_time(end)}\n"
        )

        f.write(
            f"{line}\n\n"
        )

print("Subtitles created.")


# =========================================================
# STEP 6 — CREATE 3 VISUAL SCENES
# =========================================================

print("\nSTEP 6: Creating 3-scene professional video...")


if image_url and os.path.exists("news.jpg"):

    print("Creating multiple visual scenes...")

    filter_complex = (

        # =================================================
        # SCENE 1
        # Full image with slow zoom
        # =================================================

        "[0:v]"
        "scale=1080:1920:"
        "force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        "zoompan="
        "z='min(zoom+0.0005,1.08)':"
        "x='iw/2-(iw/zoom/2)':"
        "y='ih/2-(ih/zoom/2)':"
        "d=150:"
        "s=1080x1920:"
        "fps=30,"
        "trim=duration=5,"
        "setpts=PTS-STARTPTS"
        "[scene1];"


        # =================================================
        # SCENE 2
        # Zoomed image
        # =================================================

        "[0:v]"
        "scale=1300:2300:"
        "force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        "zoompan="
        "z='min(zoom+0.0008,1.15)':"
        "x='iw/2-(iw/zoom/2)':"
        "y='ih/2-(ih/zoom/2)':"
        "d=150:"
        "s=1080x1920:"
        "fps=30,"
        "trim=duration=5,"
        "setpts=PTS-STARTPTS"
        "[scene2];"


        # =================================================
        # SCENE 3
        # Different crop
        # =================================================

        "[0:v]"
        "scale=1500:2600:"
        "force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        "zoompan="
        "z='min(zoom+0.0006,1.10)':"
        "x='(iw-iw/zoom)*0.25':"
        "y='(ih-ih/zoom)*0.35':"
        "d=150:"
        "s=1080x1920:"
        "fps=30,"
        "trim=duration=5,"
        "setpts=PTS-STARTPTS"
        "[scene3];"


        # =================================================
        # JOIN THREE SCENES
        # =================================================

        "[scene1]"
        "[scene2]"
        "[scene3]"
        "concat=n=3:v=1:a=0,"
        "setpts=PTS-STARTPTS"
        "[video];"


        # =================================================
        # NEWS GRAPHICS
        # =================================================

        "[video]"

        "drawbox="
        "x=0:y=0:"
        "w=1080:h=230:"
        "color=black@0.78:t=fill,"

        "drawtext="
        "text='BREAKING NEWS':"
        "fontcolor=white:"
        "fontsize=68:"
        "x=(w-text_w)/2:"
        "y=65,"

        "drawbox="
        "x=0:y=1650:"
        "w=1080:h=270:"
        "color=black@0.82:t=fill,"

        "drawtext="
        "text='digital info wallah':"
        "fontcolor=white:"
        "fontsize=45:"
        "x=(w-text_w)/2:"
        "y=1680,"

        "subtitles=subtitles.srt:"
        "force_style="
        "'FontSize=24,"
        "PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00000000,"
        "Outline=2,"
        "Alignment=2,"
        "MarginV=120'"
        "[final]"
    )


    ffmpeg_command = [

        "ffmpeg",
        "-y",

        "-loop",
        "1",

        "-i",
        "news.jpg",

        "-i",
        "voice.mp3",

        "-filter_complex",
        filter_complex,

        "-map",
        "[final]",

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

        "-shortest",

        "-pix_fmt",
        "yuv420p",

        OUTPUT
    ]


else:

    print("No image found. Creating backup video.")

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
            "drawbox="
            "x=0:y=0:"
            "w=1080:h=230:"
            "color=black@0.8:t=fill,"

            "drawtext="
            "text='BREAKING NEWS':"
            "fontcolor=white:"
            "fontsize=68:"
            "x=(w-text_w)/2:"
            "y=65,"

            "drawtext="
            "text='digital info wallah':"
            "fontcolor=white:"
            "fontsize=45:"
            "x=(w-text_w)/2:"
            "y=1680,"

            "subtitles=subtitles.srt:"
            "force_style="
            "'FontSize=24,"
            "PrimaryColour=&H00FFFFFF,"
            "OutlineColour=&H00000000,"
            "Outline=2,"
            "Alignment=2,"
            "MarginV=120'"
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

        OUTPUT
    ]


# =========================================================
# RUN FFMPEG
# =========================================================

subprocess.run(
    ffmpeg_command,
    check=True
)


# =========================================================
# FINISHED
# =========================================================

print("\n========================================")
print("3-SCENE NEWS VIDEO CREATED")
print("========================================")

print("Script      : script.txt")
print("Voice       : voice.mp3")
print("Subtitles   : subtitles.srt")
print("Image       : news.jpg")
print("Final video : output.mp4")

print("\nSUCCESS!")
