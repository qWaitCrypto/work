"""
文件操作工具示例
"""

import mcp.types as types
from typing import List, Union, Dict, Any
import os
import chardet
from core.registry import register_tool, ToolHandler, registered_tools, tool_handlers

@register_tool
class ReadFileToolHandler(ToolHandler):
    """文件读取工具处理器"""
    
    @staticmethod
    def tool_name() -> str:
        return "read_file"
    
    @staticmethod
    def tool_description() -> str:
        return "读取本地文件内容，自动检测编码"
    
    @staticmethod
    def input_schema() -> dict:
        return {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "要读取的文件路径"}
            },
            "required": ["file_path"]
        }
    
    async def handle(self, name: str, arguments: Dict[str, Any] | None) -> List[Union[types.TextContent, types.ImageContent, types.EmbeddedResource]]:
        """读取文件内容"""
        if not arguments or "file_path" not in arguments:
            return [types.TextContent(type="text", text="错误：缺少file_path参数")]
        
        file_path = arguments.get("file_path")
        
        # 读取文件
        content = self._read_file(file_path)
        
        # 返回结果
        return [types.TextContent(type="text", text=content)]
    
    def _read_file(self, file_path: str) -> str:
        """读取文件内容，自动检测编码"""
        try:
            # 检查文件是否存在
            if not os.path.exists(file_path):
                return f"错误：文件 '{file_path}' 不存在。"
            
            # 检查是否是文件而不是目录
            if not os.path.isfile(file_path):
                return f"错误：'{file_path}' 不是文件。"
            
            # 读取文件的前4096字节来检测编码
            with open(file_path, 'rb') as f:
                raw_data = f.read(4096)
                if not raw_data:
                    return "错误：文件为空。"
                
                # 检测文件编码
                result = chardet.detect(raw_data)
                encoding = result['encoding']
                
                # 如果检测失败，尝试常用编码
                if not encoding or result['confidence'] < 0.7:
                    encodings = ['utf-8', 'gbk', 'gb2312', 'gb18030', 'ascii']
                    for enc in encodings:
                        try:
                            with open(file_path, 'r', encoding=enc) as f:
                                f.read(4096)
                                encoding = enc
                                break
                        except UnicodeDecodeError:
                            continue
                
                if not encoding:
                    return "错误：无法确定文件编码。"
                
                # 使用检测到的编码读取整个文件
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                
                # 获取文件大小
                file_size = os.path.getsize(file_path)
                
                # 如果文件太大，只返回前10000个字符
                if file_size > 10000:
                    content = content[:10000] + f"\n... (文件内容已截断，完整文件大小: {file_size} 字节)"
                
                return content
        
        except PermissionError:
            return f"错误：没有权限读取文件 '{file_path}'。"
        except Exception as e:
            return f"读取文件时发生错误: {str(e)}"


@register_tool
class ScanPathToolHandler(ToolHandler):
    """目录扫描工具处理器"""
    
    @staticmethod
    def tool_name() -> str:
        return "scan_path"
    
    @staticmethod
    def tool_description() -> str:
        return "扫描指定路径下的文件，支持过滤和递归"
    
    @staticmethod
    def input_schema() -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "要扫描的路径，默认为当前目录"},
                "file_types": {"type": "array", "items": {"type": "string"}, "description": "要包含的文件类型，例如 ['txt', 'py']"},
                "recursive": {"type": "boolean", "description": "是否递归扫描子目录"},
                "max_depth": {"type": "integer", "description": "递归扫描的最大深度"}
            }
        }
    
    async def handle(self, name: str, arguments: Dict[str, Any] | None) -> List[Union[types.TextContent, types.ImageContent, types.EmbeddedResource]]:
        """扫描目录"""
        if not arguments:
            arguments = {}
        
        path = arguments.get("path", ".")
        file_types = arguments.get("file_types")
        recursive = arguments.get("recursive", True)
        max_depth = arguments.get("max_depth", 1)
        
        # 扫描目录
        scan_result = self._scan_path(path, file_types, recursive, max_depth)
        
        # 返回结果
        return [types.TextContent(type="text", text=scan_result)]
    
    def _scan_path(self, path: str = ".", file_types: List[str] = None, recursive: bool = True, max_depth: int = 1) -> str:
        """扫描指定路径下的文件"""
        try:
            # 检查路径是否存在
            if not os.path.exists(path):
                return f"错误：路径 '{path}' 不存在。"
            
            # 检查是否是目录
            if not os.path.isdir(path):
                return f"错误：'{path}' 不是目录。"
            
            # 初始化结果列表
            results = []
            current_depth = 0
            
            def scan_directory(current_path: str, depth: int):
                nonlocal current_depth
                current_depth = depth
                
                # 如果超过最大深度，停止扫描
                if depth > max_depth:
                    return
                
                # 遍历目录
                for item in os.listdir(current_path):
                    item_path = os.path.join(current_path, item)
                    
                    # 跳过隐藏文件和目录
                    if item.startswith('.'):
                        continue
                    
                    # 获取文件信息
                    try:
                        stat = os.stat(item_path)
                        size = stat.st_size
                        modified = stat.st_mtime
                        
                        # 格式化文件大小
                        if size < 1024:
                            size_str = f"{size} B"
                        elif size < 1024 * 1024:
                            size_str = f"{size/1024:.1f} KB"
                        else:
                            size_str = f"{size/(1024*1024):.1f} MB"
                        
                        # 获取文件扩展名
                        ext = os.path.splitext(item)[1].lower().lstrip('.')
                        
                        # 检查文件类型是否在过滤列表中
                        if file_types is None or ext in file_types:
                            # 构建文件信息字符串
                            file_info = f"{item_path} ({size_str}, 修改时间: {modified})"
                            results.append(file_info)
                        
                        # 如果是目录且需要递归，继续扫描
                        if recursive and os.path.isdir(item_path):
                            scan_directory(item_path, depth + 1)
                    
                    except Exception as e:
                        results.append(f"错误：无法访问 {item_path}: {str(e)}")
            
            # 开始扫描
            scan_directory(path, 0)
            
            # 如果没有找到文件
            if not results:
                file_types_str = ", ".join(file_types) if file_types else "所有"
                return f"在路径 '{path}' 中没有找到{file_types_str}类型的文件。"
            
            # 格式化输出
            output = f"在路径 '{path}' 中找到以下文件：\n\n"
            output += "\n".join(results)
            
            # 添加统计信息
            output += f"\n\n总计找到 {len(results)} 个文件"
            if file_types:
                output += f"（文件类型：{', '.join(file_types)}）"
            if recursive:
                output += f"（最大扫描深度：{max_depth}）"
            
            return output
        
        except Exception as e:
            return f"扫描路径时发生错误: {str(e)}"
