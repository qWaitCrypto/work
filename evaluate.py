import json
import asyncio
import aiohttp
import os
from bert_score import score

# 系统提示词
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

# API 配置
API_URL = "http://122.191.109.151:1112/v1/chat/completions"
API_KEY = "sk-f267b40f68fe47fbba06d9534b988214"

# 读取数据集
def load_dataset(path, limit=None):
    """加载数据集并可选择限制样本数量"""
    with open(path, "r", encoding="utf-8") as f:
        dataset = json.load(f)
    
    if limit and limit > 0:
        dataset = dataset[:limit]
    
    return dataset

# 提取期望答案
def extract_expected_answers(expected):
    """提取期望答案，支持多种格式"""
    if isinstance(expected, dict) and "text" in expected:
        return expected["text"]
    elif isinstance(expected, list):
        return expected
    return [str(expected)]

# 计算BERTScore
def compute_bertscore(pred, expected):
    """计算BERTScore语义匹配分数"""
    try:
        # 确保输入是列表格式
        if not isinstance(pred, list):
            pred = [pred]
        if not isinstance(expected, list):
            expected = [expected]
        
        # 计算BERTScore
        P, R, F1 = score(pred, expected, model_type="bert-base-uncased", verbose=False)
        
        # 返回F1分数（通常被视为BERTScore的主要指标）
        return F1.mean().item()
    except Exception as e:
        print(f"❌ BERTScore计算失败: {e}")
        return 0

# 评估模型输出
def evaluate_answer(pred, expected):
    """使用BERTScore评估模型输出与期望答案的匹配度"""
    possible_answers = extract_expected_answers(expected)
    pred_clean = pred.strip()
    
    # 计算与所有可能答案的BERTScore，取最高值
    bert_scores = [compute_bertscore(pred_clean, ans) for ans in possible_answers]
    final_score = max(bert_scores) if bert_scores else 0
    
    return round(final_score, 4)

# 异步请求函数
async def query_model(session, question):
    """向API发送请求获取模型回答"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question}
        ],
        "max_tokens": 256
    }
    
    try:
        async with session.post(API_URL, json=payload, headers=headers) as response:
            if response.status == 200:
                result = await response.json()
                return result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            else:
                error_text = await response.text()
                print(f"❌ API请求失败 (状态码: {response.status}): {error_text}")
                return f"Error: API请求失败 (状态码: {response.status})"
    except Exception as e:
        print(f"❌ API请求异常: {e}")
        return f"Error: {str(e)}"

# 运行评估
async def run_evaluation(dataset_path, limit=None, output_prefix="evaluation"):
    """运行评估流程"""
    print(f"📊 开始评估流程...")
    
    # 加载数据集
    dataset = load_dataset(dataset_path, limit)
    print(f"✅ 已加载数据集，共{len(dataset)}个样本")
    
    results = []
    total_score = 0
    
    # 创建HTTP会话
    async with aiohttp.ClientSession() as session:
        # 创建并发任务
        tasks = []
        for sample in dataset:
            task = asyncio.create_task(query_model(session, sample["question"]))
            tasks.append((sample, task))
        
        # 处理结果
        for i, (sample, task) in enumerate(tasks):
            try:
                print(f"⏳ 处理样本 {i+1}/{len(tasks)}...")
                response = await task
                
                # 评估回答
                score = evaluate_answer(response, sample["expected_answer"])
                total_score += score
                
                # 记录结果
                results.append({
                    "id": sample.get("id", i+1),
                    "question": sample["question"],
                    "expected_answer": sample["expected_answer"],
                    "model_response": response,
                    "bert_score": score
                })
                
                print(f"✅ 样本 {i+1} 评分: {score:.4f}")
            except Exception as e:
                print(f"❌ 处理样本 {i+1} 时出错: {e}")
    
    # 计算平均分数
    avg_score = total_score / len(results) if results else 0
    
    # 创建总结报告
    summary = {
        "total_samples": len(results),
        "average_bert_score": round(avg_score, 4),
        "evaluation_time": "完成"
    }
    
    # 保存结果
    results_file = f"{output_prefix}_results.json"
    summary_file = f"{output_prefix}_summary.json"
    
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
    
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=4, ensure_ascii=False)
    
    print(f"✅ 评估完成！")
    print(f"📊 平均BERTScore: {avg_score:.4f}")
    print(f"📄 详细结果已保存至: {results_file}")
    print(f"📄 评估摘要已保存至: {summary_file}")

# 主函数
if __name__ == "__main__":
    # 配置参数
    dataset_path = "./evaluation_dataset.json"
    sample_limit = 100  # 设置为None可评估整个数据集
    
    # 运行评估
    asyncio.run(run_evaluation(dataset_path, sample_limit))

