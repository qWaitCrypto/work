import os

os.environ['HTTP_PROXY'] = 'http://127.0.0.1:12138'
os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:12138'

import sglang as sgl
from sglang.utils import print_highlight


@sgl.function
def multi_turn_question(s, question_1, question_2):
    s += sgl.system("You are a helpful assistant.")
    s += sgl.user(question_1)
    s += sgl.assistant(sgl.gen("answer_11", max_tokens=256))
    s += sgl.user(question_2)
    s += sgl.assistant(sgl.gen("answer_2", max_tokens=256))

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

def single():
    state = multi_turn_question.run(
        question_1="What is the capital of the United States?",
        question_2="List two local attractions.",
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


if __name__ == "__main__":
    backend = sgl.OpenAI(
        model_name="deepseek-v3",
        base_url="http://deepseek.wanjiedata.com/v1",
        api_key=" Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJleHAiOjE3NzMxMjEzNzcsImtleSI6IjVLNzVaOFROQzlGNEhNMzdQOVk3In0.zOZx4Lo0Sod6fiNuYf59oRIeP9zYIZBtccJUR4fnxOA",
    )
    sgl.set_default_backend(backend)

    # Run a single request
    print("\n========== single ==========\n")
    single()

    # # Stream output
    # print("\n========== stream ==========\n")
    # stream()
    #
    # Run a batch of requests
    # print("\n========== cal ==========\n")
    # state = tool_use("What is 2 * 2?")
    # for s in state:
    #     print(s.messages())