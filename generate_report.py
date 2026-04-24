import sys
import os
sys.path.append('/home/ubuntu/xiaoban_agent')
from engines.xiaoshengchu_simulator import XiaoshengchuSimulator
from memory.memory_manager import MemoryManager

mm = MemoryManager('/home/ubuntu/xiaoban_agent/memory')
simulator = XiaoshengchuSimulator(mm)
report = simulator.generate_simulation_report()

with open('/home/ubuntu/xiaoban_agent/xiaoshengchu_ai_prediction.md', 'w', encoding='utf-8') as f:
    f.write(report)
print("Report generated successfully.")
