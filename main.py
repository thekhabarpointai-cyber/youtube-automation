import os
from huggingface_hub import InferenceClient

token = os.environ.get("HF_TOKEN")

if not token:
    raise SystemExit("HF_TOKEN was not found.")

client = InferenceClient(
    api_key=token,
    provider="auto"
)

print("Connecting to Hugging Face Inference Providers...")

response = client.chat.completions.create(
    model="openai/gpt-oss-120b",
    messages=[
        {
            "role": "user",
            "content": "Write one short Hindi sentence saying: आज भारत की एक बड़ी खबर सामने आई है।"
        }
    ]
)

text = response.choices[0].message.content

print("\n===== HUGGING FACE TEST =====")
print(text)
print("=============================")
print("Hugging Face connection successful!")
