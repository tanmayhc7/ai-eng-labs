from anthropic import Anthropic
from config import settings

client = Anthropic(api_key=settings.anthropic_api_key)

prompt = "Write one sentence about the ocean."

def ask(prompt: str, temperature: float) -> str:
    resp = client.messages.create(
        model=settings.model,
        max_tokens=100,
        messages=[{"role": "user", "content": prompt}],
        extra_body={"temperature": temperature},
    )
    return resp.content[0].text

print("=== temperature = 0 (run 5x) ===")
for i in range(5):
    print(f"{i+1}: {ask(prompt, 0.0)}")

print("\n=== temperature = 1 (run 5x) ===")
for i in range(5):
    print(f"{i+1}: {ask(prompt, 1.0)}")
