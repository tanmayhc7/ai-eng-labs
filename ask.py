from anthropic import Anthropic
from config import Settings, get_settings

def build_client(settings: Settings) -> Anthropic:
    return Anthropic(api_key=settings.anthropic_api_key.get_secret_value())

def ask(prompt: str, client: Anthropic,settings: Settings) -> str:
    resp = client.messages.create(
        model=settings.model,
        max_tokens=settings.max_tokens,
        messages=[{"role": "user", "content": prompt}],
        extra_body={"temperature": settings.temperature},
    )
    return "".join(
        block.text for block in resp.content if block.type == "text"
    )

def main() -> None:
    settings = get_settings()
    client = build_client(settings)
    print(ask("In one sentence: what is context window?", client, settings))

if __name__ == "__main__":
    main()