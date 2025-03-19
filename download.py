from datasets import load_dataset
import os
import json
import random
import tiktoken

# 设置代理（如果需要）
os.environ['HTTP_PROXY'] = 'http://127.0.0.1:7890'
os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:7890'

from huggingface_hub import snapshot_download

# 指定模型名称
model_name = "lmsys/DeepSeek-V3-NextN"

# 下载整个模型
snapshot_download(repo_id=model_name, cache_dir="./models")
