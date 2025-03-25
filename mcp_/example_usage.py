import asyncio
import json
import sys
import os
import httpx

# 服务端口
PORT = 8080


async def print_banner():
    """打印欢迎横幅"""
    banner = """
 __  __  ___  ___   _____ ___   ___  _     ___ 
|  \/  |/ __|| _ \ |_   _/ _ \ / _ \| |   / __|
| |\/| | (__ |  _/   | || (_) | (_) | |__| (__ 
|_|  |_|\___||_|     |_| \___/ \___/|____|\___|
                                               
    轻量级模块化工具框架示例
    """
    print(banner)
    print("=" * 60)
    print("")


async def start_server():
    """启动服务器"""
    try:
        # 构建服务器启动命令
        cmd = f"{sys.executable} {os.path.join(os.path.dirname(__file__), 'browser.py')}"
        
        # 使用asyncio子进程启动服务器
        print(f"启动服务器: {cmd}")
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # 等待服务器启动
        await asyncio.sleep(2)
        print(f"服务器已启动，端口: {PORT}\n")
        
        return process
    except Exception as e:
        print(f"启动服务器时出错: {e}")
        sys.exit(1)


async def list_tools():
    """列出所有可用工具"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"http://localhost:{PORT}/list_tools")
            response.raise_for_status()
            tools = response.json()
            
            print(f"发现 {len(tools)} 个可用工具:\n")
            
            for i, tool in enumerate(tools, 1):
                name = tool.get("name", "未知")
                description = tool.get("description", "无描述")
                
                print(f"{i}. {name} - {description}")
                
                # 打印输入模式
                schema = tool.get("schema", {})
                required = schema.get("required", [])
                properties = schema.get("properties", {})
                
                if properties:
                    print("   参数:")
                    for param_name, param_info in properties.items():
                        req = "*" if param_name in required else " "
                        param_type = param_info.get("type", "any")
                        param_desc = param_info.get("description", "")
                        print(f"   {req} {param_name} ({param_type}): {param_desc}")
                
                print("")
            
            return tools
    except Exception as e:
        print(f"获取工具列表时出错: {e}")
        return []


async def call_tool(tool_name, arguments=None):
    """调用特定工具"""
    if arguments is None:
        arguments = {}
    
    print(f"调用工具: {tool_name}")
    print(f"参数: {json.dumps(arguments, ensure_ascii=False, indent=2)}\n")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://localhost:{PORT}/call_tool",
                json={"name": tool_name, "arguments": arguments}
            )
            response.raise_for_status()
            result = response.json()
            
            # 处理响应
            print("工具响应:")
            for content in result:
                content_type = content.get("type")
                
                if content_type == "text":
                    print(f"\n{content.get('text')}")
                elif content_type == "image":
                    print(f"[图片: {content.get('alt', '无描述')}]")
                else:
                    print(f"[未知响应类型: {content_type}]")
            
            print("\n")
            return result
    except Exception as e:
        print(f"调用工具时出错: {e}")
        return []


async def run_examples():
    """运行一系列示例"""
    print("=" * 60)
    print("开始运行示例...")
    print("=" * 60)
    print("")
    
    # 示例1: 加法计算
    print("示例1: 加法计算")
    print("-" * 30)
    await call_tool("add", {"a": 5, "b": 7})
    
    # 示例2: 文件读取
    print("示例2: 文件读取")
    print("-" * 30)
    # 读取当前脚本文件
    await call_tool("read_file", {"file_path": __file__})
    
    # 示例3: 获取天气预报
    print("示例3: 获取天气预报 (旧金山)")
    print("-" * 30)
    await call_tool("get_forecast", {"latitude": 37.7749, "longitude": -122.4194, "days": 2})
    
    # 示例4: 路径扫描
    print("示例4: 扫描当前目录")
    print("-" * 30)
    await call_tool("scan_path", {"path": os.path.dirname(__file__), "recursive": False})
    
    # 示例5: 动态网页内容获取
    print("示例5: 获取动态网页内容")
    print("-" * 30)
    await call_tool("get_dynamic_webpage", {"url": "https://example.com", "wait_time": 1000})


async def shutdown_server(process):
    """关闭服务器"""
    if process:
        print("正在关闭服务器...")
        process.terminate()
        await process.wait()
        print("服务器已关闭")


async def main():
    """主函数"""
    await print_banner()
    
    # 启动服务器
    server_process = await start_server()
    
    try:
        # 列出所有工具
        await list_tools()
        
        # 运行示例
        await run_examples()
    finally:
        # 关闭服务器
        await shutdown_server(server_process)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"运行示例时发生错误: {e}")
    finally:
        print("\n示例运行完成") 