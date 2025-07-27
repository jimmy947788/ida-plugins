#!/usr/bin/env python3
"""
設定所有 submodule 忽略本地修改
"""

import subprocess
import re
from typing import List

def run_command(cmd: str) -> bool:
    """執行命令並返回是否成功"""
    try:
        result = subprocess.run(cmd.split(), capture_output=True, text=True)
        return result.returncode == 0
    except:
        return False

def get_submodule_paths() -> List[str]:
    """獲取所有 submodule 路徑"""
    try:
        result = subprocess.run(['git', 'submodule', 'status'], capture_output=True, text=True)
        if result.returncode != 0:
            return []
        
        paths = []
        for line in result.stdout.split('\n'):
            if line.strip():
                # 解析 git submodule status 輸出
                parts = line.strip().split()
                if len(parts) >= 2:
                    path = parts[1]
                    paths.append(path)
        
        return paths
    except:
        return []

def main():
    print("🔧 設定所有 submodule 忽略本地修改...")
    print("=" * 50)
    
    paths = get_submodule_paths()
    if not paths:
        print("❌ 沒有找到 submodule")
        return
    
    print(f"找到 {len(paths)} 個 submodule")
    print()
    
    success_count = 0
    
    for i, path in enumerate(paths):
        print(f"[{i+1}/{len(paths)}] 設定 {path}...", end=' ')
        
        # 設定忽略本地修改
        cmd = f"git config submodule.{path}.ignore all"
        if run_command(cmd):
            print("✅")
            success_count += 1
        else:
            print("❌")
    
    print()
    print(f"完成! 成功設定 {success_count}/{len(paths)} 個 submodule")
    
    if success_count > 0:
        print()
        print("📝 現在 git status 將不會顯示 submodule 的本地修改")
        print("如果要查看 submodule 修改，使用: git status --ignore-submodules=none")
        print("如果要重置某個 submodule 設定，使用: git config --unset submodule.<path>.ignore")

if __name__ == "__main__":
    main()
