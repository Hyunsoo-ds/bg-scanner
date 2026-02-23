from app.scanners.nuclei import Nuclei

target = "dev.sn0wball.cloud"

async def main():
    scanner = Nuclei()
    results = await scanner.run(target)
    
    print(results)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())