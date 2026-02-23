from typing import List, Dict, Any
import xml.etree.ElementTree as ET
from .base import BaseTool

class NmapScanner(BaseTool):
    async def run(self, target: str, **kwargs) -> List[Dict[str, Any]]:
        # nmap -sV -T4 -F <target> -oX -
        # -sV: Version detection
        # -T4: Aggressive timing template
        # -F: Fast mode (scan fewer ports than the default scan)
        # -oX -: Output in XML format to stdout
        
        # 권한 문제로 -sS (SYN scan) 등은 실패할 수 있으므로, 비특권 모드(connect scan)가 기본일 수 있음.
        # Docker 컨테이너가 root 권한이면 -sS 가능.
        
        cmd = ["nmap", "-sV", "-T4", "-F", target, "-oX", "-"]
        
        try:
            output = await self.run_command(cmd)
            return self.parse_xml(output)
        except Exception as e:
            print(f"Nmap scan failed for {target}: {e}")
            return []

    def parse_xml(self, xml_data: str) -> List[Dict[str, Any]]:
        results = []
        try:
            root = ET.fromstring(xml_data)
            
            for host in root.findall("host"):
                ports = host.find("ports")
                if ports is None:
                    continue
                
                for port in ports.findall("port"):
                    state_el = port.find("state")
                    if state_el is None or state_el.get("state") != "open":
                        continue
                    
                    port_id = port.get("portid")
                    protocol = port.get("protocol")
                    
                    service_el = port.find("service")
                    service_name = service_el.get("name") if service_el is not None else "unknown"
                    version = service_el.get("version") if service_el is not None else None
                    product = service_el.get("product") if service_el is not None else None
                    
                    full_version = f"{product} {version}".strip() if product or version else None
                    
                    results.append({
                        "port_number": int(port_id),
                        "protocol": protocol,
                        "service_name": service_name,
                        "state": "open",
                        "version": full_version
                    })
        except ET.ParseError as e:
            print(f"Failed to parse Nmap XML: {e}")
        
        return results
