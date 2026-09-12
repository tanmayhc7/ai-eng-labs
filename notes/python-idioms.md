# Python Idioms — a C/C++ Engineer's Reference

Notes from Week 1, Day 2. The AI concepts are one thing; this file collects the
*Python-language* idioms that `ask.py` leans on — the ones that don't exist in C/C++
or behave differently. Keyed to that file, but every idiom here recurs in essentially
every Python file written from here on.

Reference file:

```python
from anthropic import Anthropic

from config import Settings, get_settings


def build_client(settings: Settings) -> Anthropic:
    return Anthropic(api_key=settings.anthropic_api_key.get_secret_value())


def ask(prompt: str, client: Anthropic, settings: Settings) -> str:
    resp = client.messages.create(
        model=settings.model,
        max_tokens=settings.max_tokens,
        temperature=settings.temperature,
        messages=[{"role": "user", "content": prompt}],
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

## Imports — `from anthropic import Anthropic`

Python's version of `#include`, but smarter. It doesn't paste header text in — it runs
the `anthropic` package once and binds the name `Anthropic` (a class) into this file's
namespace. `from X import Y` means "from module `X`, pull out just the name `Y`."

No headers, no `.h`/`.cpp` split, no forward declarations, no linker step. The import
*is* the linking, and it happens at runtime when the line executes.

---

## Function definitions — `def build_client(settings: Settings) -> Anthropic:`

- **`def`** starts a function. No return-type-first declaration like
  `Anthropic build_client(...)`; Python leads with `def` and the name.
- **`settings: Settings`** is a parameter with a **type hint**. Critical difference
  from C: **Python does not enforce this.** The interpreter runs
  `build_client("hello")` fine and only fails later when the string doesn't behave like
  a `Settings`. The hint is for you, your editor, and a separate checker (`mypy`) — not
  the runtime. A very good comment that tools can read.
- **`-> Anthropic`** is the return-type hint. Same story: documentation and tooling,
  not runtime-enforced.
- **Colon + indentation.** The line ends in `:`, and the body is defined purely by
  indentation — no braces. Whitespace is syntax. Mis-indent and you change the meaning
  of the program or get a syntax error. This trips up every C programmer once.

---

## Attribute and method access — `settings.anthropic_api_key.get_secret_value()`

A chain read left to right:

- `settings` — the object.
- `.anthropic_api_key` — a field on it (a `SecretStr`).
- `.get_secret_value()` — a **method call**; the `()` means "call it." Methods are
  functions that belong to an object; the dot reaches in to find it.

The `.` does the job of both `.` and `->` in C++ — Python has no pointer/value
distinction at this level, so there's only ever the dot. And there's no manual memory
management: no `new`/`delete`, no `malloc`/`free`. Python tracks references and frees
objects automatically when nothing points to them.

---

## Assignment and nested access — `resp = client.messages.create(...)`

- **`resp = ...`** — assignment. No type on the left, no `auto`, no declaration.
  Variables spring into existence on first assignment.
- **`client.messages.create(...)`** — reaching through nested objects: `client` has a
  `messages` attribute, which has a `create` method.

---

## Keyword arguments

```python
client.messages.create(
    model=settings.model,
    max_tokens=settings.max_tokens,
    messages=[...],
)
```

In C you pass arguments *by position*. Python lets you pass them **by name**:
`model=...`, `max_tokens=...`. Order doesn't matter, and the name makes the call
self-documenting — you could reorder those lines freely. This is why Python APIs have
so many parameters: named args keep a 10-argument call readable.

---

## Lists and dicts — `messages=[{"role": "user", "content": prompt}]`

Two built-in data structures, nested:

- **`[...]` is a list** — an ordered, growable sequence. Like `std::vector`, but holds
  anything and needs no declared element type.
- **`{...}` is a dict** — key→value pairs, like `std::map`/`std::unordered_map`, but
  untyped and with clean literal syntax.

So this argument is "a list containing a single dict." The API wants a list because a
conversation is a *sequence* of messages; today you send one.

---

## The return line — comprehension + join

```python
return "".join(block.text for block in resp.content if block.type == "text")
```

Three idioms packed together:

- **`for block in resp.content`** — Python's `for` iterates over the *items
  themselves*, not an index. No `for (int i = 0; i < n; i++)`, no indexing — you get
  each element directly. This is the normal way to loop; indexing is the exception.
- **`block.text for block in resp.content if block.type == "text"`** — a **generator
  expression**: "for each `block`, *if* its `.type` is `"text"`, produce `block.text`."
  Loop, filter, and result value in one expression. The trailing `if` is the filter;
  non-text blocks are skipped. In C this would be a loop with an inner `if` appending to
  a buffer.
- **`"".join(...)`** — `join` is a string method. `separator.join(pieces)` glues a
  sequence of strings with `separator` between them. `"".join(...)` uses an empty
  separator, so it concatenates. (`", ".join(["a","b"])` → `"a, b"`; `"".join(["a","b"])`
  → `"ab"`.)

Together: filter blocks down to text blocks, pull each `.text`, concatenate into one
string, return it — and it never crashes on a non-text block, it just skips it.

---

## `None` — `def main() -> None:`

`None` is Python's "no value." Closest to `void` as a return type, and to
`nullptr`/`NULL` as a value — but it's an actual object you can assign and compare
against (`if x is None:`), not just an absence.

---

## The entry-point guard — `if __name__ == "__main__":`

The one idiom with no C equivalent.

Every Python file has a built-in variable `__name__`. **Run a file directly**
(`python ask.py`) and Python sets that file's `__name__` to the string `"__main__"`.
**Import** the file from another file and `__name__` is set to the module's name
(`"ask"`) instead.

So this line means: *only run the code below if this file is being run directly, not
when it's imported.*

Why it matters: next week the tests will `import ask` to test the `ask()` function.
Without this guard, importing would execute `main()` — firing a real, billed API call —
just from the import. The guard makes `ask.py` behave as **both** a runnable script
*and* an importable library, depending on how it's used.

Mental model: in C, `main()` is special to the compiler and runs automatically. In
Python there's no privileged `main` — a file's top level runs top-to-bottom on import
*or* execution. This `if` manually recovers the "only when run directly" behavior C
gives for free.

---

## Cheat sheet

| Python | C/C++ analogue | Key difference |
|---|---|---|
| `from x import y` | `#include` | Runtime, name-based; import *is* linking |
| `x: T` type hint | `T x` declaration | **Not enforced at runtime**; for tools/humans |
| indentation | `{ }` blocks | Whitespace is syntax |
| `.` (only) | `.` and `->` | No pointer/value split at this level |
| `f(name=val)` | positional args | Named args; order-independent |
| `[...]` list | `std::vector` | Untyped, any element type |
| `{...}` dict | `std::map` | Untyped, literal syntax |
| `for x in seq` | index loop | Iterates items, not indices |
| `a for a in seq if c` | loop + `if` + append | Comprehension: transform+filter in one expr |
| `sep.join(parts)` | manual concat loop | String method |
| `None` | `void` / `NULL` | A real object; `is None` to test |
| `if __name__ == "__main__":` | (automatic `main`) | Manual "run only if executed directly" |
| (no `new`/`delete`) | manual memory mgmt | Automatic reference-based cleanup |
