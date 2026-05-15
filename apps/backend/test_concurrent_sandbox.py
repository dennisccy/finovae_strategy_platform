import asyncio
import sys
from concurrent.futures import ThreadPoolExecutor
from strategy.sandbox import SandboxExecutor

code = """
class Strategy:
    def setup(self): pass
    def signal(self, df, bar): return 0
"""

def compile_it():
    sandbox = SandboxExecutor()
    try:
        instance = sandbox.get_strategy_instance(code)
        return True
    except Exception as e:
        print(f"FAILED: {e}")
        return False

async def main():
    with ThreadPoolExecutor(max_workers=10) as executor:
        futs = [executor.submit(compile_it) for _ in range(20)]
        results = [f.result() for f in futs]
        
    print(f"Successes: {sum(results)} / 20")

if __name__ == "__main__":
    asyncio.run(main())
