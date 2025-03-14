import json
import requests
import re
from nltk.translate.bleu_score import sentence_bleu
import os
import sglang as sgl

os.environ['HTTP_PROXY'] = 'http://127.0.0.1:7890'
os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:7890'

system_prompt = """You are an AI assistant trained to provide precise, concise, and well-formatted answers based on the type of question asked. Follow these rules:

1. **For factual, mathematical, and logical reasoning questions**:
   - Provide only the final answer without explanations.
   - Example:
     User: "What is 2 + 2?"
     AI: "4"

2. **For programming and code generation tasks**:
   - Provide a complete and correct code snippet.
   - Do not include explanations, just the code.
   - Example:
     User: "Write a Python function to reverse a list."
     AI:
     ```
     def reverse_list(lst):
         return lst[::-1]
     ```

3. **For multi-step logical reasoning problems**:
   - Keep the reasoning minimal but clear.
   - Summarize the thought process in 1-2 sentences before giving the answer.
   - Example:
     User: "If A > B and B > C, what is the relation between A and C?"
     AI: "Since A is greater than B, and B is greater than C, it follows that A > C."

4. **For reading comprehension and open-ended questions**:
   - Answer in a structured but concise manner.
   - Keep responses within 2-3 sentences unless explicitly requested for more details.

5. **General Rules**:
   - If the answer is unknown, reply: "I don't know."
   - Always use clear and formatted output.
   - If a question expects a list, format the answer as a list.
"""

# 读取数据集
dataset_path = "./evaluation_dataset.json"
with open(dataset_path, "r", encoding="utf-8") as f:
    dataset = json.load(f)

API_URL = "https://api.deepseek.com/v1/chat/completions"
API_KEY = "sk-f267b40f68fe47fbba06d9534b988214"

# 发送请求给模型
def query_model(question):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    payload = {
        "model": "deepseek-reasoner",
        "messages": [{"role": "system", "content": system_prompt},
                        {"role": "user", "content": question}],
        "max_tokens": 256
    }
    response = requests.post(API_URL, json=payload, headers=headers)

    if response.status_code != 200:
        print(f"❌ 请求失败：{response.status_code}，错误信息：{response.json()}")
        return ""
    # print(response.json())
    return response.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()


# 1️⃣ Exact Match (EM)
def exact_match(pred, expected):
    if isinstance(expected, dict) and "text" in expected:
        possible_answers = expected["text"]
    elif isinstance(expected, list):
        possible_answers = [str(ans).strip().lower() for ans in expected]
    else:
        possible_answers = [str(expected).strip().lower()]
    return 1 if pred.strip().lower() in possible_answers else 0

# 2️⃣ BLEU Score（适用于文本回答）
def compute_bleu(pred, expected):
    pred_tokens = pred.split()
    expected_tokens = expected.split()
    return sentence_bleu([expected_tokens], pred_tokens)

# 3️⃣ 数学精确匹配
def numerical_match(pred, expected):
    try:
        return 1 if float(pred) == float(expected) else 0
    except ValueError:
        return 0

# 4️⃣ 代码 Pass@k 评测
def test_python_code(code):
    try:
        exec_globals = {}
        exec(code, exec_globals)
        return 1  # 代码成功运行
    except Exception:
        return 0  # 代码报错

# 存储评估结果
results = []
metrics_summary = {
    "exact_match": [],
    "bleu_score": [],
    "numerical_score": [],
    "pass_k_score": []
}

for sample in dataset:
    print(sample)
    question = sample["question"]
    expected_answer = sample["expected_answer"]
    category = sample["category"]

    # 调用模型
    model_response = query_model(question)
    print('1', expected_answer)
    print('2', model_response)

    # 计算评测指标
    em_score = exact_match(model_response, expected_answer)
    bleu_score = compute_bleu(model_response, str(expected_answer)) if category in ["fact", "reading"] else None
    numerical_score = numerical_match(model_response, expected_answer) if category == "math" else None
    pass_k_score = test_python_code(model_response) if category == "code" else None
    print(em_score, bleu_score, numerical_score, pass_k_score)
    # exit()
    # 记录数据
    if em_score is not None:
        metrics_summary["exact_match"].append(em_score)
    if bleu_score is not None:
        metrics_summary["bleu_score"].append(bleu_score)
    if numerical_score is not None:
        metrics_summary["numerical_score"].append(numerical_score)
    if pass_k_score is not None:
        metrics_summary["pass_k_score"].append(pass_k_score)

    results.append({
        "id": sample["id"],
        "category": category,
        "question": question,
        "expected_answer": expected_answer,
        "model_response": model_response,
        "exact_match": em_score,
        "bleu_score": bleu_score,
        "numerical_score": numerical_score,
        "pass_k_score": pass_k_score
    })

# 计算综合得分
def compute_average(metric_list):
    return round(sum(metric_list) / len(metric_list), 4) if metric_list else None

summary_results = {
    "total_questions": len(results),
    "average_exact_match": compute_average(metrics_summary["exact_match"]),
    "average_bleu_score": compute_average(metrics_summary["bleu_score"]),
    "average_numerical_score": compute_average(metrics_summary["numerical_score"]),
    "average_pass_k_score": compute_average(metrics_summary["pass_k_score"]),
    "overall_score": compute_average(
        metrics_summary["exact_match"] + metrics_summary["bleu_score"] +
        metrics_summary["numerical_score"] + metrics_summary["pass_k_score"]
    )
}

# 保存结果
results_path = "./evaluation_results.json"
summary_path = "./evaluation_summary.json"

with open(results_path, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=4, ensure_ascii=False)

with open(summary_path, "w", encoding="utf-8") as f:
    json.dump(summary_results, f, indent=4, ensure_ascii=False)

print(f"✅ 评估完成！详细结果保存在 {results_path}，综合评分存于 {summary_path}")
