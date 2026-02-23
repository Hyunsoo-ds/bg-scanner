import json
from typing import List, Dict, Any
from .base import BaseTool


class KatanaScanner(BaseTool):
    """
    Katana 크롤러 래퍼.
    JavaScript 렌더링 지원, 깊이 탐색.
    """

    async def run(self, target: str, depth: int = 3, **kwargs) -> List[Dict[str, Any]]:
        """
        Args:
            target: 크롤링할 URL (예: https://example.com)
            depth:  크롤링 깊이 (기본 3)
        Returns:
            [{"url": ..., "status_code": ..., "content_type": ..., "discovered_by": "katana"}]
        """
        cmd = [
            "katana",
            "-u", target,
            "-d", str(depth),
            "-silent",
            "-jc",          # JavaScript 크롤링 활성화
            "-jsonl",       # JSON Lines 출력
            "-timeout", "10",
        ]

        try:
            output = await self.run_command(cmd)
            return self._parse(output)
        except Exception as e:
            print(f"[Katana] Failed for {target}: {e}")
            return []

    def _parse(self, output: str) -> List[Dict[str, Any]]:
        results = []
        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                url = data.get("request", {}).get("endpoint") or data.get("url") or ""
                if not url:
                    continue
                status_code = data.get("response", {}).get("status_code") or data.get("status_code")
                content_type = data.get("response", {}).get("headers", {}).get("content_type") or data.get("content_type")
                results.append({
                    "url": url,
                    "status_code": int(status_code) if status_code else None,
                    "content_type": content_type,
                    "content_length": None,
                    "discovered_by": "katana",
                })
            except (json.JSONDecodeError, ValueError):
                # 일부 버전은 plain URL만 출력하기도 함
                if line.startswith("http"):
                    results.append({
                        "url": line,
                        "status_code": None,
                        "content_type": None,
                        "content_length": None,
                        "discovered_by": "katana",
                    })
        return results
