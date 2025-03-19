import os
import time
import json

os.environ['HTTP_PROXY'] = 'http://127.0.0.1:7890'
os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:7890'

import sglang as sgl
from sglang.utils import print_highlight


@sgl.function
def multi_turn_question(s, question_1, question_2):
    s += sgl.system("You are a helpful assistant.")
    s += sgl.user(question_1)
    s += sgl.assistant(sgl.gen("answer_11", max_tokens=1024, temperature=0))
    s += sgl.user(question_2)
    s += sgl.assistant(sgl.gen("answer_2", max_tokens=1024, temperature=0))


@sgl.function
def tool_use(s, question):
    s += sgl.assistant(
        "To answer this question: "
        + question
        + ". I need to use a "
        + sgl.gen("tool", choices=["calculator", "search engine"])
        + ". "
    )
    if s["tool"] == "calculator":
        s += sgl.assistant("The math expression is: " + sgl.gen("expression"))
    elif s["tool"] == "search engine":
        s += sgl.assistant("The key word to search is: " + sgl.gen("word"))


# 新增：生成长上下文的测试函数，num_turns 表示对话轮数
@sgl.function
def long_context_test(s, num_turns: int = 50):
    s += sgl.system("You are a helpful assistant designed to handle very long contexts.")
    # 每轮对话设置适中的 max_tokens，避免单次生成过长
    for i in range(num_turns):
        s += sgl.user(f"Turn {i + 1}: Please provide a detailed explanation on topic {i + 1}.")
        s += sgl.assistant(sgl.gen(f"answer_{i + 1}", max_tokens=256, temperature=0))
    s += sgl.system("Long context test finished.")


def single():
    state = multi_turn_question.run(
        question_1="中国的首都在哪?",
        question_2="列出两个中国的节日",
    )
    for m in state.messages():
        print(m["role"], ":", m["content"])


def stream():
    state = multi_turn_question.run(
        question_1="What is the capital of the United States?",
        question_2="List two local attractions.",
        stream=True,
    )
    for out in state.text_iter():
        print(out, end="", flush=True)
    print()


def batch():
    states = multi_turn_question.run_batch(
        [
            {
                "question_1": "What is the capital of the United States?",
                "question_2": "List two local attractions.",
            },
            {
                "question_1": "What is the capital of France?",
                "question_2": "What is the population of this city?",
            },
        ]
    )
    for s in states:
        print(s.messages())


# 评估长上下文测试函数：对不同轮数进行测试并记录生成耗时、token 数量及简单质量指标
def evaluate_long_context():
    # 定义不同的对话轮数，用于测试上下文极限
    turn_counts = [40, 50, 80, 40, 50]
    results = {}

    # 简单的 token 计数函数（启发式，根据空格拆分；可根据实际情况替换为准确的 tokenizer）
    def count_tokens(text):
        return len(text.split())

    for n in turn_counts:
        print_highlight(f"\n测试 {n} 轮对话的长上下文性能...")
        start_time = time.perf_counter()
        # 调用 long_context_test 函数生成多轮对话
        state = long_context_test.run(num_turns=n)
        end_time = time.perf_counter()
        elapsed = end_time - start_time

        messages = state.messages()
        num_messages = len(messages)
        total_tokens = sum(count_tokens(m["content"]) for m in messages)
        # 只统计 assistant 消息
        assistant_messages = [m for m in messages if m["role"] == "assistant"]
        if assistant_messages:
            avg_length_chars = sum(len(m["content"]) for m in assistant_messages) / len(assistant_messages)
            avg_tokens = sum(count_tokens(m["content"]) for m in assistant_messages) / len(assistant_messages)
        else:
            avg_length_chars = 0
            avg_tokens = 0

        result = {
            "num_turns": n,
            "elapsed_time_sec": elapsed,
            "total_messages": num_messages,
            "total_tokens": total_tokens,
            "num_assistant_messages": len(assistant_messages),
            "avg_assistant_message_length_chars": avg_length_chars,
            "avg_assistant_message_tokens": avg_tokens,
        }
        results[n] = result
        print_highlight(
            f"轮数: {n}，耗时: {elapsed:.4f} 秒，消息总数: {num_messages}，assistant 消息数量: {len(assistant_messages)}")
        print_highlight(f"assistant 消息平均长度: {avg_length_chars:.2f} 字符，平均 tokens: {avg_tokens:.2f}")
        print_highlight(f"总 token 数: {total_tokens}")

        # 输出部分 assistant 消息供快速预览
        preview = assistant_messages[:2]
        for idx, msg in enumerate(preview, start=1):
            print_highlight(f"Preview {idx}: {msg['content'][:100]}...")

    # 将评估结果保存到 JSON 文件
    with open("long_context_test_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # 同时保存各轮数对应的完整对话内容
    messages_dict = {}
    for n in turn_counts:
        state_n = long_context_test.run(num_turns=n)
        messages_dict[n] = state_n.messages()
    with open("long_context_messages.json", "w", encoding="utf-8") as f:
        json.dump(messages_dict, f, indent=2, ensure_ascii=False)

    print_highlight("长上下文测试完成，结果已保存到 long_context_test_results.json 与 long_context_messages.json")


if __name__ == "__main__":
    backend = sgl.OpenAI(
        model_name="deepseek-chat",
        base_url="http://10.200.3.30:22/v1/",
        api_key="sk-f267b40f68fe47fbba06d9534b988214",
    )
    sgl.set_default_backend(backend)

    # # 示例：运行批量问答
    # print("\n========== batch ==========\n")
    # batch()

    # 示例：运行长上下文测试并评估不同轮数下的表现
    print("\n========== long context evaluation ==========\n")
    evaluate_long_context()
