# Context Window, Token Budgets, and Response Shape

Notes from Week 1, Day 2. Concepts pinned down while building the typed `ask()` client.

## Token budgets: three quantities, don't conflate them

There are three separate token counts in play on every call, and most confusion
comes from collapsing them into one:

- **Input tokens** — everything you send: system prompt, messages, and any prior
  conversation history you resent (the API is stateless, so history is on you).
  There is no parameter that caps this; its only limit is the context window.
- **Output tokens** — what the model generates in its reply. This is the *only*
  thing `max_tokens` bounds.
- **Context window** — the hard ceiling on **input + output combined**. This is
  the model's real constraint.

The relationship:

```
input_tokens + output_tokens  ≤  context_window
                    ↑
              capped by max_tokens
```

`max_tokens` is a ceiling on output, not a target and not a reservation carved out
of the window. The model emits `end_turn` when it's done and bills only for what it
actually generated. Set `max_tokens=4096` on a one-sentence answer and you pay for
one sentence.

Two consequences worth holding onto:

- **`max_tokens` is validated up front.** If `input + max_tokens > context_window`,
  the request is rejected *before* generation starts — not truncated mid-stream.
  On a 200k model, a 199k-token input with `max_tokens=4096` fails: 199k + 4,096 >
  200k. The fix is either a smaller input or a smaller `max_tokens`, and choosing
  which is a real design call in RAG.
- **Output is the expensive half.** Billing splits input and output at different
  rates — Haiku 4.5 is $1/M input, $5/M output. So `max_tokens` is a cost lever as
  much as a correctness one: the thing it caps is the pricier token.

C mental model: `max_tokens` is the size of the buffer you hand the model to write
into, not the size of the message you pass in. Undersize it and output gets cut off
at the buffer boundary — silently.

### Worked example

A 4,000-token prompt with a 200k window and `max_tokens=1000`: the output is bounded
at 1,000 tokens, and the *cycle* occupies up to 5,000 tokens (4,000 in + up to 1,000
out) inside the window. In RAG this is the whole ballgame — the room left for
retrieved chunks is `context_window - max_tokens - system_prompt - history`, and that
remainder is your chunk budget. People discover this by getting a 400 in production.

## Silent truncation

When `max_tokens` *is* hit, truncation is silent. You get text that just stops;
nothing raises. The only signal is `resp.stop_reason == "max_tokens"`. Log
`stop_reason` alongside token counts on every call — a truncated JSON response that
fails to parse three weeks later will otherwise read like a prompt bug.

## Determinism: temperature 0 is not a guarantee

Temperature 0 is greedy sampling — take the argmax token at each step — so it *should*
be deterministic. In practice it isn't, for reasons below the model:

- GPU kernels reduce floating-point sums in a nondeterministic order depending on how
  requests are batched together. Two logits differing in the 7th decimal can swap
  ranks. One swapped token early cascades, because each token conditions the next.
- The model behind an alias can be updated underneath you.

Engineering consequence: **never assert exact LLM output in a test.** Assert on
properties, not strings. This is the reason eval harnesses (Week 3) exist.

## Statelessness

The API remembers nothing between calls. Whatever the model should "know" about an
earlier turn has to be resent as part of the input. Proven empirically on Day 1 with
a three-call experiment. This is also the concept that makes agent loops (Week 10)
demystifying: "memory" there is nothing more than appending to a list and resending it.

## Response shape: `resp.content` is a list, not a string

`resp.content` is a **list of content blocks**, not a string. Each block carries a
`.type`; text blocks also carry `.text`.

The reason is extensibility. One response can hold several blocks of different kinds
— text, plus `tool_use` blocks when the model calls a tool, plus `thinking` blocks on
extended-thinking models. A plain string field could never carry that, so the API
committed to a list from day one rather than breaking every client later.

This is why the correct extraction is:

```python
"".join(block.text for block in resp.content if block.type == "text")
```

and not `resp.content[0].text`. The naive index works until tool use appears, then
silently returns the wrong block or crashes. Write the version that survives.

## Training vs. inference

Calling the API is **inference**: running a frozen model. Training happened once,
beforehand, and is done. The C++ analogy: training is compilation, inference is
running the binary. RAG exists precisely because of this gap — the model can't learn
your documents at inference time, so relevant context has to be injected into the
input on each call.
