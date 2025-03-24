from openai import OpenAI
import os
import base64
import requests


client = OpenAI(
    # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx"
    api_key="11111",
    base_url="None",
)

def encode_image_from_url(image_url):
    response = requests.get(image_url)
    if response.status_code != 200:
        raise Exception("无法下载图片")
    return base64.b64encode(response.content).decode("utf-8")

image_base64 = encode_image_from_url("https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20241022/emyrja/dog_and_girl.jpeg")

completion = client.chat.completions.create(
    model="qwen-vl-7b",
    messages=[
        {"role": "system",
         "content": [{"type": "text", "text": "You are a helpful assistant."}]},
        {"role": "user",
         "content": [{"type": "image_base64", "image_base64": image_base64},
                     {"type": "text", "text": "图中描绘的是什么景象？"}]}
    ],
    stream=True
)

full_content = ""
print("流式输出内容为：")
for chunk in completion:
    if chunk.choices[0].delta.content is None:
        continue
    full_content += chunk.choices[0].delta.content
    print(chunk.choices[0].delta.content)

print(f"完整内容为：{full_content}")
