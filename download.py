import torch
from modelscope import snapshot_download
from modelscope import GenerationConfig
model_dir = snapshot_download('qwen/Qwen-7B-Chat', cache_dir='/model/qwen7b')