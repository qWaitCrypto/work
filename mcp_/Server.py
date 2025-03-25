import asyncio

from typing import Dict, List, Any, Union, Type

from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
from pydantic import AnyUrl
import mcp.server.stdio
import mcp.server.sse
from mcp_.core.registry import registered_tools, tool_handlers, ToolHandler, register_tool
import sys
from pathlib import Path

current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent

sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(parent_dir))

# 创建MCP服务器
server = Server("modular-tool-server")

# 共享会话状态
class SharedState:
    sessions: Dict[str, Any] = {}
    playwright = None

# 自动加载工具模块
def discover_tools(tools_dir='tools'):
    """从指定目录发现并加载工具"""
    # 确保工具目录存在
    tools_path = Path(__file__).parent / tools_dir
    if not tools_path.exists():
        tools_path.mkdir(parents=True)
        init_file = tools_path / "__init__.py"
        if not init_file.exists():
            init_file.touch()
        print(f"已创建工具目录: {tools_path}")
        return
    
    sys.path.append(str(Path(__file__).parent))
    
    # 清空之前的工具注册（避免重复）
    registered_tools.clear()
    tool_handlers.clear()
    
    print(f"开始扫描工具目录: {tools_path}")
    
    # 遍历工具模块
    module_files = list(tools_path.glob("*.py"))
    print(f"发现 {len(module_files)} 个工具模块文件")
    
    # 强制加载所有工具模块
    for file_path in module_files:
        if file_path.name.startswith("_"):  # 跳过私有文件
            continue
        
        module_name = f"{tools_dir}.{file_path.stem}"
        
        try:
            # 先尝试重新加载模块（如果之前已加载）
            if module_name in sys.modules:
                print(f"重新加载模块: {module_name}")
                import importlib
                importlib.reload(sys.modules[module_name])
            
            # 导入模块
            module = __import__(module_name, fromlist=['*'])
            print(f"已加载工具模块: {module_name}")
            
            # 查找模块中的所有ToolHandler子类并注册
            for name in dir(module):
                item = getattr(module, name)
                if (
                    isinstance(item, type) 
                    and issubclass(item, ToolHandler) 
                    and item != ToolHandler
                ):
                    # 确保这个类已经被注册
                    found = False
                    for tool_name, handler in tool_handlers.items():
                        if isinstance(handler, item):
                            found = True
                            break
                    
                    if not found:
                        # 如果没有被注册，手动注册
                        print(f"手动注册工具: {name}")
                        register_tool(item)
            
            # 在加载模块后，打印当前已注册的工具数量
            # print(len(registered_tools))
            print(f"当前已注册 {len(registered_tools)} 个工具: {', '.join(registered_tools.keys())}")
            
        except Exception as e:
            print(f"加载模块 {module_name} 失败: {str(e)}")
            import traceback
            traceback.print_exc()

# MCP服务器API实现
@server.list_resources()
async def handle_list_resources() -> list[types.Resource]:
    """列出可用资源"""
    return []

@server.read_resource()
async def handle_read_resource(uri: AnyUrl) -> str:
    """读取特定资源"""
    raise ValueError(f"不支持的 URI 模式: {uri.scheme}")

@server.list_prompts()
async def handle_list_prompts() -> list[types.Prompt]:
    """列出可用提示"""
    return []

@server.get_prompt()
async def handle_get_prompt(
    name: str, arguments: dict[str, str] | None
) -> types.GetPromptResult:
    """获取特定提示"""
    raise ValueError(f"未知提示: {name}")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """列出所有可用工具"""
    print(f"list_tools 被调用，当前已注册 {len(registered_tools)} 个工具: {', '.join(registered_tools.keys())}")
    return [
        types.Tool(
            name=tool_def["name"],
            description=tool_def["description"],
            inputSchema=tool_def["inputSchema"]
        )
        for tool_def in registered_tools.values()
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """处理工具调用请求"""
    print(f"call_tool 被调用: {name}")
    print(f"当前已注册工具处理器: {', '.join(tool_handlers.keys())}")
    
    if name in tool_handlers:
        try:
            return await tool_handlers[name].handle(name, arguments)
        except Exception as e:
            return [types.TextContent(type="text", text=f"工具执行错误: {str(e)}")]
    else:
        raise ValueError(f"未知工具: {name}")

# 主函数：启动服务器
async def main():
    """主函数 - 加载工具并启动服务器"""
    print("发现并加载工具...")
    discover_tools()

    if not registered_tools:
        print("警告: 没有找到已注册的工具")
    else:
        print(f"总共已注册 {len(registered_tools)} 个工具: {', '.join(registered_tools.keys())}")
        print(f"工具处理器: {len(tool_handlers)} 个")
        
        # 验证所有工具都有对应的处理器
        missing_handlers = [name for name in registered_tools if name not in tool_handlers]
        if missing_handlers:
            print(f"⚠️ 警告: 以下工具没有对应的处理器: {', '.join(missing_handlers)}")
        
        # 检查是否有未使用的处理器
        unused_handlers = [name for name in tool_handlers if name not in registered_tools]
        if unused_handlers:
            print(f"⚠️ 警告: 以下处理器没有对应的工具定义: {', '.join(unused_handlers)}")
    
    print("启动 MCP 服务器...")
    # 运行服务器
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="modular-tools",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

def run_server_sync():
    """同步方式运行服务器，包装异步入口"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # 如果是在Jupyter或嵌套事件循环中运行
            import nest_asyncio
            nest_asyncio.apply()
            loop.run_until_complete(main())
        else:
            loop.run_until_complete(main())
    except RuntimeError:
        asyncio.run(main())

if __name__ == "__main__":
    run_server_sync()

