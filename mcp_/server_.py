# server.py
from mcp.server.fastmcp import FastMCP
from typing import Any
import httpx
from playwright.async_api import async_playwright
import asyncio
import re
from bs4 import BeautifulSoup
import html
import os
import chardet
import openai

# Create an MCP server
mcp = FastMCP("Demo")

# 初始化OpenAI客户端，指向本地模型服务
client = openai.OpenAI(
    base_url="http://0.0.0.0:30000/v1",
    api_key="not-needed"  # 本地服务不需要API key
)

# API交互常量
NWS_API_BASE = "https://api.weather.gov"  # 美国国家气象服务API的基础URL
USER_AGENT = "weather-app/1.0"  # API请求的用户代理标识符


async def make_nws_request(url: str) -> dict[str, Any] | None:
    """向NWS API发送请求并进行适当的错误处理。

    此函数处理HTTP请求细节，包括请求头和超时设置。

    参数:
        url: NWS API端点的完整URL

    返回:
        包含JSON响应数据的字典，如果请求失败则返回None
    """
    # 设置NWS API所需的请求头
    headers = {
        "User-Agent": USER_AGENT,  # NWS API要求提供用户代理
        "Accept": "application/geo+json"  # 指定预期的响应格式
    }

    # 创建异步HTTP客户端
    async with httpx.AsyncClient() as client:
        try:
            # 使用适当的超时设置发送GET请求
            response = await client.get(url, headers=headers, timeout=30.0)
            # 对4XX/5XX响应抛出异常
            response.raise_for_status()
            # 解析并返回JSON响应
            return response.json()
        except Exception:
            # 对任何异常（连接错误、超时、JSON解析错误等）返回None
            return None


def format_alert(feature: dict) -> str:
    """将预警特征格式化为可读字符串。

    从天气预警特征中提取并格式化相关信息。

    参数:
        feature: 包含来自NWS API的天气预警特征的字典

    返回:
        包含预警详情的格式化字符串
    """
    # 提取包含预警详情的properties对象
    props = feature["properties"]

    # 将预警信息格式化为可读的多行字符串
    # 使用.get()方法并提供默认值以处理缺失的属性
    return f"""
Event: {props.get('event', 'Unknown')}
Area: {props.get('areaDesc', 'Unknown')}
Severity: {props.get('severity', 'Unknown')}
Description: {props.get('description', 'No description available')}
Instructions: {props.get('instruction', 'No specific instructions provided')}
"""


@mcp.tool()
async def get_alerts(state: str) -> str:
    """获取美国州的天气预警。

    从NWS API获取指定美国州的所有活动天气预警。

    参数:
        state: 两字母美国州代码（例如CA, NY）

    返回:
        包含所有活动预警的格式化字符串，如果没有找到预警则返回相应消息
    """
    # 构建州预警端点的URL
    url = f"{NWS_API_BASE}/alerts/active/area/{state}"

    # 发送API请求
    data = await make_nws_request(url)

    # 检查请求是否失败或返回了意外数据
    if not data or "features" not in data:
        return "无法获取预警或未找到预警。"

    # 检查是否没有活动预警
    if not data["features"]:
        return "该州没有活动预警。"

    # 格式化每个预警特征并用分隔符连接它们
    alerts = [format_alert(feature) for feature in data["features"]]
    return "\n---\n".join(alerts)


@mcp.tool()
async def get_forecast(latitude: float, longitude: float) -> str:
    """获取位置的天气预报。

    使用坐标获取特定位置的天气预报。
    该过程涉及两个API调用：
    1. 获取坐标的预报网格端点
    2. 从该端点获取详细预报

    参数:
        latitude: 位置的纬度
        longitude: 位置的经度

    返回:
        包含未来几个时段预报的格式化字符串
    """
    # 步骤1：获取坐标的预报网格端点
    points_url = f"{NWS_API_BASE}/points/{latitude},{longitude}"
    points_data = await make_nws_request(points_url)

    # 检查第一个请求是否失败
    if not points_data:
        return "无法获取该位置的预报数据。"

    # 步骤2：从points响应中提取预报URL
    forecast_url = points_data["properties"]["forecast"]

    # 步骤3：从预报URL获取详细预报
    forecast_data = await make_nws_request(forecast_url)

    # 检查第二个请求是否失败
    if not forecast_data:
        return "无法获取详细预报。"

    # 步骤4：提取并格式化预报时段
    periods = forecast_data["properties"]["periods"]
    forecasts = []

    # 只显示接下来的5个时段以保持响应简洁
    for period in periods[:5]:
        forecast = f"""
{period['name']}:
Temperature: {period['temperature']}°{period['temperatureUnit']}
Wind: {period['windSpeed']} {period['windDirection']}
Forecast: {period['detailedForecast']}
"""
        forecasts.append(forecast)

    # 用分隔符连接所有预报时段
    return "\n---\n".join(forecasts)

# Add an addition tool
@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b


def clean_html_content(html_content: str) -> str:
    """清理HTML内容，提取有用的文本信息。
    
    参数:
        html_content: 原始HTML内容
        
    返回:
        清理后的文本内容
    """
    # 使用BeautifulSoup解析HTML
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 移除脚本和样式元素
    for script in soup(["script", "style", "meta", "link", "noscript"]):
        script.decompose()
    
    # 获取文本内容
    text = soup.get_text(separator='\n', strip=True)
    
    # 清理空白行和多余空格
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    text = '\n'.join(lines)
    
    # 清理HTML实体
    text = html.unescape(text)
    
    # 清理特殊字符和多余空格
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()

@mcp.tool()
async def get_dynamic_webpage(url: str) -> str:
    """获取动态加载的网页内容。

    使用 Playwright 访问指定的URL，等待页面加载完成并获取内容。
    支持JavaScript渲染的页面，可以获取动态加载的内容。

    参数:
        url: 要访问的网站URL（例如 https://example.com）

    返回:
        包含网页内容的字符串，如果访问失败则返回错误信息
    """
    try:
        async with async_playwright() as p:
            # 启动浏览器（使用 chromium）
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            )
            
            # 创建新页面
            page = await context.new_page()
            
            # 访问URL
            await page.goto(url, wait_until="networkidle")
            
            # 等待页面加载完成
            await page.wait_for_load_state("domcontentloaded")
            
            # 获取页面内容
            content = await page.content()
            
            # 提取文章内容（针对新华社网站）
            if "xinhuanet.com" in url:
                # 等待文章内容加载
                await page.wait_for_selector("article", timeout=10000)
                # 获取文章内容
                article = await page.query_selector("article")
                if article:
                    content = await article.inner_text()
            
            # 关闭浏览器
            await browser.close()
            
            # 清理并返回内容
            return clean_html_content(content)
            
    except Exception as e:
        return f"访问 {url} 时发生错误: {str(e)}"

@mcp.tool()
def read_file(file_path: str) -> str:
    """读取本地文件内容。

    读取指定路径的文件，自动检测文件编码，并返回文件内容。
    支持文本文件，包括但不限于：txt, md, py, js, html, css, json, xml等。

    参数:
        file_path: 要读取的文件路径（相对路径或绝对路径）

    返回:
        文件内容的字符串，如果读取失败则返回错误信息
    """
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
                content = content[:10000] + "\n... (文件内容已截断，完整文件大小: {} 字节)".format(file_size)

            return content

    except PermissionError:
        return f"错误：没有权限读取文件 '{file_path}'。"
    except Exception as e:
        return f"读取文件时发生错误: {str(e)}"

@mcp.tool()
def scan_path(path: str = ".", file_types: list[str] = None, recursive: bool = True, max_depth: int = 1) -> str:
    """扫描指定路径下的所有文件。

    递归扫描指定目录下的所有文件，支持按文件类型过滤，并可以控制扫描深度。

    参数:
        path: 要扫描的路径，默认为当前目录
        file_types: 要包含的文件类型列表，例如 ["txt", "py", "jpg"]。如果为None，则包含所有文件
        recursive: 是否递归扫描子目录
        max_depth: 递归扫描的最大深度，默认为1层

    返回:
        包含所有找到的文件信息的格式化字符串
    """
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

@mcp.tool()
async def analyze_image(image_url: str, task: str = "描述这张图片", detail_level: str = "normal") -> str:
    """分析图片内容。

    使用Qwen-VL模型分析图片内容，支持多种分析任务和详细程度。

    参数:
        image_url: 图片的URL地址或本地文件路径
        task: 分析任务类型，可选值：
            - "描述这张图片"：生成图片描述
            - "识别物体"：识别图片中的主要物体
            - "分析场景"：分析图片场景和环境
            - "提取文字"：提取图片中的文字（OCR）
            - "分析人物"：分析图片中的人物特征
            - "分析颜色"：分析图片的主要颜色
            - "分析构图"：分析图片的构图方式
        detail_level: 分析的详细程度，可选值：
            - "simple"：简单描述
            - "normal"：正常描述
            - "detailed"：详细描述

    返回:
        分析结果的字符串，如果分析失败则返回错误信息
    """
    try:
        # 验证任务类型
        valid_tasks = {
            "描述这张图片": "请详细描述这张图片的内容",
            "识别物体": "请识别并列出这张图片中的主要物体",
            "分析场景": "请分析这张图片的场景和环境",
            "提取文字": "请提取这张图片中的文字内容",
            "分析人物": "请分析这张图片中的人物特征",
            "分析颜色": "请分析这张图片的主要颜色",
            "分析构图": "请分析这张图片的构图方式"
        }

        if task not in valid_tasks:
            return f"错误：不支持的任务类型 '{task}'。\n支持的任务类型：{', '.join(valid_tasks.keys())}"

        # 验证详细程度
        valid_levels = {
            "simple": "请用简单的话",
            "normal": "请用正常详细程度",
            "detailed": "请用非常详细的方式"
        }

        if detail_level not in valid_levels:
            return f"错误：不支持的详细程度 '{detail_level}'。\n支持的详细程度：{', '.join(valid_levels.keys())}"

        # 构建提示词
        prompt = f"{valid_levels[detail_level]} {valid_tasks[task]}"

        # 构建消息
        messages = [
            {"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_url}}
            ]}
        ]

        # 调用Qwen-VL模型
        response = client.chat.completions.create(
            model="qwen-vl",
            messages=messages,
            temperature=0.1,
            max_tokens=1024
        )

        # 检查响应
        if not response or not response.choices:
            return "错误：模型返回结果为空"

        # 返回分析结果
        return response.choices[0].message.content

    except Exception as e:
        return f"分析图片时发生错误: {str(e)}"

def main():
    print("成功")
    mcp.run(transport='stdio')

if __name__ == "__main__":
    # 当脚本直接运行（而非导入）时执行此代码块
    # 初始化并运行服务器，使用stdio传输进行通信
    mcp.run(transport='stdio')