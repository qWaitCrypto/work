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
import json
import asyncio
import aiohttp
import os
import re
from nltk.translate.bleu_score import sentence_bleu
from Levenshtein import distance as levenshtein_distance
from bert_score import score

# os.environ['HTTP_PROXY'] = 'http://127.0.0.1:7890'
# os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:7890'

# ✅ API 配置
API_URL = "https://api.deepseek.com/v1/chat/completions"
API_KEY = "sk-f267b40f68fe47fbba06d9534b988214"

# ✅ 读取数据集
dataset_path = "./evaluation_dataset.json"
with open(dataset_path, "r", encoding="utf-8") as f:
    dataset = json.load(f)

dataset = dataset[:10]  # 仅取前 100 条数据进行测试

# ✅ 提取期望答案（支持多答案）
def extract_expected_answers(expected):
    if isinstance(expected, dict) and "text" in expected:
        return expected["text"]
    elif isinstance(expected, list):
        return expected
    return [str(expected)]

# ✅ 计算 Jaccard 相似度
def jaccard_similarity(pred, expected):
    """计算 Jaccard 相似度（词级匹配）"""
    pred_set = set(pred.split())
    expected_set = set(expected.split())
    intersection = len(pred_set & expected_set)
    union = len(pred_set | expected_set)
    return intersection / union if union != 0 else 0

# ✅ 计算 Levenshtein 相似度
def normalized_levenshtein(pred, expected):
    """计算归一化的 Levenshtein 距离"""
    dist = levenshtein_distance(pred, expected)
    max_len = max(len(pred), len(expected))
    return 1 - (dist / max_len)  # 归一化到 0-1

# ✅ 计算 BERTScore（可选，如果有 GPU）
def compute_bertscore(pred, expected):
    """计算 BERTScore 语义匹配分数"""
    try:
        P, R, F1 = score([pred], [expected], lang="zh", rescale_with_baseline=True)
        return F1.item()  # 返回 F1 分数
    except Exception as e:
        print(f"❌ BERTScore 计算失败: {e}")
        return 0  # 避免错误

# ✅ 评估模型输出
def evaluate_answer(pred, expected):
    possible_answers = extract_expected_answers(expected)
    pred_clean = pred.strip().lower()

    # 计算多个 `possible_answers` 的评分，取最高值
    jaccard_score = max(jaccard_similarity(pred_clean, ans.lower()) for ans in possible_answers)
    print(f"Jaccard score: {jaccard_score}")
    levenshtein_score = max(normalized_levenshtein(pred_clean, ans.lower()) for ans in possible_answers)
    print(f"Levenshtein score: {levenshtein_score}")
    bert_score = max(compute_bertscore(pred_clean, ans) for ans in possible_answers)
    print(f"BERT score: {bert_score}")

    # 计算最终得分（加权）
    final_score = round((jaccard_score * 0.4 + levenshtein_score * 0.4 + bert_score * 0.2), 4)
    return final_score

# ✅ 异步请求函数
async def query_model(session, question):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "You are an AI assistant trained to provide precise and concise answers."},
            {"role": "user", "content": question}
        ],
        "max_tokens": 256
    }
    async with session.post(API_URL, json=payload, headers=headers) as response:
        try:
            result = await response.json()
            return result.get("choices", [{}])[0].get("message", {}).get("content", "").strip() or "No response"
        except Exception as e:
            print(f"❌ API 请求错误: {e}")
            return "Error"

# ✅ 运行并发评估
async def run_evaluation():
    results = []
    async with aiohttp.ClientSession() as session:
        tasks = [asyncio.create_task(query_model(session, sample["question"])) for sample in dataset]
        responses = await asyncio.gather(*tasks)

        # 处理评测结果
        for sample, response in zip(dataset, responses):
            question = sample["question"]
            expected_answer = sample["expected_answer"]
            final_score = evaluate_answer(response, expected_answer)

            results.append({
                "id": sample["id"],
                "question": question,
                "expected_answer": expected_answer,
                "model_response": response,
                "final_score": final_score
            })

    # ✅ 计算整体评分
    final_scores = [r["final_score"] for r in results]
    overall_score = {
        "total_questions": len(results),
        "average_final_score": round(sum(final_scores) / len(final_scores), 4)
    }

    # ✅ 保存结果
    with open("evaluation_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)

    with open("evaluation_summary.json", "w", encoding="utf-8") as f:
        json.dump(overall_score, f, indent=4, ensure_ascii=False)

    print(f"✅ 评估完成！详细结果保存在 `evaluation_results.json`，综合评分保存在 `evaluation_summary.json`")

# ✅ 运行评估
asyncio.run(run_evaluation())

