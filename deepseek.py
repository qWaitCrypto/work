# 使用这个python脚本之前需要在python环境中安装openai库：pip install openai

from openai import OpenAI
openai_api_key = "EMPTY"

# 用了10.200.4.101 和 10.200.4.102 两台机器部署。两个都能访问
# openai_api_base = "http://10.200.4.101:12345/v1"  # DeepSeek-R1-AWQ
# openai_api_base = "http://10.200.4.102:12345/v1"  # DeepSeek-R1-AWQ

# openai_api_base = "http://10.200.0.142:12345/v1"  # DeepSeek-V3-bf16

openai_api_base = "http://10.200.3.25:12345/v1"  # DeepSeek-R1  全量版

client = OpenAI(
    api_key=openai_api_key,
    base_url=openai_api_base,
)

# 流式的python访问
def stream():
    chat_response = client.chat.completions.create(
        # model="deepseek-reasoner",  # DeepSeek-R1-AWQ
        # model="deepseek-v3",  # DeepSeek-V3-bf16
        model="deepseek-reasoner-bf16", # DeepSeek-R1  全量版
        messages=[
            {"role": "user", "content": "介绍一下武汉热干面怎么做."},
        ],
        stream="True"
    )
    for chunk in chat_response:
        role = chunk.choices[0].delta.role
        content = chunk.choices[0].delta.content
        if not role:
            print(content, flush=True, end='')
    print("\n")

stream()