from vllm import LLM, SamplingParams

# 加载模型并指定使用 CPU
llm = LLM('D:\\model\\qwen7b\\qwen\\Qwen-7B-Chat', device=0, trust_remote_code=True)

# 设置推理参数
sampling_params = SamplingParams(
    max_tokens=100,
    temperature=0.7,
    top_p=0.9,
)

# 生成文本
response = llm.generate("What is the capital of France?", sampling_params)
print(response)
