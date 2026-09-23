from pathlib import Path
import subprocess

output = Path("output.mp4")

# Create a 5-second test video
command = [
    "ffmpeg",
    "-y",
    "-f", "lavfi",
    "-i", "color=c=black:s=1080x1920:d=5",
    "-vf", "drawtext=text='YouTube Automation Test':fontcolor=white:fontsize=60:x=(w-text_w)/2:y=(h-text_h)/2",
    "-c:v", "libx264",
    "-pix_fmt", "yuv420p",
    str(output)
]

subprocess.run(command, check=True)

print(f"Video created: {output}")
