"""
计算器工具示例
"""

# 确保导入路径正确
import sys
import os
from pathlib import Path

# 添加项目根目录到系统路径
root_dir = Path(__file__).parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import mcp.types as types
from typing import List, Union, Dict, Any
from core.registry import register_tool, ToolHandler, registered_tools, tool_handlers

print(f"[calculator_tool] 导入时，当前已注册工具: {registered_tools.keys()}")


@register_tool
class AddToolHandler(ToolHandler):
    """加法工具处理器"""
    
    @staticmethod
    def tool_name() -> str:
        return "add"
    
    @staticmethod
    def tool_description() -> str:
        return "将两个数字相加"
    
    @staticmethod
    def input_schema() -> dict:
        return {
            "type": "object",
            "properties": {
                "a": {"type": "number", "description": "第一个数字"},
                "b": {"type": "number", "description": "第二个数字"}
            },
            "required": ["a", "b"]
        }
    
    async def handle(self, name: str, arguments: Dict[str, Any] | None) -> List[Union[types.TextContent, types.ImageContent, types.EmbeddedResource]]:
        """执行加法操作"""
        if not arguments or "a" not in arguments or "b" not in arguments:
            return [types.TextContent(type="text", text="错误：缺少a或b参数")]
        
        try:
            a = float(arguments.get("a", 0))
            b = float(arguments.get("b", 0))
            
            result = a + b
            
            # 如果结果是整数，去掉小数部分
            if result.is_integer():
                result = int(result)
            
            return [types.TextContent(type="text", text=f"{a} + {b} = {result}")]
        
        except ValueError:
            return [types.TextContent(type="text", text="错误：a和b必须是数字")]
        except Exception as e:
            return [types.TextContent(type="text", text=f"计算时发生错误: {str(e)}")]


@register_tool
class MultiplyToolHandler(ToolHandler):
    """乘法工具处理器"""
    
    @staticmethod
    def tool_name() -> str:
        return "multiply"
    
    @staticmethod
    def tool_description() -> str:
        return "将两个数字相乘"
    
    @staticmethod
    def input_schema() -> dict:
        return {
            "type": "object",
            "properties": {
                "a": {"type": "number", "description": "第一个数字"},
                "b": {"type": "number", "description": "第二个数字"}
            },
            "required": ["a", "b"]
        }
    
    async def handle(self, name: str, arguments: Dict[str, Any] | None) -> List[Union[types.TextContent, types.ImageContent, types.EmbeddedResource]]:
        """执行乘法操作"""
        if not arguments or "a" not in arguments or "b" not in arguments:
            return [types.TextContent(type="text", text="错误：缺少a或b参数")]
        
        try:
            a = float(arguments.get("a", 0))
            b = float(arguments.get("b", 0))
            
            result = a * b
            
            # 如果结果是整数，去掉小数部分
            if result.is_integer():
                result = int(result)
            
            return [types.TextContent(type="text", text=f"{a} × {b} = {result}")]
        
        except ValueError:
            return [types.TextContent(type="text", text="错误：a和b必须是数字")]
        except Exception as e:
            return [types.TextContent(type="text", text=f"计算时发生错误: {str(e)}")]


@register_tool
class CalculateToolHandler(ToolHandler):
    """通用计算工具处理器"""
    
    @staticmethod
    def tool_name() -> str:
        return "calculate"
    
    @staticmethod
    def tool_description() -> str:
        return "执行基本的数学运算，支持 +, -, *, /, ** (幂运算)"
    
    @staticmethod
    def input_schema() -> dict:
        return {
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": "要计算的数学表达式，例如 '2 + 3 * 4'"}
            },
            "required": ["expression"]
        }
    
    async def handle(self, name: str, arguments: Dict[str, Any] | None) -> List[Union[types.TextContent, types.ImageContent, types.EmbeddedResource]]:
        """执行数学表达式计算"""
        if not arguments or "expression" not in arguments:
            return [types.TextContent(type="text", text="错误：缺少expression参数")]
        
        try:
            expression = arguments.get("expression", "")
            
            # 安全检查：确保表达式只包含允许的字符
            if not self._is_safe_expression(expression):
                return [types.TextContent(type="text", text="错误：表达式包含不允许的字符或操作")]
            
            # 计算表达式
            result = eval(expression)
            
            # 如果结果是整数，去掉小数部分
            if isinstance(result, float) and result.is_integer():
                result = int(result)
            
            return [types.TextContent(type="text", text=f"{expression} = {result}")]
        
        except SyntaxError:
            return [types.TextContent(type="text", text="错误：表达式语法错误")]
        except (NameError, TypeError):
            return [types.TextContent(type="text", text="错误：表达式只能包含数字和基本运算符 (+, -, *, /, **)")] 
        except ZeroDivisionError:
            return [types.TextContent(type="text", text="错误：除数不能为零")]
        except Exception as e:
            return [types.TextContent(type="text", text=f"计算时发生错误: {str(e)}")]
    
    def _is_safe_expression(self, expression: str) -> bool:
        """检查表达式是否安全（只包含数字和基本运算符）"""
        import re
        
        # 只允许数字、运算符和括号
        allowed_pattern = r'^[0-9\+\-\*\/\(\)\.\s\^]*$'
        if not re.match(allowed_pattern, expression):
            return False
        
        # 不允许使用__
        if '__' in expression:
            return False
        
        # 不允许使用eval、exec等危险函数
        dangerous_functions = ['eval', 'exec', 'import', 'open', 'os', 'sys', 'globals', 'locals']
        for func in dangerous_functions:
            if func in expression:
                return False
        
        return True 