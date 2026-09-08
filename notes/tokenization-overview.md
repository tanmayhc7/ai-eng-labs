# Tokenization — A Plain-English Overview

*A Week 1 reference for the AI Engineering Apprenticeship. Keep this in `notes/`.*

---

## The one-sentence version

An LLM never sees your text as letters or words — it sees **tokens**, which are sub-word chunks. Tokenization is the step that chops your text into those chunks before the model ever runs, and stitches the model's output chunks back into text afterward.

---

## Why you should care (as an engineer)

Three practical consequences flow from tokenization, and everything else is detail:

1. **You pay per token.** Not per word, not per character. Token count *is* your bill and your latency.
2. **The context window is measured in tokens.** "200k context" means 200k tokens of working memory, not 200k words. You need to reason in tokens to know if your input fits.
3. **Token count is not predictable from length.** The same 100 characters can be 20 tokens or 60 tokens depending on *what* they are. Plain English is cheap; code, rare words, and non-English text are expensive.

If you internalize nothing else, internalize: **tokens ≠ words, and you can't eyeball the count.**

---

## What a token actually is

A token is a **sub-word chunk** — on average about 4 characters, or roughly 0.75 words, in English. Some examples of how words split:

- `"the"` → one token (extremely common, earned its own slot)
- `"debugging"` → maybe `de` + `bug` + `ging` (three tokens)
- `"tokenization"` → maybe `token` + `ization` (two tokens)

Common whole words are single tokens. Rare words get fragmented into pieces. The rarer and weirder the string, the more pieces it breaks into.

---

## How the chunks get decided: BPE (the short story)

Most modern LLMs use a scheme called **Byte Pair Encoding (BPE)**. You don't need to implement it, but the mental model pays off:

1. **Start from the floor: individual bytes.** The vocabulary includes all 256 possible bytes. This is the guarantee that tokenization can *never* fail — more on that below.
2. **Merge frequent pairs.** During the tokenizer's training, it scans a huge amount of text and repeatedly merges the most common adjacent pair into a new single entry: `t`+`h` → `th`, then `th`+`e` → `the`, and so on, thousands of times.
3. **Result: a vocabulary of ~50k–100k+ entries**, ranging from single bytes up to common whole words. Frequent sequences became their own tokens; rare ones didn't.

At runtime, the tokenizer greedily grabs the **longest entry in its vocabulary** that matches the upcoming text, then continues from there.

---

## "What if there's nothing available for a chunk?"

There always is — that's the point of starting from bytes.

If the tokenizer can't match a long chunk, it shrinks its ambition until it finds a match. Worst case, that match is a **single byte**, which is always in the vocabulary. So *any* input — any language, emoji, binary garbage, a novel identifier — always has a valid tokenization. Some inputs just produce a long, inefficient stream of tiny tokens.

**Analogy for C/C++ folks:** it's like a lexer whose token table is guaranteed complete because its last rule is always "match a single raw byte." It can tokenize *any* input stream — some streams just come out as a flood of one-byte tokens.

---

## Why this matters for code and non-English text

This is where the "you can't eyeball it" rule bites, and it's especially relevant to your embedded/hardware capstone:

- **Code fragments heavily.** A made-up identifier like `xzq_handle` isn't a common English string, so it shatters into small pieces (`x`, `z`, `q`, `_hand`, `le`, or byte-level bits). Dense macros, hex blobs, and unusual symbols burn far more tokens than their character count suggests.
- **Non-English text is more expensive.** Scripts and words that appeared less often in the tokenizer's training data fall back to smaller chunks — sometimes down to bytes — so the same *meaning* costs more tokens than it would in English.
- **Whitespace and formatting count too.** Indentation, newlines, and repeated punctuation are all tokens. Pretty-printed JSON costs more than minified JSON.

Practical upshot: a screen of C source can cost noticeably more tokens than a screen of prose. When you're stuffing technical docs into a context window later in the course, this is a real budget factor, not a footnote.

---

## The vocabulary of terms (quick glossary)

| Term | Plain meaning |
|---|---|
| **Token** | A sub-word chunk; the unit the model actually reads and writes. |
| **Tokenizer** | The component that converts text ↔ tokens. Runs before and after the model. |
| **Vocabulary** | The fixed set of all tokens the tokenizer knows (bytes up to whole words). |
| **BPE** | Byte Pair Encoding — the merge-based algorithm that built the vocabulary. |
| **Byte-level fallback** | The safety net: any text decomposes to bytes, so tokenization never fails. |
| **Context window** | Total tokens the model can see at once (input + output), e.g. 200k. |
| **Token count** | The number of tokens in some text — drives cost and latency. |

---

## What to remember

- The model reads **tokens**, not words or characters.
- Tokens are **sub-word chunks**, ~4 chars each on average — but only on average.
- **BPE** builds the vocabulary by merging frequent pairs, starting from raw bytes.
- **Byte-level fallback** means tokenization can never hit a chunk it can't represent.
- **Code and non-English text fragment more**, costing more tokens than their length implies.
- You **cannot reliably predict** token count by eye — run the real tokenizer when it matters.

---

## Try it yourself (Week 1 exercise tie-in)

One of your Week 1 coding exercises is: *print the raw token count for 5 strings, and predict the count before running.* Pick deliberately weird ones — a normal English sentence, a line of C, a hex string, some non-English text, and an identifier like `xzq_handle`. You'll guess the plain sentence about right and be badly wrong on the others. Being wrong on purpose is how the intuition sticks.
