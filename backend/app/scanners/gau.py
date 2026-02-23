import asyncio
from typing import List, Dict, Any
from .base import BaseTool


class GauScanner(BaseTool):
    """
    GetAllUrls (gau) 래퍼.
    AlienVault OTX, Wayback Machine, Common Crawl 등에서 URL 수집.
    echo <domain> | gau 형태로 실행.
    """

    async def run(self, target: str, threads: int = 5, **kwargs) -> List[Dict[str, Any]]:
        """
        Args:
            target: 도메인 또는 URL
            threads: 병렬 스레드 수 (기본 5)
        Returns:
            [{"url": ..., "status_code": None, "content_type": None, "discovered_by": "gau"}]
        """
        domain = self._extract_domain(target)

        try:
            process = await asyncio.create_subprocess_exec(
                "gau",
                "--threads", str(threads),
                "--timeout", "60",
                domain,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=120,
            )
            output = stdout.decode()
            return self._parse(output)
        except asyncio.TimeoutError:
            print(f"[Gau] Timeout for {domain}")
            return []
        except Exception as e:
            print(f"[Gau] Failed for {domain}: {e}")
            return []

    def _extract_domain(self, target: str) -> str:
        """https://example.com/path → example.com"""
        domain = target
        for prefix in ("https://", "http://"):
            if domain.startswith(prefix):
                domain = domain[len(prefix):]
                break
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
                    "discovered_by": "gau",
                })
        return results
