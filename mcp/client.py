"""
MCP客户端模块

本模块实现了一个MCP（Model-Context-Protocol）客户端，用于连接到MCP服务器并使用本地LLM处理用户查询。
客户端可以连接到Python或JavaScript实现的MCP服务器，并使用服务器提供的工具来增强AI的能力。

主要功能：
1. 连接到MCP服务器（Python或JavaScript）
2. 使用本地LLM处理用户查询
3. 调用服务器提供的工具并整合结果
4. 提供交互式聊天界面

依赖项：
- mcp: 用于MCP客户端会话和通信
- openai: 用于与本地LLM交互
- dotenv: 用于加载环境变量
"""

import asyncio
import json
from typing import Optional, List, Dict, Any
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()  # 从.env文件加载环境变量（如API密钥）

# 初始化OpenAI客户端
client = OpenAI(
    base_url="http://122.191.109.151:1112/v1/",  # 本地LLM服务地址
    api_key="sk-f267b40f68fe47fbba06d9534b988214",  # API密钥
)


class MCPClient:
    """MCP客户端类
    
    该类实现了与MCP服务器的连接、工具调用和用本地LLM处理查询的功能。
    它提供了一个交互式聊天循环，允许用户输入查询并获取增强的AI响应。
    """
    
    def __init__(self, transport: str = "stdio"):
        """初始化MCP客户端
        
        创建必要的会话对象和退出栈。
        初始时，客户端未连接到任何服务器。
        """
        # 初始化会话对象
        self.transport = transport
        self.session: Optional[ClientSession] = None  # MCP客户端会话，用于与服务器通信
        self.exit_stack = AsyncExitStack()  # 异步退出栈，用于管理异步资源
        self.messages: List[Dict[str, Any]] = []  # 对话历史记录
        self.tools: List[Dict[str, Any]] = []  # 可用工具列表
        self.sse_url: str = "http://127.0.0.1:8000/sse"
        # 添加系统提示词
        self.messages.append({
            "role": "system",
            "content": """你是一个很牛逼的AI助手。当你需要使用工具时，请遵循以下规则：
            1. 首先，用一句话告诉用户你正在做什么，例如"我正在查询数据，请稍等..."或"我正在访问网页获取信息..."
            2. 然后再提供工具调用信息
            3. 最后，根据工具返回的结果，用通俗易懂的语言解释给用户
            
            请确保你的回复既专业又友好，让用户了解你正在进行的操作。"""
        })

    async def connect_to_server(self, server_script_path):
        if(self.transport=='stdio'):
            is_python = server_script_path.endswith('.py')
            is_js = server_script_path.endswith('.js')
            if not (is_python or is_js):
                raise ValueError("服务器脚本必须是.py或.js文件")

            # 根据脚本类型选择命令
            command = "python" if is_python else "node"
            # 创建服务器参数
            server_params = StdioServerParameters(
                command=command,
                args=[server_script_path],
                env=None  # 使用当前环境变量
            )
            # 创建stdio传输通道
            stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
            self.stdio, self.write = stdio_transport
            # 创建客户端会话
            self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

        if(self.transport=='sse'):
            sse_transport = await self.exit_stack.enter_async_context(sse_client(self.sse_url))
            self.sse, self.write = sse_transport
            self.session = await self.exit_stack.enter_async_context(ClientSession(self.sse, self.write))

        # 初始化会话
        await self.session.initialize()

        # 列出可用工具
        response = await self.session.list_tools()
        self.tools = [{
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema
            }
        } for tool in response.tools]
        print("\n已连接到服务器，可用工具:", [tool["function"]["name"] for tool in self.tools])

    async def process_query(self, query: str) -> str:
        """处理用户查询
        
        使用本地LLM和可用工具处理用户查询。如果LLM决定使用工具，
        客户端会调用相应的工具并将结果提供给LLM进行进一步处理。
        
        参数:
            query: 用户查询文本
            
        返回:
            处理后的响应文本，包括AI回复和工具调用结果
        """
        # 添加用户查询到消息历史
        self.messages.append({
            "role": "user",
            "content": query
        })

        # 调用本地LLM
        response = client.chat.completions.create(
            model="./qwq",  # 使用QwQ模型
            messages=self.messages,
            temperature=0.1,
            top_p=0.95,
            max_tokens=1024,
            stream=False,  # 非流式响应
            tools=self.tools,
            tool_choice="auto"  # 允许模型自动选择是否使用工具
        )

        # 获取助手回复
        assistant_message = response.choices[0].message
        # print("Assistant message:", assistant_message)  # 添加调试输出
        
        # 保存原始回复内容
        original_content = assistant_message.content or ""
        if(original_content != ""):
            print("\n" + original_content)
        
        # 添加助手回复到消息历史
        self.messages.append({
            "role": "assistant",
            "content": original_content
        })
        print(assistant_message.tool_calls)
        # 检查是否有工具调用
        if assistant_message.tool_calls:
            for tool_call in assistant_message.tool_calls:
                # 添加工具调用到消息历史，保留原始内容
                self.messages.append({
                    "role": "assistant",
                    "content": original_content,  # 保留原始内容
                    "tool_calls": [{
                        "id": tool_call.id,
                        "type": "function",
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments
                        }
                    }]
                })

                # 执行工具调用
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                print("Tool call:", tool_name, tool_args)  # 添加调试输出

                # 调用工具并获取结果
                tool_result = await self.session.call_tool(tool_name, tool_args)
                print("Tool result:", tool_result)  # 添加调试输出
                
                # 添加工具结果到消息历史
                self.messages.append({
                    "role": "tool",
                    "content": str(tool_result),
                    "tool_call_id": tool_call.id
                })

                # 让LLM处理工具调用结果
                final_response = client.chat.completions.create(
                    model="./qwq",
                    messages=self.messages,
                    temperature=0.1,
                    top_p=0.95,
                    max_tokens=1024,
                    stream=False,
                    tools=self.tools,
                    tool_choice="auto"
                )

                # 添加最终回复到消息历史
                final_message = final_response.choices[0].message
                # print("Final message:", final_message)  # 添加调试输出
                self.messages.append({
                    "role": "assistant",
                    "content": final_message.content
                })

                return final_message.content

        return original_content  # 如果没有工具调用，返回原始内容

    async def chat_loop(self):
        """运行交互式聊天循环
        
        提供一个命令行界面，允许用户输入查询并显示响应。
        用户可以输入'quit'退出聊天循环。
        """
        print("\nMCP客户端已启动！")
        print("输入您的查询或输入'quit'退出。")

        # 持续循环直到用户选择退出
        while True:
            try:
                # 获取用户输入
                query = input("\n查询: ").strip()

                # 检查是否退出
                if query.lower() == 'quit':
                    break

                # 处理查询并显示响应
                response = await self.process_query(query)
                print("\n" + response)

            except Exception as e:
                # 处理错误
                print(f"\n错误: {str(e)}")

    async def cleanup(self):
        """清理资源
        
        关闭所有打开的资源和连接。
        应在客户端使用完毕后调用此方法。
        """
        # 关闭异步退出栈中的所有资源
        await self.exit_stack.aclose()


async def main():
    """MCP 客户端主函数"""
    if len(sys.argv) < 3:
        print("用法: python client.py <stdio/sse> <服务器路径>")
        sys.exit(1)

    transport = sys.argv[1]  # 连接方式
    server_path = sys.argv[2]

    client = MCPClient(transport)
    try:
        await client.connect_to_server(server_path)
        await client.chat_loop()
    finally:
        await client.cleanup()


if __name__ == "__main__":
    # 当脚本直接运行时执行
    import sys

    # 运行主异步函数
    asyncio.run(main())