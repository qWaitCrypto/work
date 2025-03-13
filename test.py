import sglang as sgl
from sglang.utils import print_highlight
import threading
import time
import random


@sgl.function
def multi_turn_question(s, question_1, question_2):
    s += sgl.system("You are a helpful assistant.")
    s += sgl.user(question_1)
    s += sgl.assistant(sgl.gen("answer_1", max_tokens=1024, temperature=0))
    s += sgl.user(question_2)
    s += sgl.assistant(sgl.gen("answer_2", max_tokens=1024, temperature=0))


def single():
    state = multi_turn_question.run(
        question_1="中国的首都在哪?",
        question_2="列出两个中国的节日",
    )

    for m in state.messages():
        print(m["role"], ":", m["content"])


def process_user_request(user_id, questions):
    """处理单个用户的请求"""
    print(f"\n========== 处理用户{user_id}的请求 ==========\n")
    state = multi_turn_question.run(
        question_1=questions[0],
        question_2=questions[1]
    )
    print(f"\n----- 用户{user_id}的对话结果 -----\n")
    for m in state.messages():
        print(m["role"], ":", m["content"])


def generate_question_pairs(topics, num_pairs=10):
    """
    根据主题列表生成问题对
    
    参数:
    topics: 主题列表
    num_pairs: 要生成的问题对数量
    
    返回:
    问题对列表，每个元素是包含两个问题的列表
    """
    # 预定义的问题模板 - 确保每个模板只有一个或两个占位符
    single_param_templates = [
        "什么是{}?",
        "{}的主要特点是什么?",
        "{}有哪些应用?",
        "如何学习{}?",
        "{}的历史是怎样的?",
        "推荐一些关于{}的资源",
        "{}的未来发展趋势如何?",
        "{}的优缺点是什么?",
        "如何在实际中应用{}?"
    ]
    
    double_param_templates = [
        "{}与{}有什么区别?",
        "{}和{}哪个更好?",
        "如何将{}应用到{}中?",
        "{}对{}有什么影响?"
    ]
    
    # 生成问题对
    question_pairs = []
    for _ in range(num_pairs):
        # 随机选择一个主题
        topic = random.choice(topics)
        
        # 为第一个问题随机选择单参数模板
        template1 = random.choice(single_param_templates)
        question1 = template1.format(topic)
        
        # 为第二个问题随机决定使用单参数还是双参数模板
        if random.random() < 0.3:  # 30%的概率使用双参数模板
            template2 = random.choice(double_param_templates)
            # 随机选择另一个不同的主题
            other_topics = [t for t in topics if t != topic]
            if other_topics:
                other_topic = random.choice(other_topics)
                question2 = template2.format(topic, other_topic)
            else:
                # 如果没有其他主题，就使用单参数模板
                template2 = random.choice(single_param_templates)
                question2 = template2.format(topic)
        else:
            # 使用单参数模板
            template2 = random.choice(single_param_templates)
            question2 = template2.format(topic)
        
        question_pairs.append([question1, question2])
    
    return question_pairs


def simulate_concurrent_users(questions_list, num_users=None):
    """
    模拟多个用户同时发送请求
    
    参数:
    questions_list: 问题列表，每个元素是一个包含两个问题的列表或元组
    num_users: 要模拟的用户数量，默认为None表示使用整个问题列表
    """
    # 如果指定了用户数量，则只使用相应数量的问题
    if num_users is not None and num_users > 0:
        # 确保不超过问题列表长度
        num_users = min(num_users, len(questions_list))
        # 随机选择问题
        selected_questions = random.sample(questions_list, num_users)
    else:
        selected_questions = questions_list
    
    threads = []
    
    # 根据问题列表自动创建用户
    for i, questions in enumerate(selected_questions):
        # 确保每个用户有两个问题
        if len(questions) < 2:
            print(f"警告: 用户{i+1}的问题数量不足，已跳过")
            continue
            
        # 创建线程处理用户请求
        thread = threading.Thread(
            target=process_user_request, 
            args=(i+1, questions[:2])  # 只取前两个问题
        )
        threads.append(thread)
    
    print(f"\n========== 开始模拟{len(threads)}个用户同时发送请求 ==========\n")
    
    # 启动所有线程，模拟并发请求
    for thread in threads:
        thread.start()
        # 添加很小的随机延迟，避免完全同时启动
        time.sleep(random.uniform(0.05, 0.1))
    
    # 等待所有线程完成
    for thread in threads:
        thread.join()
    
    print("\n========== 所有用户请求处理完成 ==========\n")


if __name__ == "__main__":
    backend = sgl.OpenAI(
        model_name="default",
        base_url="http://122.191.109.151:1094/v1",
        api_key="empty",
    )
    sgl.set_default_backend(backend)

    # 预定义的问题列表
    predefined_questions = [
        ["中国的首都在哪?", "列出两个中国的节日"],
        ["什么是人工智能?", "机器学习和深度学习有什么区别?"],
        ["太阳系有多少个行星?", "月球的形成理论是什么?"],
        ["推荐一本科幻小说", "谁是阿西莫夫?"],
        ["介绍一下中国的长城", "长城有多长?"],
        ["什么是量子计算?", "量子计算机与传统计算机有什么不同?"],
        ["如何学习英语?", "推荐一些英语学习方法"],
        ["什么是可持续发展?", "可再生能源有哪些?"],
        ["介绍一下莎士比亚", "莎士比亚的代表作有哪些?"],
        ["Python和JavaScript的主要区别是什么?", "哪种语言更适合Web开发?"]
    ]
    
    # 自定义主题列表
    topics = [
        "人工智能", "机器学习", "深度学习", "自然语言处理", 
        "计算机视觉", "区块链", "云计算", "大数据", 
        "物联网", "5G技术", "虚拟现实", "增强现实",
        "网络安全", "量子计算", "边缘计算", "DevOps",
        "微服务", "容器化", "serverless", "前端开发",
        "后端开发", "移动开发", "游戏开发", "数据科学"
    ]
    
    # 生成更多问题对
    generated_questions = generate_question_pairs(topics, num_pairs=15)
    
    # 合并预定义和生成的问题
    all_questions = predefined_questions + generated_questions
    
    # 运行单个请求示例
    # print("\n========== 单个用户请求示例 ==========\n")
    # single()
    
    # 模拟指定数量的用户同时发送请求
    num_concurrent_users = 10  # 可以根据需要修改
    print(f"\n========== 模拟{num_concurrent_users}个用户同时发送请求 ==========\n")
    simulate_concurrent_users(all_questions, num_concurrent_users)
