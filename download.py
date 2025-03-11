from transformers import AutoModelForCausalLM, AutoTokenizer
import os

# 设置 HTTP 和 HTTPS 代理
os.environ['HTTP_PROXY'] = 'http://127.0.0.1:7890'
os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:7890'
# 下载并加载 Llama2 模型和分词器
model_name = "meta-llama/Llama-2-13b-chat-hf"
model = AutoModelForCausalLM.from_pretrained(model_name)
tokenizer = AutoTokenizer.from_pretrained(model_name)
model.save_pretrained('/model')
tokenizer.save_pretrained('/model')
