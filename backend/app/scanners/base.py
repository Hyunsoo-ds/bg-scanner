import subprocess
import asyncio
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseTool(ABC):
    def __init__(self):
        pass

    async def run_command(self, cmd: List[str]) -> str:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise Exception(f"Command failed: {stderr.decode()}")
            
        return stdout.decode()

    @abstractmethod
    async def run(self, target: str, **kwargs) -> List[Dict[str, Any]]:
        pass
