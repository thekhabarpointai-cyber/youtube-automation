import os
import re
import html
import time
import asyncio
import subprocess
import urllib.request
import urllib.parse
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


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    )
}


# ============================================================
# DOWNLOAD URL
# ============================================================

def download_url(url, timeout=30):

    request = urllib.request.Request(
        url,
        headers=HEADERS
    )

    with urllib.request.urlopen(
        request,
        timeout=timeout
    ) as response:

        return response.read()


# ============================================================
# FETCH NEWS
# ============================================================

print("========================================")
print("1. FETCHING NEWS")
print("========================================")

data = None

for attempt in range(3):

    try:

        print(f"Attempt {attempt + 1}/3")

        data = download_url(
            RSS_URL
        )

        break

    except Exception as error:

        print("RSS error:")
        print(error)

        if attempt < 2:
            time.sleep(10)


if data is None:

    raise SystemExit(
        "ERROR: Could not fetch Google News."
    )


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

article_link = item.findtext(
    "link",
    default=""
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
print("NEWS TITLE:")
print(title)

print()
print("ARTICLE LINK:")
print(article_link)


# ============================================================
# FIND IMAGE FROM ARTICLE
# ============================================================

print()
print("========================================")
print("2. FINDING ARTICLE IMAGE")
print("========================================")


image_url = None


# ------------------------------------------------------------
# METHOD 1 — CHECK RSS MEDIA
# ------------------------------------------------------------

for child in item:

    tag = child.tag.lower()

    if (
        "content" in tag
        or "thumbnail" in tag
    ):

        possible_url = child.attrib.get(
            "url"
        )

        if possible_url:

            image_url = possible_url

            print(
                "Image found in RSS."
            )

            break


# ------------------------------------------------------------
# METHOD 2 — OPEN ARTICLE AND FIND OG:IMAGE
# ------------------------------------------------------------

if not image_url and article_link:

    try:

        print(
            "Opening news article..."
        )

        article_html = download_url(
            article_link
        ).decode(
            "utf-8",
            errors="ignore"
        )

        # og:image
        patterns = [

            r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)',
            
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',

            r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)',

            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']twitter:image["\']'
        ]


        for pattern in patterns:

            match = re.search(
                pattern,
                article_html,
                re.IGNORECASE
            )

            if match:

                image_url = html.unescape(
                    match.group(1)
                )

                image_url = urllib.parse.urljoin(
                    article_link,
                    image_url
                )

                print(
                    "Article image found."
                )

                break


    except Exception as error:

        print(
            "Could not read article page:"
        )

        print(error)


# ============================================================
# DOWNLOAD IMAGE
# ============================================================

if image_url:

    try:

        print()
        print(
            "Downloading news image..."
        )

        image_data = download_url(
            image_url
        )

        with open(
            IMAGE_FILE,
            "wb"
        ) as file:

            file.write(
                image_data
            )

        print(
            "News image saved:"
        )

        print(
            IMAGE_FILE
        )

    except Exception as error:

        print(
            "Image download failed:"
        )

        print(error)

        image_url = None


# ============================================================
# FALLBACK IMAGE
# ============================================================

if not image_url:

    print()
    print(
        "WARNING: No article image found."
    )

    print(
        "Video will use a generated news background."
    )


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
आप एक प्रोफेशनल भारतीय हिंदी न्यूज़ एंकर हैं।

इस खबर के आधार पर लगभग 45 से 60 सेकंड की
सरल और आकर्षक हिंदी न्यूज़ स्क्रिप्ट लिखें।

खबर का शीर्षक:
{title}

खबर की जानकारी:
{description}

नियम:

1. शुरुआत "नमस्कार दोस्तों!" से करें।
2. खबर का मुख्य विषय स्पष्ट बताएं।
3. केवल उपलब्ध जानकारी का इस्तेमाल करें।
4. कोई तथ्य खुद से न बनाएं।
5. आसान बोलने वाली हिंदी इस्तेमाल करें।
6. 45 से 60 सेकंड की स्क्रिप्ट रखें।
7. अंत में चैनल को सब्सक्राइब करने के लिए कहें।
8. Emoji का इस्तेमाल न करें।
9. केवल न्यूज़ स्क्रिप्ट दें।
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


print()
print("SCRIPT:")
print(script)


# ============================================================
# GENERATE VOICE
# ============================================================

print()
print("========================================")
print("4. GENERATING HINDI VOICE")
print("========================================")


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


print(
    "Hindi voice created."
)


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

    print(
        "Using actual news image."
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

        (
            "scale=1080:1920:"
            "force_original_aspect_ratio=increase,"
            "crop=1080:1920,"
            "setsar=1,"
            "drawbox="
            "x=0:y=0:"
            "w=1080:h=190:"
            "color=black@0.70:t=fill,"
            "drawtext="
            "text='BREAKING NEWS':"
            "fontcolor=white:"
            "fontsize=60:"
            "x=(w-text_w)/2:"
            "y=55,"
            "drawbox="
            "x=0:y=1680:"
            "w=1080:h=240:"
            "color=black@0.80:t=fill,"
            "drawtext="
            "text='digital info wallah':"
            "fontcolor=white:"
            "fontsize=42:"
            "x=(w-text_w)/2:"
            "y=1725"
        ),

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

    print(
        "Using generated gradient-style background."
    )

    command = [

        "ffmpeg",
        "-y",

        "-f",
        "lavfi",

        "-i",
        "color=c=darkblue:"
        "s=1080x1920:"
        "r=30",

        "-i",
        str(VOICE_FILE),

        "-vf",

        (
            "drawbox="
            "x=0:y=0:"
            "w=1080:h=190:"
            "color=black@0.8:t=fill,"
            "drawtext="
            "text='BREAKING NEWS':"
            "fontcolor=white:"
            "fontsize=60:"
            "x=(w-text_w)/2:"
            "y=55,"
            "drawtext="
            "text='digital info wallah':"
            "fontcolor=white:"
            "fontsize=42:"
            "x=(w-text_w)/2:"
            "y=1725"
        ),

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


# ============================================================
# RENDER
# ============================================================

print()
print(
    "Rendering video..."
)


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

for file in OUTPUT_DIR.iterdir():

    print(
        f"Created: {file.name}"
    )
