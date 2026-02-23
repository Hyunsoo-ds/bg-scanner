import asyncio
from typing import List, Dict, Any
from .base import BaseTool


class WaybackurlsScanner(BaseTool):
    """
    Wayback Machine URL 수집 래퍼.
    echo <domain> | waybackurls 형태로 실행.
    """

    async def run(self, target: str, **kwargs) -> List[Dict[str, Any]]:
        """
        Args:
            target: 도메인 또는 URL (프로토콜 제거 후 도메인만 사용)
        Returns:
            [{"url": ..., "status_code": None, "content_type": None, "discovered_by": "waybackurls"}]
        """
        # URL에서 도메인만 추출
        domain = self._extract_domain(target)

        try:
            # echo <domain> | waybackurls
            process = await asyncio.create_subprocess_exec(
                "waybackurls",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=domain.encode()),
                timeout=60,
            )
            output = stdout.decode()
            return self._parse(output)
        except asyncio.TimeoutError:
            print(f"[Waybackurls] Timeout for {domain}")
            return []
        except Exception as e:
            print(f"[Waybackurls] Failed for {domain}: {e}")
            return []

    def _extract_domain(self, target: str) -> str:
        """https://example.com/path → example.com"""
        domain = target
        for prefix in ("https://", "http://"):
            if domain.startswith(prefix):
                domain = domain[len(prefix):]
                break
        # 경로 제거
        domain = domain.split("/")[0]
        return domain

    def _parse(self, output: str) -> List[Dict[str, Any]]:
        results = []
        for line in output.splitlines():
            url = line.strip()
            if url and url.startswith("http"):
                results.append({
                    "url": url,
                    "status_code": None,
                    "content_type": None,
                    "content_length": None,
                    "discovered_by": "waybackurls",
                })
        return results
