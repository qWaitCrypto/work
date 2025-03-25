from typing import Dict, Any, Union, List
import mcp.types as types
import inspect

# 工具注册表
registered_tools: Dict[str, dict] = {}

# 工具处理器实例映射
tool_handlers: Dict[str, Any] = {}


# 工具处理器基类
class ToolHandler:
    """所有工具处理器的基类"""

    @staticmethod
    def tool_name() -> str:
        """返回工具名称"""
        raise NotImplementedError("工具必须实现 tool_name 方法")

    @staticmethod
    def tool_description() -> str:
        """返回工具描述"""
        raise NotImplementedError("工具必须实现 tool_description 方法")

    @staticmethod
    def input_schema() -> dict:
        """返回工具输入 schema"""
        raise NotImplementedError("工具必须实现 input_schema 方法")

    async def handle(
            self,
            name: str,
            arguments: dict | None
    ) -> List[Union[types.TextContent, types.ImageContent, types.EmbeddedResource]]:
        """处理工具调用的具体实现"""
        raise NotImplementedError("工具必须实现 handle 方法")


# 工具注册装饰器
def register_tool(handler_class):
    """注册工具处理器的装饰器函数"""

    if not issubclass(handler_class, ToolHandler):
        raise TypeError(f"{handler_class.__name__} 必须是 ToolHandler 的子类")
        
    # 获取调用者信息（模块名称）
    caller_frame = inspect.stack()[1]
    caller_module = inspect.getmodule(caller_frame[0])
    module_name = caller_module.__name__ if caller_module else "未知模块"

    # 实例化处理器
    handler = handler_class()

    # 获取工具名称
    tool_name = handler.tool_name()
    
    # 检查是否已经注册了同名工具
    if tool_name in registered_tools:
        print(f"⚠️ 工具 {tool_name} 已经被注册，跳过")
        return handler_class
    
    # 获取其他元数据
    tool_description = handler.tool_description()
    input_schema = handler.input_schema()

    # 注册工具信息
    registered_tools[tool_name] = {
        "name": tool_name,
        "description": tool_description,
        "inputSchema": input_schema
    }

    # 注册处理器实例
    tool_handlers[tool_name] = handler

    print(f"已注册工具: {tool_name} (来自模块: {module_name})")
    print(f"当前已注册工具: {len(registered_tools)}个 - {', '.join(registered_tools.keys())}")
    
    return handler_class
