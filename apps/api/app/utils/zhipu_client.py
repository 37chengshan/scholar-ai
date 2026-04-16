"""ZhipuAI LLM Client Wrapper.

统一封装 zhipuai SDK 的调用，提供异步接口和错误处理。

Usage:
    from app.utils.zhipu_client import ZhipuLLMClient
    
    client = ZhipuLLMClient()
    response = await client.chat_completion(
        messages=[...],
        tools=[...],
        max_tokens=2048
    )
"""

import json
from typing import Any, Dict, List, Optional
from zhipuai import ZhipuAI

from app.config import settings
from app.utils.logger import logger


class ZhipuLLMClient:
    """ZhipuAI LLM Client Wrapper.
    
    封装 zhipuai SDK 的异步调用，提供：
    - 统一的 API 调用接口
    - 错误处理和重试
    - 工具调用支持
    - 流式输出支持
    
    Attributes:
        client: ZhipuAI 客户端实例
        model: 默认模型名称
        max_tokens: 最大输出 token 数
        temperature: 温度参数
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ):
        """初始化 ZhipuAI 客户端。
        
        Args:
            api_key: API密钥（默认从 settings.ZHIPU_API_KEY）
            model: 模型名称（默认从 settings.LLM_MODEL）
            max_tokens: 最大输出 token（默认从 settings.LLM_MAX_TOKENS）
            temperature: 温度参数（默认从 settings.LLM_TEMPERATURE）
        """
        self.api_key = api_key or settings.ZHIPU_API_KEY
        self.model = self._parse_model_name(model or settings.LLM_MODEL)
        self.max_tokens = max_tokens or settings.LLM_MAX_TOKENS
        self.temperature = temperature or settings.LLM_TEMPERATURE
        
        if not self.api_key:
            raise ValueError("ZHIPU_API_KEY not configured")
        
        self.client = ZhipuAI(api_key=self.api_key)
        
        logger.info(
            "ZhipuAI client initialized",
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature
        )
    
    def _parse_model_name(self, model: str) -> str:
        """解析模型名称，移除 LiteLLM 格式前缀。
        
        Args:
            model: LiteLLM 格式的模型名（如 'zhipu/glm-4.5-air'）
            
        Returns:
            纯模型名（如 'glm-4.5-air'）
        """
        if '/' in model:
            return model.split('/')[-1]
        return model
    
    async def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = "auto",
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stream: bool = False,
        thinking: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """异步聊天补全 API 调用。
        
        Args:
            messages: 对话消息列表
            tools: 工具定义列表（可选）
            tool_choice: 工具选择策略（'auto', 'none', 或具体工具名）
            max_tokens: 最大输出 token（可选）
            temperature: 温度参数（可选）
            stream: 是否流式输出（默认 False）
            thinking: 思考模式参数（如 {'type': 'enabled'}）
            
        Returns:
            API 响应对象，包含 choices, usage 等字段
            
        Raises:
            Exception: API 调用失败
        """
        try:
            params = {
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens or self.max_tokens,
                "temperature": temperature or self.temperature,
                "stream": stream
            }
            
            if tools:
                params["tools"] = tools
                params["tool_choice"] = tool_choice
            
            if thinking:
                params["thinking"] = thinking
            
            logger.debug(
                "Calling ZhipuAI API",
                model=self.model,
                messages_count=len(messages),
                has_tools=bool(tools),
                stream=stream
            )
            
            response = self.client.chat.completions.create(**params)
            
            logger.debug(
                "ZhipuAI API response received",
                response_type=type(response).__name__
            )
            
            return response
            
        except Exception as e:
            logger.error(
                "ZhipuAI API call failed",
                error=str(e),
                model=self.model
            )
            raise
    
    async def simple_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> str:
        """简化的补全接口，用于简单文本生成。
        
        Args:
            prompt: 用户提示文本
            system_prompt: 系统提示文本（可选）
            max_tokens: 最大输出 token（可选）
            temperature: 温度参数（可选）
            
        Returns:
            生成的文本内容
            
        Raises:
            Exception: API 调用失败
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        response = await self.chat_completion(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        return response.choices[0].message.content
    
    def parse_tool_calls(self, response: Any) -> List[Dict[str, Any]]:
        """解析工具调用响应。
        
        Args:
            response: API 响应对象
            
        Returns:
            工具调用列表，每个元素包含：
                - name: 工具名称
                - parameters: 工具参数（已解析为 dict）
        """
        tool_calls = []
        
        message = response.choices[0].message
        
        if hasattr(message, 'tool_calls') and message.tool_calls:
            for tool_call in message.tool_calls:
                tool_calls.append({
                    "name": tool_call.function.name,
                    "parameters": json.loads(tool_call.function.arguments)
                })
        
        return tool_calls


llm_client: Optional[ZhipuLLMClient] = None


def get_llm_client() -> ZhipuLLMClient:
    """获取全局 LLM 客户端实例（单例模式）。
    
    Returns:
        ZhipuLLMClient 实例
    """
    global llm_client
    
    if llm_client is None:
        llm_client = ZhipuLLMClient()
    
    return llm_client