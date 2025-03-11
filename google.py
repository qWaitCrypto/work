import google.generativeai as genai
import os

os.environ['HTTP_PROXY'] = 'http://127.0.0.1:7890'
os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:7890'
# 设置 API Key
genai.configure(api_key="AIzaSyCElknLMmO3-4Fl1QVLufYRatYGMppV9vM")

# 创建 Gemini Pro 模型
model = genai.GenerativeModel('gemini-2.0-flash')

# 生成内容
response = model.generate_content("美国的首都是哪里？")

# 输出结果
print(response.text)
