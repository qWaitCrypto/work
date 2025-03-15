from datasets import load_dataset
import os
import json
import random
import tiktoken

# 设置代理（如果需要）
os.environ['HTTP_PROXY'] = 'http://127.0.0.1:7890'
os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:7890'

# 初始化 Tokenizer
tokenizer = tiktoken.encoding_for_model("gpt-3.5-turbo")

# 设定目标数据量
TARGET_SIZE = 1000
MAX_TOKENS = 256

# 加载数据集（只保留事实问答 & 语言任务）
mmlu = load_dataset('lukaemon/mmlu', 'high_school_world_history', split='test', trust_remote_code=True)  # 事实问答
cmrc = load_dataset('cmrc2018', split='validation')  # 中文阅读理解
# 过滤数据，确保答案在 256 tokens 以内
def filter_by_token_length(data, question_key, answer_key, category, dataset_name):
    filtered_data = []
    for idx, item in enumerate(data):
        question = item.get(question_key, "").strip()
        answer = item.get(answer_key, "")
        # 处理答案为空的情况
        if answer is None:
            continue

        # 如果答案是字典（如 CMRC 2018），直接存储完整答案
        elif isinstance(answer, dict) and "text" in answer:
            pass  # 保持原始格式

        # 如果答案是列表，取所有非空项
        elif isinstance(answer, list):
            answer = [str(ans) for ans in answer if ans]  # 确保列表里都是字符串

        # 处理数字答案（转换为字符串）
        elif isinstance(answer, (int, float)):
            answer = str(answer)

        # 确保 `answer` 不是空的
        if not answer:
            continue

        # 计算 Token 数量（转换为字符串）
        token_count = len(tokenizer.encode(str(answer)))
        if token_count <= MAX_TOKENS:
            filtered_data.append({
                "id": f"{dataset_name}_{idx}",
                "category": category,
                "question": question,
                "expected_answer": answer  # 可能是字符串、列表、字典
            })
    return filtered_data

# 处理数据集
filtered_mmlu = filter_by_token_length(mmlu, "question", "answer", "fact", "mmlu")
filtered_cmrc = filter_by_token_length(cmrc, "question", "answers", "reading", "cmrc")

# 数据集任务分布（只保留 fact 和 reading）
category_distribution = {
    "fact": 0,
    "reading": 1000
}
print(len(filtered_mmlu), len(filtered_cmrc))
# 随机采样
final_dataset = (
    random.sample(filtered_mmlu, category_distribution["fact"]) +
    random.sample(filtered_cmrc, category_distribution["reading"])
)

# 确保总数据量不超过目标值
final_dataset = final_dataset[:TARGET_SIZE]

# 保存优化后的数据集
output_file = "evaluation_dataset.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(final_dataset, f, indent=4, ensure_ascii=False)

print(f"✅ 数据集构建完成，共 {len(final_dataset)} 条问题，已保存到 {output_file}")
