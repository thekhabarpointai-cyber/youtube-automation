import os

token = os.environ.get("HF_TOKEN")

if not token:
    raise SystemExit("HF_TOKEN was not found.")

print("HF_TOKEN is available.")
print("Token is securely loaded from GitHub Secrets.")
