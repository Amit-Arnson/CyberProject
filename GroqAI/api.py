import typing

import aiohttp
from aiohttp import ClientTimeout


class Response:
    def __init__(self, original: dict[typing.Any], content: str):
        self.original = original
        self.content = content


class Model:
    def __init__(self, key: str, model: str):
        self.key = key
        self.model = model

        self._client_timeout = ClientTimeout(60)

    async def _get(self, url: str, headers: dict[str, str], **kwargs) -> dict:
        """returns the json of the response"""
        async with aiohttp.ClientSession(timeout=self._client_timeout) as session:
            async with session.get(
                    url=url,
                    headers=headers,
                    **kwargs,
            ) as response:
                return await response.json()

    async def _post(self, url: str, headers: dict[str, str], **kwargs) -> dict:
        """returns the json of the response"""
        async with aiohttp.ClientSession(timeout=self._client_timeout) as session:
            async with session.post(
                    url=url,
                    headers=headers,
                    **kwargs,
            ) as response:
                return await response.json()

    async def prompt(self, messages: str | list[dict[str, str]], max_completion_tokens: int = None, temperature: float = 1.0) -> Response:
        url = "https://api.groq.com/openai/v1/chat/completions"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.key}"
        }

        if isinstance(messages, str):
            messages = [
                {
                    "role": "user",
                    "content": f"{messages}"
                }
            ]

        json_data = {
            "model": f"{self.model}",
            "messages": messages,
            "max_completion_tokens": max_completion_tokens,
            "temperature": temperature
        }

        response = await self._post(url=url, headers=headers, json=json_data)

        content = response.get("choices", [{}])[0].get("message", {}).get("content")
        # -> ["choices"][0]["message"]["content"]

        return Response(
            original=response,
            content=content,
        )
