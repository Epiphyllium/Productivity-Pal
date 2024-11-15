import os
from volcenginesdkarkruntime import Ark

client = Ark(base_url="https://ark.cn-beijing.volces.com/api/v3",api_key=("fbcf73dd-657b-42da-afe4-70edd36bf553"))

print("----- streaming request -----")
stream = client.chat.completions.create(
    model="ep-20241112153408-rnvqn",
    messages = [
        {"role": "system", "content": "你是豆包，是由字节跳动开发的 AI 人工智能助手"},
        {"role": "user", "content": "常见的十字花科植物有哪些？"},
    ],
    stream=True
)
for chunk in stream:
    if not chunk.choices:
        continue
    print(chunk.choices[0].delta.content, end="")
print()