#!/usr/bin/env python3
"""入口：python3 run.py（默认 0.0.0.0:8081，可用 PORT 环境变量改）"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.app import main

if __name__ == "__main__":
    main()
