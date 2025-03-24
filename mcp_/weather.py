"""
FastMCP 天气服务模块

本模块使用美国国家气象服务(NWS)API提供天气信息工具。
它提供了获取美国地区天气预警和天气预报的功能。

模块提供两个主要工具：
1. get_alerts: 获取指定美国州的活动天气预警
2. get_forecast: 使用经纬度为特定位置提供天气预报

依赖项：
- httpx: 用于发送异步HTTP请求
- FastMCP: 用于将工具作为服务暴露
"""

from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP

# 使用名称"weather"初始化FastMCP服务器
mcp = FastMCP("weather")

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

# Add a dynamic greeting resource
@mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """Get a personalized greeting"""
    return f"Hello, {name}!"

if __name__ == "__main__":
    # 当脚本直接运行（而非导入）时执行此代码块
    # 初始化并运行服务器，使用stdio传输进行通信
    mcp.run(transport='stdio')