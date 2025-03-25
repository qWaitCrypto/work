"""
浏览器操作工具示例
"""

import asyncio
import uuid
import os
import base64
import mcp.types as types
from typing import List, Union, Dict, Any
from playwright.async_api import async_playwright
from core.registry import register_tool, ToolHandler, registered_tools, tool_handlers

# 全局共享会话状态 - 模块级变量
_sessions = {}
_playwright = None

# 页面点击后更新页面的装饰器
def update_page_after_click(func):
    async def wrapper(self, name: str, arguments: dict | None):
        global _sessions
        if not _sessions:
            return [types.TextContent(type="text", text="No active session. Please create a new session first.")]
        
        session_id = list(_sessions.keys())[-1]
        page = _sessions[session_id]["page"]
        
        new_page_future = asyncio.ensure_future(page.context.wait_for_event("page", timeout=3000))
        
        result = await func(self, name, arguments)
        try:
            new_page = await new_page_future
            await new_page.wait_for_load_state()
            _sessions[session_id]["page"] = new_page
        except:
            pass
        
        return result
    return wrapper

@register_tool
class NavigateToolHandler(ToolHandler):
    """网页导航工具处理器"""
    
    @staticmethod
    def tool_name() -> str:
        return "navigate"
    
    @staticmethod
    def tool_description() -> str:
        return "导航到指定URL，如果没有活动会话则创建一个"
    
    @staticmethod
    def input_schema() -> dict:
        return {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "要导航到的URL"}
            },
            "required": ["url"]
        }
    
    async def handle(self, name: str, arguments: Dict[str, Any] | None) -> List[Union[types.TextContent, types.ImageContent, types.EmbeddedResource]]:
        """导航到指定URL"""
        global _sessions, _playwright
        
        if not _sessions:
            # 创建新的会话
            _playwright = await async_playwright().start()
            browser = await _playwright.chromium.launch(headless=False)
            page = await browser.new_page()
            session_id = str(uuid.uuid4())
            _sessions[session_id] = {"browser": browser, "page": page}
        
        session_id = list(_sessions.keys())[-1]
        page = _sessions[session_id]["page"]
        
        url = arguments.get("url")
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url
        
        await page.goto(url)
        
        # 获取页面文本内容
        text_content = await self._get_page_text(page)
        
        return [types.TextContent(
            type="text", 
            text=f"已导航到 {url}\n页面内容预览:\n\n{text_content[:200]}..."
        )]
    
    async def _get_page_text(self, page):
        """提取页面文本内容"""
        # 获取页面上的文本
        unique_texts = await page.evaluate('''() => {
            var elements = Array.from(document.querySelectorAll('*'));
            var uniqueTexts = new Set();

            for (var element of elements) {
                if (element.offsetWidth > 0 || element.offsetHeight > 0) {
                    var childrenCount = element.querySelectorAll('*').length;
                    if (childrenCount <= 3) {
                        var innerText = element.innerText ? element.innerText.trim() : '';
                        if (innerText && innerText.length <= 1000) {
                            uniqueTexts.add(innerText);
                        }
                        var value = element.getAttribute('value');
                        if (value) {
                            uniqueTexts.add(value);
                        }
                    }
                }
            }
            return Array.from(uniqueTexts);
        }''')
        
        return "\n".join(unique_texts)

@register_tool
class ScreenshotToolHandler(ToolHandler):
    """截图工具处理器"""
    
    @staticmethod
    def tool_name() -> str:
        return "screenshot"
    
    @staticmethod
    def tool_description() -> str:
        return "截取页面或特定元素的屏幕截图"
    
    @staticmethod
    def input_schema() -> dict:
        return {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "截图文件名(不含扩展名)"},
                "selector": {"type": "string", "description": "要截图的元素CSS选择器(可选)"}
            },
            "required": ["name"]
        }
    
    async def handle(self, name: str, arguments: Dict[str, Any] | None) -> List[Union[types.TextContent, types.ImageContent, types.EmbeddedResource]]:
        """截取屏幕截图"""
        global _sessions
        
        if not _sessions:
            return [types.TextContent(type="text", text="错误：没有活动的浏览器会话，请先导航到一个URL")]
        
        # 获取截图参数
        screenshot_name = arguments.get("name")
        selector = arguments.get("selector")
        
        # 获取最后一个会话的页面
        session_id = list(_sessions.keys())[-1]
        page = _sessions[session_id]["page"]
        
        # 临时文件路径
        file_path = f"{screenshot_name}.png"
        
        # 截图
        try:
            if selector:
                element = await page.locator(selector)
                await element.screenshot(path=file_path)
            else:
                await page.screenshot(path=file_path, full_page=True)
            
            # 读取图片并转为base64
            with open(file_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
            
            # 删除临时文件
            os.remove(file_path)
            
            # 返回图片数据
            return [types.ImageContent(type="image", data=encoded_string, mimeType="image/png")]
        except Exception as e:
            return [types.TextContent(type="text", text=f"截图失败: {str(e)}")]

@register_tool
class ClickToolHandler(ToolHandler):
    """点击元素工具处理器"""
    
    @staticmethod
    def tool_name() -> str:
        return "click"
    
    @staticmethod
    def tool_description() -> str:
        return "点击页面上的元素"
    
    @staticmethod
    def input_schema() -> dict:
        return {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "要点击的元素CSS选择器"}
            },
            "required": ["selector"]
        }
    
    @update_page_after_click
    async def handle(self, name: str, arguments: Dict[str, Any] | None) -> List[Union[types.TextContent, types.ImageContent, types.EmbeddedResource]]:
        """点击元素"""
        global _sessions
        
        if not _sessions:
            return [types.TextContent(type="text", text="错误：没有活动的浏览器会话，请先导航到一个URL")]
        
        # 获取会话
        session_id = list(_sessions.keys())[-1]
        page = _sessions[session_id]["page"]
        
        # 获取选择器
        selector = arguments.get("selector")
        
        try:
            # 点击元素
            await page.locator(selector).click()
            return [types.TextContent(type="text", text=f"已点击选择器 {selector} 的元素")]
        except Exception as e:
            return [types.TextContent(type="text", text=f"点击失败: {str(e)}")]

@register_tool
class FillToolHandler(ToolHandler):
    """填充表单工具处理器"""
    
    @staticmethod
    def tool_name() -> str:
        return "fill"
    
    @staticmethod
    def tool_description() -> str:
        return "填充页面上的输入字段"
    
    @staticmethod
    def input_schema() -> dict:
        return {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "输入字段的CSS选择器"},
                "value": {"type": "string", "description": "要填入的值"}
            },
            "required": ["selector", "value"]
        }
    
    async def handle(self, name: str, arguments: Dict[str, Any] | None) -> List[Union[types.TextContent, types.ImageContent, types.EmbeddedResource]]:
        """填充输入字段"""
        global _sessions
        
        if not _sessions:
            return [types.TextContent(type="text", text="错误：没有活动的浏览器会话，请先导航到一个URL")]
        
        # 获取会话
        session_id = list(_sessions.keys())[-1]
        page = _sessions[session_id]["page"]
        
        # 获取选择器和值
        selector = arguments.get("selector")
        value = arguments.get("value")
        
        try:
            # 填充字段
            await page.locator(selector).fill(value)
            return [types.TextContent(type="text", text=f"已填充选择器 {selector} 的字段，值为 {value}")]
        except Exception as e:
            return [types.TextContent(type="text", text=f"填充失败: {str(e)}")]

@register_tool
class EvaluateToolHandler(ToolHandler):
    """执行JavaScript工具处理器"""
    
    @staticmethod
    def tool_name() -> str:
        return "evaluate"
    
    @staticmethod
    def tool_description() -> str:
        return "在浏览器中执行JavaScript代码"
    
    @staticmethod
    def input_schema() -> dict:
        return {
            "type": "object",
            "properties": {
                "script": {"type": "string", "description": "要执行的JavaScript代码"}
            },
            "required": ["script"]
        }
    
    async def handle(self, name: str, arguments: Dict[str, Any] | None) -> List[Union[types.TextContent, types.ImageContent, types.EmbeddedResource]]:
        """执行JavaScript"""
        global _sessions
        
        if not _sessions:
            return [types.TextContent(type="text", text="错误：没有活动的浏览器会话，请先导航到一个URL")]
        
        # 获取会话
        session_id = list(_sessions.keys())[-1]
        page = _sessions[session_id]["page"]
        
        # 获取脚本
        script = arguments.get("script")
        
        try:
            # 执行脚本
            result = await page.evaluate(script)
            return [types.TextContent(type="text", text=f"已执行脚本，结果: {result}")]
        except Exception as e:
            return [types.TextContent(type="text", text=f"执行脚本失败: {str(e)}")]

@register_tool
class ClickTextToolHandler(ToolHandler):
    """按文本点击工具处理器"""
    
    @staticmethod
    def tool_name() -> str:
        return "click_text"
    
    @staticmethod
    def tool_description() -> str:
        return "根据文本内容点击页面上的元素"
    
    @staticmethod
    def input_schema() -> dict:
        return {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "要点击的元素的文本内容"}
            },
            "required": ["text"]
        }
    
    @update_page_after_click
    async def handle(self, name: str, arguments: Dict[str, Any] | None) -> List[Union[types.TextContent, types.ImageContent, types.EmbeddedResource]]:
        """根据文本点击元素"""
        global _sessions
        
        if not _sessions:
            return [types.TextContent(type="text", text="错误：没有活动的浏览器会话，请先导航到一个URL")]
        
        # 获取会话
        session_id = list(_sessions.keys())[-1]
        page = _sessions[session_id]["page"]
        
        # 获取文本
        text = arguments.get("text")
        
        try:
            # 点击含有指定文本的元素
            await page.locator(f"text={text}").nth(0).click()
            return [types.TextContent(type="text", text=f"已点击包含文本 '{text}' 的元素")]
        except Exception as e:
            return [types.TextContent(type="text", text=f"点击失败: {str(e)}")]

@register_tool
class GetTextContentToolHandler(ToolHandler):
    """获取页面文本工具处理器"""
    
    @staticmethod
    def tool_name() -> str:
        return "get_text_content"
    
    @staticmethod
    def tool_description() -> str:
        return "获取页面上所有可见元素的文本内容"
    
    @staticmethod
    def input_schema() -> dict:
        return {
            "type": "object",
            "properties": {}
        }
    
    async def handle(self, name: str, arguments: Dict[str, Any] | None) -> List[Union[types.TextContent, types.ImageContent, types.EmbeddedResource]]:
        """获取页面文本内容"""
        global _sessions
        
        if not _sessions:
            return [types.TextContent(type="text", text="错误：没有活动的浏览器会话，请先导航到一个URL")]
        
        # 获取会话
        session_id = list(_sessions.keys())[-1]
        page = _sessions[session_id]["page"]
        
        try:
            # 获取页面上的所有文本
            unique_texts = await page.evaluate('''() => {
                var elements = Array.from(document.querySelectorAll('*'));
                var uniqueTexts = new Set();

                for (var element of elements) {
                    if (element.offsetWidth > 0 || element.offsetHeight > 0) {
                        var childrenCount = element.querySelectorAll('*').length;
                        if (childrenCount <= 3) {
                            var innerText = element.innerText ? element.innerText.trim() : '';
                            if (innerText && innerText.length <= 1000) {
                                uniqueTexts.add(innerText);
                            }
                            var value = element.getAttribute('value');
                            if (value) {
                                uniqueTexts.add(value);
                            }
                        }
                    }
                }
                return Array.from(uniqueTexts);
            }''')
            
            return [types.TextContent(type="text", text=f"页面上的文本内容: {unique_texts}")]
        except Exception as e:
            return [types.TextContent(type="text", text=f"获取文本失败: {str(e)}")]

@register_tool
class GetHtmlContentToolHandler(ToolHandler):
    """获取HTML内容工具处理器"""
    
    @staticmethod
    def tool_name() -> str:
        return "get_html_content"
    
    @staticmethod
    def tool_description() -> str:
        return "获取指定元素的HTML内容"
    
    @staticmethod
    def input_schema() -> dict:
        return {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "元素的CSS选择器"}
            },
            "required": ["selector"]
        }
    
    async def handle(self, name: str, arguments: Dict[str, Any] | None) -> List[Union[types.TextContent, types.ImageContent, types.EmbeddedResource]]:
        """获取HTML内容"""
        global _sessions
        
        if not _sessions:
            return [types.TextContent(type="text", text="错误：没有活动的浏览器会话，请先导航到一个URL")]
        
        # 获取会话
        session_id = list(_sessions.keys())[-1]
        page = _sessions[session_id]["page"]
        
        # 获取选择器
        selector = arguments.get("selector")
        
        try:
            # 获取HTML内容
            html_content = await page.locator(selector).inner_html()
            return [types.TextContent(type="text", text=f"选择器 {selector} 元素的HTML内容: {html_content}")]
        except Exception as e:
            return [types.TextContent(type="text", text=f"获取HTML内容失败: {str(e)}")] 