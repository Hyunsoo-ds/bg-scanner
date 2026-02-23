from typing import List, Dict, Any
from .base import BaseTool

class Subfinder(BaseTool):
    async def run(self, target: str, **kwargs) -> List[Dict[str, Any]]:
        # subfinder -d target.com -silent -json
        cmd = ["subfinder", "-d", target, "-silent", "-json"]
        
        try:
            output = await self.run_command(cmd)
            results = []
            for line in output.splitlines():
                if line.strip():
                    # JSON 파싱 대신 간단히 호스트만 추출 (JSON 옵션 줬지만, 라인별 처리)
                    # 실제로는 json.loads(line) 해서 더 많은정보 가져올 수 있음
                    import json
                    try:
                        data = json.loads(line)
                        results.append({
                            "hostname": data.get("host"),
                            "ip_address": data.get("ip"),
                            "source": "subfinder"
                        })
                    except:
                        continue
            return results
        except Exception as e:
            print(f"Subfinder failed: {e}")
            return []
