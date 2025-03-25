"""
动态网页内容获取工具示例
"""

import mcp.types as types
from typing import List, Union, Dict, Any
import re
import base64
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from mcp_.core.registry import register_tool, ToolHandler, registered_tools, tool_handlers


@register_tool
class DynamicWebpageToolHandler(ToolHandler):
    """动态网页内容获取工具处理器"""
    
    @staticmethod
    def tool_name() -> str:
        return "get_dynamic_webpage"
    
    @staticmethod
    def tool_description() -> str:
        return "使用无头浏览器获取动态网页内容"
    
    @staticmethod
    def input_schema() -> dict:
        return {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "要获取内容的网页URL"},
                "wait_time": {"type": "integer", "description": "等待页面加载的时间（毫秒），默认为3000"},
                "wait_for_selector": {"type": "string", "description": "等待特定元素加载的选择器"},
                "include_images": {"type": "boolean", "description": "是否包含图片，默认为False"}
            },
            "required": ["url"]
        }
    
    async def handle(self, name: str, arguments: Dict[str, Any] | None) -> List[Union[types.TextContent, types.ImageContent, types.EmbeddedResource]]:
        """获取动态网页内容"""
        if not arguments or "url" not in arguments:
            return [types.TextContent(type="text", text="错误：缺少url参数")]
        
        url = arguments.get("url")
        wait_time = arguments.get("wait_time", 3000)
        wait_for_selector = arguments.get("wait_for_selector")
        include_images = arguments.get("include_images", False)
        
        # 获取网页内容
        content_result = await self._get_dynamic_webpage(url, wait_time, wait_for_selector, include_images)
        
        # 如果是错误信息，直接返回文本
        if isinstance(content_result, str):
            return [types.TextContent(type="text", text=content_result)]
        
        # 返回结果列表
        return content_result
    
    async def _get_dynamic_webpage(self, url: str, wait_time: int = 3000, wait_for_selector: str = None, include_images: bool = False) -> Union[str, List[Union[types.TextContent, types.ImageContent, types.EmbeddedResource]]]:
        """使用Playwright获取动态网页内容"""
        try:
            result = []
            
            # 创建Playwright实例
            async with async_playwright() as p:
                # 启动浏览器
                browser = await p.chromium.launch(headless=True)
                
                # 创建新页面
                page = await browser.new_page()
                
                # 设置用户代理
                await page.set_extra_http_headers({
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                })
                
                # 导航到URL
                await page.goto(url, wait_until="domcontentloaded")
                
                # 等待指定时间
                if wait_time > 0:
                    await page.wait_for_timeout(wait_time)
                
                # 等待特定选择器
                if wait_for_selector:
                    try:
                        await page.wait_for_selector(wait_for_selector, timeout=10000)
                    except Exception:
                        result.append(types.TextContent(
                            type="text", 
                            text=f"警告：选择器 '{wait_for_selector}' 未在页面上找到。继续处理可用内容。"
                        ))
                
                # 获取页面内容
                html_content = await page.content()
                
                # 获取页面标题
                title = await page.title()
                result.append(types.TextContent(
                    type="text", 
                    text=f"页面标题: {title}\n\nURL: {url}\n\n"
                ))
                
                # 清理HTML内容
                cleaned_content = self._clean_html_content(html_content)
                result.append(types.TextContent(
                    type="text", 
                    text=cleaned_content
                ))
                
                # 如果需要包含图片
                if include_images:
                    # 获取所有图片元素
                    image_elements = await page.query_selector_all("img")
                    
                    # 限制最多处理10张图片
                    for i, img in enumerate(image_elements[:10]):
                        try:
                            # 获取图片URL
                            src = await img.get_attribute("src")
                            if not src:
                                continue
                                
                            # 获取图片alt文本
                            alt = await img.get_attribute("alt") or f"图片 {i+1}"
                            
                            # 如果是相对URL，转换为绝对URL
                            if src.startswith("/"):
                                # 解析基础URL
                                base_url = "/".join(url.split("/")[:3])  # http(s)://domain.com
                                src = f"{base_url}{src}"
                            
                            # 截取图片元素
                            screenshot_bytes = await img.screenshot()
                            if screenshot_bytes:
                                # 将图片编码为base64
                                img_base64 = base64.b64encode(screenshot_bytes).decode("utf-8")
                                
                                # 添加图片内容
                                result.append(types.ImageContent(
                                    type="image", 
                                    image=img_base64, 
                                    alt=alt
                                ))
                        except Exception as e:
                            result.append(types.TextContent(
                                type="text", 
                                text=f"处理图片时出错: {str(e)}"
                            ))
                
                # 关闭浏览器
                await browser.close()
                
                return result
        
        except Exception as e:
            return f"获取动态网页内容时发生错误: {str(e)}"
    
    def _clean_html_content(self, html: str) -> str:
        """清理HTML内容，提取有用的文本"""
        try:
            # 使用BeautifulSoup解析HTML
            soup = BeautifulSoup(html, "html.parser")
            
            # 移除script和style元素
            for script in soup(["script", "style", "head", "meta", "link", "noscript", "iframe"]):
                script.decompose()
            
            # 获取纯文本
            text = soup.get_text()
            
            # 清理文本
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            text = "\n".join(lines)
            
            # 移除多余的空格和换行
            text = re.sub(r"\n\s*\n", "\n\n", text)
            
            # 如果文本太长，截断
            if len(text) > 10000:
                text = text[:10000] + "...\n(内容已截断，超过10000个字符)"
            
            return text
        
        except Exception as e:
            return f"清理HTML内容时发生错误: {str(e)}"