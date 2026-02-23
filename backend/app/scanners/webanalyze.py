import json
import asyncio
import os
from typing import List, Dict, Any
from app.scanners.base import BaseTool

TECH_FILE = "/app/technologies.json"

class WebanalyzeScanner(BaseTool):
    def __init__(self, target_url: str):
        super().__init__()
        self.target_url = target_url

    async def _ensure_tech_file(self):
        """Download technologies.json if not present."""
        if not os.path.exists(TECH_FILE):
            print("technologies.json not found, downloading...")
            try:
                await self.run_command(["webanalyze", "-update"])
            except Exception as e:
                print(f"Failed to update technologies.json: {e}")

    async def _run_webanalyze(self, command):
        """Run webanalyze and capture stdout regardless of exit code."""
        import asyncio
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        # webanalyze exits with code 1 even when it finds results
        # so we always return stdout
        return stdout.decode(), stderr.decode()

    async def run(self, target: str = None, **kwargs) -> List[Dict[str, Any]]:
        """
        Runs webanalyze against the target URL.
        target_url should be a full URL (http://... or https://...)
        """
        url = target or self.target_url
        
        await self._ensure_tech_file()
        
        # webanalyze -host <url> -crawl 1 -output json -apps <path>
        command = [
            "webanalyze",
            "-host", url,
            "-crawl", "1",
            "-output", "json",
            "-apps", TECH_FILE,
        ]
        
        try:
            stdout, stderr = await self._run_webanalyze(command)
        except Exception as e:
            print(f"Webanalyze Error: {e}")
            return []
        
        if not stdout or not stdout.strip():
            if stderr:
                print(f"Webanalyze stderr: {stderr[:200]}")
            return []

        try:
            # webanalyze outputs one JSON object per line (one per URL crawled):
            # {"hostname": "...", "matches": [{"app_name": "...", "categories": [...], "version": "..."}, ...]}
            # {"hostname": "...", "matches": [...]}
            all_matches = []
            for line in stdout.strip().splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    all_matches.extend(data.get("matches", []))
                except json.JSONDecodeError:
                    continue
            
            # Normalize categories to list of strings and deduplicate by app_name
            seen = set()
            normalized = []
            for match in all_matches:
                app_name = match.get("app_name", "Unknown")
                if app_name in seen:
                    continue
                seen.add(app_name)
                
                cats = match.get("categories", [])
                cat_names = []
                for c in cats:
                    if isinstance(c, dict):
                        cat_names.append(c.get("name", ""))
                    elif isinstance(c, str):
                        cat_names.append(c)
                normalized.append({
                    "app_name": app_name,
                    "version": match.get("version") or None,
                    "categories": [n for n in cat_names if n],
                })
            print(f"Webanalyze found {len(normalized)} technologies")
            return normalized
        except Exception as e:
            print(f"Failed to parse webanalyze output: {e} | stdout: {stdout[:200]}")
            return []

