import os
from anthropic import Anthropic

client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

# --- Call 1 ---
first = client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=200,
    messages=[
        {"role": "user", "content": "In two sentences, explain what a token is to a C++ engineer."}
    ],
)
answer_1 = first.content[0].text
print("ANSWER 1:\n", answer_1, "\n")

# --- Call 2: feed the first answer back as an assistant turn ---
second = client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=200,
    messages=[
        {"role": "user", "content": "In two sentences, explain what a token is to a C++ engineer."},
        {"role": "assistant", "content": answer_1},          # the model's own prior reply, fed back
        {"role": "user", "content": "Give me an example"}     # now THIS refers to the above
    ],
)
print("ANSWER 2:\n", second.content[0].text)

# --- Call 3: do not feed the context, proving api is stateless ---
third = client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=200,
    messages=[
        {"role": "user", "content": "Give me an example"}     # now THIS refers to the above
    ],
)
print("ANSWER 3:\n", third.content[0].text)