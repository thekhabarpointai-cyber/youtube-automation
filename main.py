import os
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import asyncio
import subprocess
import html
import re
import time
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
    raise SystemExit(
        "ERROR: HF_TOKEN GitHub Secret was not found."
    )

VOICE = "hi-IN-MadhurNeural"

CHANNEL_NAME = "digital info wallah"

OUTPUT_DIR = Path("generated_video")

OUTPUT_VIDEO = OUTPUT_DIR / "news_video.mp4"

IMAGE_FILE = OUTPUT_DIR / "news.jpg"

VOICE_FILE = OUTPUT_DIR / "voice.mp3"

SCRIPT_FILE = OUTPUT_DIR / "script.txt"

SUBTITLE_FILE = OUTPUT_DIR / "subtitles.srt"


# ============================================================
# CREATE OUTPUT FOLDER
# ============================================================

OUTPUT_DIR.mkdir(
    exist_ok=True
)


# ============================================================
# STEP 1 — FETCH NEWS
# ============================================================

print()
print("==============================================")
print("STEP 1 — FETCHING LATEST INDIAN NEWS")
print("==============================================")
print()


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

            print(
                f"Attempt {attempt + 1}/3..."
            )

            response = urllib.request.urlopen(
                request,
                timeout=30
            )

            data = response.read()

            print(
                "Google News RSS connected."
            )

            return data

        except Exception as e:

            print(
                "News request failed:"
            )

            print(e)

            if attempt < 2:

                print(
                    "Waiting 10 seconds..."
                )

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


print()
print("NEWS TITLE:")
print(title)


# ============================================================
# STEP 2 — FIND NEWS IMAGE
# ============================================================

print()
print("==============================================")
print("STEP 2 — FINDING NEWS IMAGE")
print("==============================================")
print()


image_url = None


# Try RSS media fields
for child in item:

    tag = child.tag.lower()

    if (
        "content" in tag
        or "thumbnail" in tag
    ):

        url = child.attrib.get(
            "url"
        )

        if url:

            image_url = url

            break


# Try image URL inside description
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

        print(
            "Downloading news image..."
        )

        image_request = urllib.request.Request(
            image_url,
            headers={
                "User-Agent":
                    "Mozilla/5.0"
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

            file.write(
                image_data
            )


        print(
            "News image downloaded."
        )

    except Exception as e:

        print(
            "Image download failed:"
        )

        print(e)

        image_url = None

else:

    print(
        "No news image found."
    )


# ============================================================
# STEP 3 — GENERATE HINDI SCRIPT
# ============================================================

print()
print("==============================================")
print("STEP 3 — GENERATING HINDI SCRIPT")
print("==============================================")
print()


client = InferenceClient(
    api_key=HF_TOKEN,
    provider="auto"
)


prompt = f"""
आप एक प्रोफेशनल भारतीय हिंदी न्यूज़ एंकर हैं।

इस खबर के आधार पर लगभग 45 से 60 सेकंड
की सरल और आकर्षक हिंदी न्यूज़ स्क्रिप्ट लिखें।

खबर का शीर्षक:
{title}

उपलब्ध जानकारी:
{description}

नियम:

1. शुरुआत "नमस्कार दोस्तों!" से करें।
2. खबर का मुख्य विषय स्पष्ट बताएं।
3. केवल उपलब्ध जानकारी का इस्तेमाल करें।
4. कोई तथ्य खुद से न बनाएं।
5. आसान बोलने वाली हिंदी इस्तेमाल करें।
6. स्क्रिप्ट 45 से 60 सेकंड की रखें।
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

    file.write(
        script
    )


print(
    "Hindi script generated."
)


# ============================================================
# STEP 4 — GENERATE HINDI VOICE
# ============================================================

print()
print("==============================================")
print("STEP 4 — GENERATING HINDI VOICE")
print("==============================================")
print()


async def generate_voice():

    communicate = edge_tts.Communicate(
        script,
        VOICE,
        rate="+0%",
        volume="+0%"
    )

    await communicate.save(
        str(VOICE_FILE)
    )


asyncio.run(
    generate_voice()
)


print(
    "Hindi voice generated."
)


# ============================================================
# STEP 5 — CREATE SUBTITLES
# ============================================================

print()
print("==============================================")
print("STEP 5 — CREATING SUBTITLES")
print("==============================================")
print()


def split_text(
    text,
    words_per_line=7
):

    words = text.split()

    lines = []

    current = []

    for word in words:

        current.append(
            word
        )

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


def format_time(
    seconds
):

    hours = int(
        seconds // 3600
    )

    minutes = int(
        (seconds % 3600) // 60
    )

    secs = int(
        seconds % 60
    )

    milliseconds = int(
        (seconds - int(seconds))
        * 1000
    )

    return (
        f"{hours:02d}:"
        f"{minutes:02d}:"
        f"{secs:02d},"
        f"{milliseconds:03d}"
    )


lines = split_text(
    script
)


duration_per_line = 3.5


with open(
    SUBTITLE_FILE,
    "w",
    encoding="utf-8"
) as file:

    for i, line in enumerate(lines):

        start = (
            i
            * duration_per_line
        )

        end = (
            (i + 1)
            * duration_per_line
        )

        file.write(
            f"{i + 1}\n"
        )

        file.write(
            f"{format_time(start)} --> "
            f"{format_time(end)}\n"
        )

        file.write(
            f"{line}\n\n"
        )


print(
    "Subtitles created."
)


# ============================================================
# STEP 6 — CREATE VIDEO
# ============================================================

print()
print("==============================================")
print("STEP 6 — CREATING 9:16 VIDEO")
print("==============================================")
print()


if (
    image_url
    and IMAGE_FILE.exists()
):

    filter_complex = (

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

        "[scene1]"
        "[scene2]"
        "[scene3]"
        "concat=n=3:v=1:a=0,"
        "setpts=PTS-STARTPTS"
        "[video];"

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

        "subtitles="
        f"{SUBTITLE_FILE}:"
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
        str(IMAGE_FILE),

        "-i",
        str(VOICE_FILE),

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

        str(OUTPUT_VIDEO)
    ]


else:

    print(
        "No news image available."
    )

    print(
        "Creating backup video."
    )


    ffmpeg_command = [

        "ffmpeg",

        "-y",

        "-f",
        "lavfi",

        "-i",
        "color=c=black:s=1080x1920",

        "-i",
        str(VOICE_FILE),

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

            "subtitles="
            f"{SUBTITLE_FILE}:"
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

        str(OUTPUT_VIDEO)
    ]


# ============================================================
# STEP 7 — RENDER VIDEO
# ============================================================

print()
print("Rendering video...")
print()


subprocess.run(
    ffmpeg_command,
    check=True
)


# ============================================================
# FINISHED
# ============================================================

print()
print("================================================")
print("        NEWS VIDEO CREATED SUCCESSFULLY")
print("================================================")
print()

print(
    f"Video       : {OUTPUT_VIDEO}"
)

print(
    f"Script      : {SCRIPT_FILE}"
)

print(
    f"Voice       : {VOICE_FILE}"
)

print(
    f"Subtitles   : {SUBTITLE_FILE}"
)

print(
    f"Image       : {IMAGE_FILE}"
)

print()
print("SUCCESS!")
