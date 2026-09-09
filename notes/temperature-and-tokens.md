# Temperature & Tokens — Deep Dive

*A Week 1 note for the AI Engineering Apprenticeship. Learned by experiment — keep in `notes/`.*

This note covers two Day 1 concepts explored hands-on: **temperature** (sampling
randomness) and **tokens** (how text is chunked, counted, and priced).

---

# PART 1 — TEMPERATURE

## What it is

Temperature controls **how much randomness is injected when the model samples the next
token**. The model produces a probability distribution over possible next tokens;
temperature reshapes how *peaked* that distribution is before a token is drawn from it.

- **temperature = 0** → greedy. Always take the single most likely token. Near-deterministic.
- **temperature = 1** → the model's natural distribution. Likely tokens dominate, but lower-probability ones get a real chance.
- **temperature > 1** (where allowed) → distribution flattens further; even unlikely tokens get picked. More surprising / chaotic. *(Anthropic's API caps temperature at 1.0; some providers allow up to 2.0.)*

## The mechanism (why it's called "temperature")

The name is borrowed from **statistical thermodynamics** (the Boltzmann / softmax-with-
temperature distribution). The same equation that describes how energetically particles
explore states in a physical system is used to turn the model's raw scores (logits) into
probabilities:

```
probability(token) ∝ exp(score / temperature)
```

The division by temperature is the whole trick:

- **temperature → 0:** dividing by a tiny number blows up the score differences → the top
  token's probability approaches 1, the rest approach 0. Distribution becomes a single
  spike. "Cold," frozen, orderly. Always the top token.
- **temperature = 1:** scores pass through unchanged → natural distribution.
- **temperature > 1:** dividing by a large number flattens score differences → low-scoring
  tokens gain probability. "Hot," energetic, exploratory.

**Physical intuition:** a cold system freezes into its single lowest-energy state; a hot
system has energy to wander across many states. A cold model freezes onto the most probable
token; a hot model wanders across token choices.

**Landscape image:** picture the probability distribution as hills and valleys.
- Cold (0): the tallest peak becomes infinitely tall, everything else flattens → one choice.
- Warm (1): natural terrain → big hills likely, small hills occasionally.
- Hot (>1): terrain melts flatter → even little hills get chosen sometimes.

## The experiment (what I observed)

Prompt: *"Write one sentence about the ocean."* Run 5× at temp 0, 5× at temp 1.

- **Temp 0:** all five outputs **identical** — the model kept picking the single most likely
  continuation. Determinism made visible.
- **Temp 1:** three of five were *still* identical to the temp-0 answer; only runs 1 and 5
  diverged (and only near the *end* of the sentence).

**Why temp 1 varied less than expected:** the prompt is heavily constraining. "One sentence
about the ocean" has a dominant, high-probability opening ("The ocean covers more than 70%
of Earth's surface..."), so even with randomness turned up, the model lands there often.
Temperature widens the distribution; it doesn't force variety. If one path is overwhelmingly
probable, a wider distribution still lands on it much of the time.

**Why divergence appeared only at the end:** early tokens ("The ocean covers more than
70%...") are nearly certain, so there's little room to stray. By the end of the sentence
several continuations are plausible, so that's where randomness expresses itself.

**To see temp 1 really cut loose:** use a prompt with a *flat* distribution (many roughly
equal continuations), e.g. "Invent a name for a fictional sea creature." Then temp 1 sprays
genuinely different outputs every run.

## Engineering takeaway

- Temperature is **not** "creativity on/off." It's *how much you let the model stray from
  its single most-confident answer.*
- On confident/constrained prompts, even high temperature stays fairly stable.
- On open-ended prompts, temperature's effect is large.
- **Default low (0–0.3)** for engineering tasks needing repeatability (extraction,
  classification, structured output). Raise it only when you *want* variety.
- Even at temp 0, output is *near*-deterministic, not a mathematical guarantee.

## Related parameters

`top_p` and `top_k` are *other* ways to reshape the same distribution — they chop off the
low-probability tail rather than rescaling the whole thing. Same goal: control how far the
model may stray from its most confident guess. (All three — `temperature`, `top_p`, `top_k`
— were removed from the SDK method signatures in the anthropic 1.0 migration; see the SDK
note below.)

---

# PART 2 — TOKENS

## What a token is

The model reads and writes **tokens**, not words or characters. A token is a **sub-word
chunk**, ~4 characters / ~0.75 words in English *on average* — but only on average.

- Common whole words → often one token (`"the"`).
- Rarer words → split into pieces (`"debugging"` → `de`+`bug`+`ging`).
- Truly novel strings → fall back toward single bytes.

## Why it matters (three consequences)

1. **You pay per token** — not per word or character. Token count = bill + latency.
2. **The context window is measured in tokens** (e.g. 200k tokens, not words).
3. **Token count is not predictable from length** — same character count can be very
   different token counts depending on *what* the characters are.

## How chunks are decided: BPE + byte fallback

Most LLMs use **Byte Pair Encoding (BPE)**:
1. Start from the floor — all 256 individual **bytes** are in the vocabulary.
2. During tokenizer training, repeatedly merge the most frequent adjacent pair into a new
   vocab entry (`t`+`h` → `th`, `th`+`e` → `the`, ...).
3. Result: a vocabulary of ~50k–100k+ entries from single bytes up to common whole words.

At runtime the tokenizer greedily grabs the **longest vocabulary entry** matching the
upcoming text, shrinking its ambition until it finds a match.

**"What if nothing matches a chunk?"** There's always the byte-level fallback — any text
decomposes to bytes, which are always in the vocabulary. Tokenization can never fail; weird
input just produces a long stream of tiny tokens.

**C/C++ analogy:** like a lexer whose token table is guaranteed complete because its last
rule is "match a single raw byte." It tokenizes *any* input; some inputs just come out as a
flood of one-byte tokens.

## The experiment (what I measured)

Using `client.messages.count_tokens(...)` on five strings:

| Tokens | Words | String | Note |
|---|---|---|---|
| 14 | 6 | `The cat sat on the mat.` | plain English — baseline |
| 24 | 6 | `std::vector<int> v = {1, 2, 3};` | C++ code |
| 26 | 2 | `0xDEADBEEF 0xCAFEBABE` | hex |
| 14 | 1 | `こんにちは世界` | Japanese |
| 18 | 1 | `xzq_handle_reset_interrupt_vector` | identifier |

**Overhead:** `count_tokens` counts the full message structure (role markers, wrapping), not
just raw text — roughly the first ~7–8 tokens are fixed overhead paid on *every* call.
Compare rows relative to each other, not against a pure tokenizer.

**Row-by-row (adjusting for shared overhead):**
- **English (14):** ~1 token/word. The cheap case — common words compress well. Cheapest
  thing you can send.
- **C++ (24):** 10 more than English for a shorter-looking line. `::`, `<`, `>`, `=`, `{`,
  `}`, `;`, digits each ≈ their own token. **Code costs far more tokens than equivalent-
  length prose.**
- **Hex (26):** highest count from the shortest-looking input. `0xDEADBEEF` isn't a learned
  word → shatters into tiny pieces. Random-looking alphanumerics (hex, UUIDs, hashes,
  base64) are worst-case for tokenizers.
- **Japanese (14):** 6 on-screen characters ≈ 7 content tokens — *more than one token per
  character*. Non-Latin scripts fragment toward bytes (rarer in training data). Same
  *meaning* costs more tokens than in English — real cost/fairness implication.
- **Identifier (18):** one whitespace-"word" ≈ 11 content tokens. Breaks at underscores:
  `xzq`, `_handle`, `_reset`, `_interrupt`, `_vector`. Long snake_case / camelCase
  identifiers (everywhere in embedded code) fragment more than they look.

**The ranking (tokens per visible length):**
> Hex ≈ code > identifiers > Japanese > plain English.

Plain English is cheapest; symbol-heavy, random-looking, or non-Latin text is expensive.
**You cannot eyeball token count from length — measure it.** `count_tokens` lets you measure
*before* sending, so you know if input fits the window and what it'll cost.

---

# APPENDIX — SDK note (anthropic 1.0 migration)

Discovered live during Week 1: `anthropic` Python SDK **v1.0** (Aug 2026) **removed
`temperature`, `top_p`, `top_k` from the method signatures** of `messages.create()`,
`.stream()`, `.parse()`. Passing `temperature=...` as a kwarg raises `TypeError` on the 1.x
SDK.

**Key subtlety:** the SDK dropped the parameters; the **wire protocol did not**. The API
still accepts `temperature` (default 1.0, range 0.0–1.0). So on 1.x, pass it via
`extra_body`:

```python
resp = client.messages.create(
    model=settings.model,
    max_tokens=100,
    messages=[{"role": "user", "content": prompt}],
    extra_body={"temperature": temperature},   # reaches the API even though not a named kwarg
)
```

Alternative: pin to the last 0.x SDK (`anthropic>=0.125,<1`) to keep `temperature` as a
first-class kwarg. **Decision for this course:** stay on 1.x (current, maintained,
interview-relevant) and use `extra_body`.

---

## What to remember

**Temperature**
- Controls how far the model may stray from its most-confident next token.
- Named after thermodynamics: `exp(score / temperature)` — cold = spike, hot = flat.
- Constrained prompts stay stable even at high temp; open-ended prompts vary a lot.
- Default low for engineering tasks.

**Tokens**
- Model reads tokens (sub-word chunks), not words. BPE + byte fallback → never fails.
- Pay per token; context window measured in tokens; count unpredictable from length.
- Code, hex/random strings, non-English, and long identifiers all fragment heavily.
- Measure with `count_tokens` before sending; there's fixed per-message overhead.
