from typing import List, Dict, Any
from .base import BaseTool
import json
import os

class Nuclei(BaseTool):
    async def run(self, target: str, **kwargs) -> List[Dict[str, Any]]:
        """
        Run Nuclei scan on a target (URL or Host).
        kwargs can contain:
        - templates: list of templates to run (optional)
        - tags: list of tags to run (optional)
        """
        
        # Ensure target is valid
        if not target:
            return []
            
        # Basic command: nuclei -u <target> -j -silent
        cmd = ["nuclei", "-u", target, "-j", "-silent"]

        # Add any additional flags if needed, e.g. for templates
        # cmd.extend(["-t", "cves", "-t", "vulnerabilities"]) # Example defaults?
        # For now, let's stick to default scans or maybe mild ones to avoid taking forever
        # Or maybe just criticals/highs? 
        # For now, let's just run default nuclei (which might be heavy).
        # Optimization: maybe limit to critical, high, medium?
        # cmd.extend(["-s", "critical,high,medium,low"])
        
        try:
            output = await self.run_command(cmd)
            results = []
            for line in output.splitlines():
                if line.strip():
                    try:
                        data = json.loads(line)
                        results.append({
                            "name": data.get("info", {}).get("name", "Unknown"),
                            "severity": data.get("info", {}).get("severity", "info"),
                            "description": data.get("info", {}).get("description"),
                            "matcher_name": data.get("matcher-name"),
                            "extracted_results": json.dumps(data.get("extracted-results", [])),
                            "raw": data # Keep raw just in case
                        })
                    except Exception as e:
                        print(f"Error parsing nuclei output line: {e}")
                        continue
            return results
        except Exception as e:
            print(f"Nuclei scan failed for {target}: {e}")
            return []
