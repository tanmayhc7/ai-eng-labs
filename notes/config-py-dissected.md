# `config.py` Dissected

Notes from Week 1, Day 2. A line-by-line breakdown of the typed configuration
layer. The one-line summary: this file turns configuration from scattered,
untyped, unvalidated `os.environ` string lookups into a single typed object that
fails loudly at startup if anything is wrong.

The full file:

```python
from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    anthropic_api_key: SecretStr
    model: str = "claude-haiku-4-5-20251001"
    max_tokens: int = Field(default=512, ge=1, le=8192)
    temperature: float = Field(default=1.0, ge=0.0, le=1.0)


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

---

## Imports

```python
from functools import lru_cache
```

`lru_cache` is a decorator from the standard library. Used here to make
`get_settings()` a lazy singleton — the environment is read and validated once,
then the same object is handed back on every later call.

```python
from pydantic import Field, SecretStr
```

- `Field` attaches validation rules and metadata to a field, beyond what the bare
  type annotation gives.
- `SecretStr` wraps a sensitive value so it renders as `**********` if the object
  ever hits a log, traceback, or `print()`.

```python
from pydantic_settings import BaseSettings, SettingsConfigDict
```

The gotcha import. In Pydantic v2, `BaseSettings` was moved *out* of `pydantic`
into the separate `pydantic-settings` package. Tutorials that do
`from pydantic import BaseSettings` are pre-v2 and fail on import. `SettingsConfigDict`
is the v2 way to configure a settings class (it replaces the old inner
`class Config:` from v1).

---

## The class and its config

```python
class Settings(BaseSettings):
```

Subclassing `BaseSettings` (not plain `BaseModel`) is what gives the class its
superpower: it automatically reads values from the environment and from a `.env`
file, mapping variable names to fields.

```python
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
```

Configures *how* the settings class loads:

- **`env_file=".env"`** — read variables from a `.env` file in addition to the real
  process environment.
- **`env_file_encoding="utf-8"`** — how to decode that file.
- **`extra="ignore"`** — what to do with environment variables that don't map to any
  field on the class. The real environment is full of noise (`PATH`, `HOME`, `SHELL`,
  …); `"ignore"` drops the unknowns silently. The alternatives:
  - `"forbid"` — raise on any unknown field. Right for a *closed* schema (data you
    control, where an extra field is a bug), fatal for `BaseSettings` because it would
    choke on `PATH`.
  - `"allow"` — accept unknowns as arbitrary attributes. Defeats the point of a typed
    schema.

  Rule of thumb: `"ignore"` for an **open** source you don't control (the
  environment); `"forbid"` for a **closed** schema you're asserting a contract on
  (e.g. an LLM's JSON output in Week 2).

---

## The fields

```python
    anthropic_api_key: SecretStr
```

- **No default → required.** If it's absent from the environment and `.env`,
  constructing `Settings()` raises a `ValidationError` naming this field — before any
  network call. This is the fail-fast behavior proven in the Step 5 check.
- **`SecretStr` type** — renders masked anywhere it's accidentally displayed. The real
  bytes come out only via a deliberate `.get_secret_value()`. Converts "don't log the
  key" from a rule you must remember into a default the type enforces.
- Maps from the env var `ANTHROPIC_API_KEY` (case-insensitive, name-based).

```python
    model: str = "claude-haiku-4-5-20251001"
```

A plain field with a default. Overridable via a `MODEL` env var. Defaulted to Haiku
4.5 deliberately: Week 1 is hundreds of throwaway calls where output quality is
irrelevant, so paying frontier-model prices would burn the budget. Because `model` is
config and not a hardcoded literal, it can be switched per-task later without touching
code.

```python
    max_tokens: int = Field(default=512, ge=1, le=8192)
    temperature: float = Field(default=1.0, ge=0.0, le=1.0)
```

Fields with both a default *and* validation constraints, which is why they use the
`Field()` form (you can't write `max_tokens: int = 512, ge=1` — not valid syntax;
`Field()` bundles default + rules into one call).

- **`default=`** — same role as `= 512` would have on its own.
- **`ge` / `le`** — **g**reater-than-or-**e**qual / **l**ess-than-or-**e**qual. So
  `max_tokens ∈ [1, 8192]` and `temperature ∈ [0.0, 1.0]`.
- Set `TEMPERATURE=5` and construction fails at startup with a message naming the
  field and its bound.

Other `Field()` validators worth knowing: `gt`/`lt` (strict), `multiple_of` for
numbers; `min_length`/`max_length`/`pattern` for strings and collections;
`description`, `alias`, `examples` for docs and tooling.

**C++ analogy:** the type annotation (`int`) is like the declared type of a member;
`Field(ge=..., le=...)` is the invariant you'd otherwise assert in the constructor
(`assert(1 <= max_tokens && max_tokens <= 8192)`). Pydantic moves that assertion into
a declarative annotation and runs it automatically at construction, so no object of
this type can exist in an invalid state.

---

## The accessor

```python
@lru_cache
def get_settings() -> Settings:
    return Settings()
```

`Settings()` reads and validates the environment. Wrapping the accessor in
`@lru_cache` makes it a lazy singleton: the first call builds and caches the object;
every later call returns the same instance. Cheap, and it guarantees config can't
drift mid-run — one `Settings` for the whole process.

Returning `Settings` as a value (rather than reaching for a global) is also what makes
the rest of the code testable: `ask()` takes a `Settings` as a parameter, so tests can
construct a fake one pointing at a mocked client and exercise retry logic with no real
key, no network, and no spend.

---

## What the file achieves, summarized

A **validated, typed, self-documenting, leak-resistant, injectable** configuration
boundary. Once you hold a `Settings`, it is guaranteed well-formed — downstream code
never has to re-check. That boundary is a large part of what separates a script from
software.

The one discipline it costs: every required field added here needs a matching
placeholder line in `.env.example`, in the same commit. Nothing enforces that sync but
you.
