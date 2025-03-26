# tools包初始化文件
# 此文件使tools目录成为Python包 

# 确保core目录在导入路径中
import sys
import os
from pathlib import Path

# 添加项目根目录到系统路径
parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
    print(f"已添加路径: {parent_dir}") 