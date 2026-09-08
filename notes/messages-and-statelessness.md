# The `messages` API & Statelessness

*A Week 1, Day 1 note for the AI Engineering Apprenticeship. Learned by experiment — keep in `notes/`.*

---

## The core idea

The LLM API is **stateless**. The model remembers **nothing** between calls. Each call to
`client.messages.create(...)` is a completely independent event — it only ever sees the
`messages` list you hand it *in that one call*. There is no "conversation" the model is
aware of; "context" is not something the model has, it's something **you construct and pass
in, every single time.**

**You are the memory.** Not the model.

---

## The `messages` structure

`messages` is a **list of conversation turns**, in order. Each turn is a dict with two keys:

```python
messages=[
    {"role": "user", "content": "In two sentences, explain what a token is to a C++ engineer."}
]
```

- **`role`** — who is speaking:
  - `"user"` → you / your application (the human side)
  - `"assistant"` → the model's replies
  - (a `system` prompt also exists, but Anthropic passes it as a *separate* parameter,
    not inside `messages`)
- **`content`** — what was said. A plain string for now; later it can be a **list of blocks**
  (text + images, etc.), mirroring the list-of-blocks you see on the response side
  (`resp.content[0].text`).

Turns should **alternate sensibly**: user → assistant → user → assistant. Don't stack two
`user` turns back to back (see the gotcha below).

---

## How you "fake" memory: resend the whole history

Because the model retains nothing, a multi-turn conversation works by **resending the entire
history every call**, appending each new turn.

Single turn:
```python
messages=[
    {"role": "user", "content": "What's a token?"}
]
```

Follow-up — note you feed the model's own previous reply back in as an `assistant` turn:
```python
messages=[
    {"role": "user", "content": "What's a token?"},
    {"role": "assistant", "content": "A token is a sub-word chunk..."},  # its last reply, fed back
    {"role": "user", "content": "Give me an example."}                   # now this has something to refer to
]
```

If you drop that middle `assistant` turn, "give me an example" refers to nothing — the model
genuinely doesn't remember its own previous answer.

---

## The experiment that proved it

Three calls in the same script, seconds apart:

- **Call 1** — asked the original question. Got a good answer. Saved it as `answer_1`.
- **Call 2** — sent `[original question, assistant: answer_1, "Give me an example"]`.
  The full history was present, so "example" had context → got a relevant tokenization example.
- **Call 3** — sent **only** `[{"role": "user", "content": "Give me an example"}]`.
  No history. The model had no idea what to exemplify → returned a random, unrelated example.

**Key realization:** Call 3 ran *after* Call 2, in the same file, same run — and still knew
nothing. From the model's side, Call 2 never happened. It doesn't know the calls came from the
same person, script, or session. The only thing it ever sees is that one call's `messages` list.

Call 3 *felt* broken because **I** remembered Call 2. The model didn't.

---

## Mental model (for a C/C++ engineer)

Treat the call as a **pure function with no internal state**:

```
reply = model(system_instructions, full_message_history)
```

- Output depends **only** on the arguments passed in.
- No member variable quietly holds the conversation. No hidden session state.
- If you want the model to "know" something, it must be **in the arguments** — i.e. in the
  `messages` list for *that* call.
- That's why it's a list you keep growing, not a session object you keep talking to.

---

## Gotcha: two `user` turns in a row

Sending two consecutive `user` turns (no `assistant` between them):

```python
messages=[
    {"role": "user", "content": "Explain what a token is."},
    {"role": "user", "content": "Give me an example"}
]
```

Anthropic's API is **lenient** and merges them into one combined message, so it "works" — but
this is not a real multi-turn exchange; it's just two instructions concatenated into one turn.
Some APIs **reject** non-alternating roles outright. Don't rely on the leniency — it's a habit
that bites later.

---

## Why this matters later (agents)

An **agent** is essentially a loop that carefully **appends to this `messages` list** — every
tool call, every tool result, every prior step — so the model has what it needs on the *next*
call. Mismanage the list and the agent "forgets" things mid-task. The context-free failure of
Call 3 above is exactly the failure mode you engineer around in the agents week.

---

## What to remember

- The API is **stateless**; the model remembers nothing between calls.
- `messages` is the **conversation history you resend every call** — the list *is* the memory.
- `role` is `user` / `assistant`; `content` is a string (or later, a list of blocks).
- Feed the model's own prior replies back as `assistant` turns to sustain a conversation.
- Think **pure function**: output depends only on what you pass in.
- Don't stack same-role turns; keep them alternating.
- Managing this list well *is* the core skill behind agents.
