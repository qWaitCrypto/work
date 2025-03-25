"""
天气查询工具示例
"""

import mcp.types as types
from typing import List, Union, Dict, Any
import httpx
import json
import re
from datetime import datetime
from core.registry import register_tool, ToolHandler, registered_tools, tool_handlers


# 常量定义
NWS_API_BASE = "https://api.weather.gov"

@register_tool
class WeatherForecastToolHandler(ToolHandler):
    """天气预报工具处理器"""
    
    @staticmethod
    def tool_name() -> str:
        return "get_forecast"
    
    @staticmethod
    def tool_description() -> str:
        return "获取指定位置的天气预报"
    
    @staticmethod
    def input_schema() -> dict:
        return {
            "type": "object",
            "properties": {
                "latitude": {"type": "number", "description": "纬度"},
                "longitude": {"type": "number", "description": "经度"},
                "days": {"type": "number", "description": "预报天数，默认为3天"}
            },
            "required": ["latitude", "longitude"]
        }
    
    async def handle(self, name: str, arguments: Dict[str, Any] | None) -> List[Union[types.TextContent, types.ImageContent, types.EmbeddedResource]]:
        """获取天气预报"""
        if not arguments or "latitude" not in arguments or "longitude" not in arguments:
            return [types.TextContent(type="text", text="错误：缺少latitude或longitude参数")]
        
        try:
            latitude = float(arguments.get("latitude"))
            longitude = float(arguments.get("longitude"))
            days = int(arguments.get("days", 3))
            
            # 获取天气预报
            forecast = await self._get_forecast(latitude, longitude, days)
            
            # 返回结果
            return [types.TextContent(type="text", text=forecast)]
        
        except ValueError:
            return [types.TextContent(type="text", text="错误：latitude和longitude必须是数字")]
        except Exception as e:
            return [types.TextContent(type="text", text=f"获取天气预报时发生错误: {str(e)}")]
    
    async def _make_api_request(self, endpoint: str) -> Dict:
        """发送API请求并返回结果"""
        headers = {
            "User-Agent": "MCP Weather Tool/1.0",
            "Accept": "application/geo+json"
        }
        
        url = f"{NWS_API_BASE}{endpoint}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
    
    async def _get_forecast(self, latitude: float, longitude: float, days: int = 3) -> str:
        """获取指定位置的天气预报"""
        # 首先获取当前位置的气象站点
        points_endpoint = f"/points/{latitude:.4f},{longitude:.4f}"
        points_data = await self._make_api_request(points_endpoint)
        
        # 从响应中获取预报URL
        forecast_url = points_data.get("properties", {}).get("forecast")
        if not forecast_url:
            return "无法获取预报URL，请检查经纬度是否正确"
        
        # 获取具体预报数据
        forecast_endpoint = forecast_url.replace(NWS_API_BASE, "")
        forecast_data = await self._make_api_request(forecast_endpoint)
        
        # 提取预报信息
        periods = forecast_data.get("properties", {}).get("periods", [])
        
        # 限制预报天数
        if days > 0:
            periods = periods[:days*2]  # 每天有白天和夜晚两个预报
        
        # 格式化预报信息
        if not periods:
            return "没有找到任何预报信息"
        
        location = points_data.get("properties", {}).get("relativeLocation", {}).get("properties", {})
        city = location.get("city", "未知城市")
        state = location.get("state", "未知州")
        
        # 构建预报字符串
        forecast_str = f"📍 {city}, {state} (坐标: {latitude:.4f}, {longitude:.4f}) 天气预报:\n\n"
        
        for period in periods:
            name = period.get("name", "未知时段")
            temperature = period.get("temperature", "未知")
            unit = period.get("temperatureUnit", "F")
            
            # 如果是华氏温度，转换为摄氏度
            if unit == "F":
                celsius = (temperature - 32) * 5 / 9
                temp_display = f"{temperature}°F ({celsius:.1f}°C)"
            else:
                temp_display = f"{temperature}°{unit}"
                
            wind_speed = period.get("windSpeed", "未知")
            wind_direction = period.get("windDirection", "未知")
            detailed_forecast = period.get("detailedForecast", "无详细预报")
            
            forecast_str += f"⏰ {name}:\n"
            forecast_str += f"🌡️ 温度: {temp_display}\n"
            forecast_str += f"💨 风速/风向: {wind_speed} {wind_direction}\n"
            forecast_str += f"📝 详情: {detailed_forecast}\n\n"
        
        return forecast_str


@register_tool
class WeatherAlertsToolHandler(ToolHandler):
    """天气预警工具处理器"""
    
    @staticmethod
    def tool_name() -> str:
        return "get_alerts"
    
    @staticmethod
    def tool_description() -> str:
        return "获取指定美国州的天气预警信息"
    
    @staticmethod
    def input_schema() -> dict:
        return {
            "type": "object",
            "properties": {
                "state": {"type": "string", "description": "美国州代码，例如'CA'表示加利福尼亚州"},
                "limit": {"type": "integer", "description": "返回的预警数量限制，默认为5"}
            },
            "required": ["state"]
        }
    
    async def handle(self, name: str, arguments: Dict[str, Any] | None) -> List[Union[types.TextContent, types.ImageContent, types.EmbeddedResource]]:
        """获取天气预警"""
        if not arguments or "state" not in arguments:
            return [types.TextContent(type="text", text="错误：缺少state参数")]
        
        try:
            state = arguments.get("state").upper()
            limit = int(arguments.get("limit", 5))
            
            # 验证州代码格式
            if not re.match(r'^[A-Z]{2}$', state):
                return [types.TextContent(type="text", text="错误：state参数必须是两个字母的州代码，例如'CA'")]
            
            # 获取天气预警
            alerts = await self._get_alerts(state, limit)
            
            # 返回结果
            return [types.TextContent(type="text", text=alerts)]
        
        except Exception as e:
            return [types.TextContent(type="text", text=f"获取天气预警时发生错误: {str(e)}")]
    
    async def _make_api_request(self, endpoint: str) -> Dict:
        """发送API请求并返回结果"""
        headers = {
            "User-Agent": "MCP Weather Tool/1.0",
            "Accept": "application/geo+json"
        }
        
        url = f"{NWS_API_BASE}{endpoint}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
    
    def _format_alert(self, alert: Dict) -> str:
        """格式化预警信息"""
        properties = alert.get("properties", {})
        
        event = properties.get("event", "未知事件")
        headline = properties.get("headline", "无标题")
        description = properties.get("description", "无描述")
        instruction = properties.get("instruction", "无相关指导")
        severity = properties.get("severity", "未知")
        
        # 解析开始和结束时间
        effective = properties.get("effective")
        expires = properties.get("expires")
        
        try:
            if effective:
                effective_dt = datetime.fromisoformat(effective.replace("Z", "+00:00"))
                effective_str = effective_dt.strftime("%Y-%m-%d %H:%M:%S")
            else:
                effective_str = "未知"
                
            if expires:
                expires_dt = datetime.fromisoformat(expires.replace("Z", "+00:00"))
                expires_str = expires_dt.strftime("%Y-%m-%d %H:%M:%S")
            else:
                expires_str = "未知"
        except Exception:
            effective_str = effective or "未知"
            expires_str = expires or "未知"
        
        # 截断长文本
        if len(description) > 500:
            description = description[:500] + "..."
        
        if len(instruction) > 300:
            instruction = instruction[:300] + "..."
        
        # 返回格式化的预警信息
        result = f"⚠️ {event} ({severity})\n"
        result += f"📰 {headline}\n"
        result += f"⏱️ 生效时间: {effective_str}\n"
        result += f"⌛ 过期时间: {expires_str}\n"
        result += f"📝 描述:\n{description}\n"
        
        if instruction and instruction != "无相关指导":
            result += f"🔔 指导建议:\n{instruction}\n"
            
        return result
    
    async def _get_alerts(self, state: str, limit: int = 5) -> str:
        """获取指定州的天气预警"""
        # 构建预警接口URL
        alerts_endpoint = f"/alerts/active/area/{state}"
        
        try:
            # 获取预警数据
            alerts_data = await self._make_api_request(alerts_endpoint)
            
            # 提取预警信息
            features = alerts_data.get("features", [])
            
            if not features:
                return f"🌈 好消息！{state}州目前没有活跃的天气预警。"
            
            # 限制返回数量
            if limit > 0:
                features = features[:limit]
            
            # 格式化预警信息
            alerts_str = f"⚠️ {state}州活跃天气预警 ({len(features)}个):\n\n"
            
            for i, feature in enumerate(features):
                alerts_str += f"--- 预警 {i+1} ---\n"
                alerts_str += self._format_alert(feature)
                alerts_str += "\n"
                
            if len(features) == limit and alerts_data.get("features", []) > limit:
                alerts_str += f"\n(仅显示前{limit}个预警，实际共有{len(alerts_data.get('features', []))}个活跃预警)"
                
            return alerts_str
            
        except Exception as e:
            return f"获取{state}州预警时发生错误: {str(e)}" 