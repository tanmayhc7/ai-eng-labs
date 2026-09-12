# `ask.py` Dissected

Notes from Week 1, Day 2. A line-by-line breakdown of the LLM client, plus the two
bugs found while getting it to run — both worth more than the clean code, because
neither one threw an error.

Final working file:

```python
from anthropic import Anthropic

from config import Settings, get_settings


def build_client(settings: Settings) -> Anthropic:
    return Anthropic(api_key=settings.anthropic_api_key.get_secret_value())


def ask(prompt: str, client: Anthropic, settings: Settings) -> str:
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
    print(ask("In one sentence: what is a context window?", client, settings))


if __name__ == "__main__":
    main()
```

---

## `build_client(settings)` — client construction

```python
def build_client(settings: Settings) -> Anthropic:
    return Anthropic(api_key=settings.anthropic_api_key.get_secret_value())
```

- Takes a validated `Settings` and returns a ready `Anthropic` client.
- **`.get_secret_value()`** is the one place in the codebase the raw API key is
  unwrapped. Everywhere else the `SecretStr` keeps it masked. Unwrapping is deliberate
  and local, not scattered.
- Building the client in its own function (rather than inline in `ask()`) is what lets
  a test inject a fake client later.

## `ask(prompt, client, settings)` — the call

```python
def ask(prompt: str, client: Anthropic, settings: Settings) -> str:
```

**Dependency injection.** `ask()` takes the `client` and `settings` as parameters
instead of constructing them or reaching for globals. This is the design decision that
makes Saturday's mocked tests possible: a test passes a fake client and exercises retry
logic with no real key, no network, no spend. Injection isn't ceremony — it's what
makes the code testable.

```python
    resp = client.messages.create(
        model=settings.model,
        max_tokens=settings.max_tokens,
        messages=[{"role": "user", "content": prompt}],
        extra_body={"temperature": settings.temperature},
    )
```

Every argument comes from config, not a literal — so model, token limit, and
temperature are all switchable without touching code. The `messages` value is a list
of one dict because a conversation is a *sequence*; today it holds a single user turn.

The `extra_body` line is bug #1's fix — see below.

```python
    return "".join(
        block.text for block in resp.content if block.type == "text"
    )
```

`resp.content` is a **list of content blocks**, not a string. This filters to text
blocks, pulls each `.text`, and concatenates. It's written to survive Week 2, when
tool-use responses interleave `text` and `tool_use` blocks in one list — code that did
`resp.content[0].text` would then grab the wrong block. This line was bug #2's location.

## `main()` and the entry-point guard

```python
def main() -> None:
    ...

if __name__ == "__main__":
    main()
```

`main()` wires config → client → call → print. The `if __name__ == "__main__":` guard
runs `main()` only when the file is executed directly (`python ask.py`), not when it's
imported. Next week the tests will `import ask` to test `ask()`; without the guard,
importing would fire a real billed API call. The guard makes the file behave as both a
runnable script and an importable library.

---

## The two bugs — both silent, neither threw

The client was correct on the first raw call (a manual `messages.create` returned a
proper `TextBlock`). But `python ask.py` printed a **blank line** — no output, no
error. Two separate causes, found by isolating the raw call from the wrapper.

### Bug #1 — `temperature` as a direct kwarg (SDK v1.0 breaking change)

```python
# Broke:
client.messages.create(..., temperature=settings.temperature)
# TypeError: Messages.create() got an unexpected keyword argument 'temperature'

# Fixed:
client.messages.create(..., extra_body={"temperature": settings.temperature})
```

The Anthropic Python SDK went to **v1.0.0 (20 Aug 2026)** and removed `temperature`,
`top_p`, and `top_k` from every Messages method signature — they now raise `TypeError`.
The parameters are gone from the *method*, not the *API*: models that predate the change
still honor them, passed via `extra_body`, which the SDK merges into the request JSON
untouched. Confusingly, the Messages API reference **still documents** `temperature`
with a default of 1.0 and range 0.0–1.0, so nearly every tutorial online is now wrong on
this point.

Caveat for M10 defense: whether a call site should drop the parameter or route it
through `extra_body` depends on the target model. Haiku 4.5 (the Week 1 default) still
honors it, so `extra_body` is correct here.

### Bug #2 — wrong block-type string

```python
# Broke (silently):
... if block.type == "output_text"

# Fixed:
... if block.type == "text"
```

The Anthropic block type is `"text"`. `"output_text"` is the **OpenAI** Responses-API
name — an easy cross-wire, especially with an OpenAI-compatible gateway (OmniRoute) in
mind. The comprehension tested every block against a string that never matched, yielded
nothing, and `"".join([])` returned `""`, which `print()` rendered as a blank line.
Filtering to zero matches is perfectly legal, so nothing crashed.

### The lesson that ties both together

**Neither bug threw. Both produced an innocent-looking empty string.** An LLM pipeline
fails quietly far more often than it fails loudly — a wrong assumption becomes `""` or
`None`, not a traceback. This is exactly why:

- per-call logging (Wednesday) should log `stop_reason`, token counts, **and**
  `len(resp.content)` + block types, so a zero-match filter announces itself;
- eval harnesses (Week 3) exist at all — you can't trust that output *looks* fine.

Diagnostic method that found both: isolate the raw `messages.create()` call from the
wrapper. The raw call succeeded (ruling out key/config/network), which localized the
fault to the two lines the wrapper added — the `temperature` kwarg and the filter
string.
