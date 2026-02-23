import json
import asyncio
from typing import List, Dict, Any
from .base import BaseTool


class DirsearchScanner(BaseTool):
    """
    dirsearch 디렉터리 브루트포스 래퍼.
    python3 /opt/dirsearch/dirsearch.py -u <url> --format=json -q 실행.
    """

    async def run(self, target: str, extensions: str = "php,html,js,json,txt,xml", **kwargs) -> List[Dict[str, Any]]:
        """
        Args:
            target: 스캔할 URL (예: https://example.com)
            extensions: 검색할 파일 확장자 (콤마 구분)
        Returns:
            [{"url": ..., "status_code": ..., "content_type": ..., "content_length": ..., "discovered_by": "dirsearch"}]
        """
        import tempfile
        import os

        # dirsearch는 JSON 출력을 파일로 저장하는 방식이 안정적
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp_path = tmp.name

        cmd = [
            "python3", "/opt/dirsearch/dirsearch.py",
            "-u", target,
            "-e", extensions,
            "--format=json",
            "-o", tmp_path,
            "--quiet",
            "--no-color",
            "--timeout=10",
            "--max-time=120",
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.wait_for(process.communicate(), timeout=150)

            # JSON 파일 파싱
            if os.path.exists(tmp_path):
                with open(tmp_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                return self._parse_json(content, target)
            return []
        except asyncio.TimeoutError:
            print(f"[Dirsearch] Timeout for {target}")
            return []
        except Exception as e:
            print(f"[Dirsearch] Failed for {target}: {e}")
            return []
        finally:
            try:
                import os as _os
                if _os.path.exists(tmp_path):
                    _os.unlink(tmp_path)
            except Exception:
                pass

    def _parse_json(self, content: str, base_url: str) -> List[Dict[str, Any]]:
        """
        dirsearch JSON 출력 파싱.
        형식: {"results": [{"url": ..., "status": ..., "content-length": ..., "content-type": ...}]}
        """
        results = []
        if not content.strip():
            return results
        try:
            data = json.loads(content)
            # dirsearch JSON 구조: {"results": {"https://...": [{"path": ..., "status": ..., ...}]}}
            raw_results = data.get("results", {})
            if isinstance(raw_results, dict):
                for url_key, entries in raw_results.items():
                    if not isinstance(entries, list):
                        continue
                    for entry in entries:
                        path = entry.get("path", "")
                        status = entry.get("status")
                        length = entry.get("content-length") or entry.get("content_length")
                        ctype = entry.get("content-type") or entry.get("content_type")
                        full_url = entry.get("url") or (url_key.rstrip("/") + "/" + path.lstrip("/"))
                        results.append({
                            "url": full_url,
                            "status_code": int(status) if status else None,
                            "content_type": ctype,
                            "content_length": int(length) if length else None,
                            "discovered_by": "dirsearch",
                        })
            elif isinstance(raw_results, list):
                for entry in raw_results:
                    url = entry.get("url", "")
                    status = entry.get("status")
                    length = entry.get("content-length") or entry.get("content_length")
                    ctype = entry.get("content-type") or entry.get("content_type")
                    if url:
                        results.append({
                            "url": url,
                            "status_code": int(status) if status else None,
                            "content_type": ctype,
                            "content_length": int(length) if length else None,
                            "discovered_by": "dirsearch",
                        })
        except (json.JSONDecodeError, ValueError) as e:
            print(f"[Dirsearch] JSON parse error: {e}")
        return results
