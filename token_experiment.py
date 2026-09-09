from anthropic import Anthropic
from config import settings

client = Anthropic(api_key=settings.anthropic_api_key)

strings = [
    "The cat sat on the mat.",              # plain English
    "std::vector<int> v = {1, 2, 3};",       # C++ code
    "0xDEADBEEF 0xCAFEBABE",                 # hex
    "こんにちは世界",                          # non-English (Japanese)
    "xzq_handle_reset_interrupt_vector",     # weird identifier
]

for s in strings:
    count = client.messages.count_tokens(
        model=settings.model,
        messages=[{"role": "user", "content": s}],
    )
    words = len(s.split())
    print(f"{count.input_tokens:>3} tokens | {words:>2} words | {s}")