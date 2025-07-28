#!/usr/bin/env python3
"""
更新 .gitmodules 中的所有 submodule
支援批量更新、失敗重試、和詳細進度顯示
"""
import subprocess
import os
import sys
import time
import json
from datetime import datetime
from typing import List, Dict

def run_command(cmd: str, cwd: str = None, timeout: int = 300) -> Dict:
    """執行命令並返回結果"""
    try:
        result = subprocess.run(
            cmd.split(),
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        return {
            'success': result.returncode == 0,
            'returncode': result.returncode,
            'stdout': result.stdout.strip(),
            'stderr': result.stderr.strip(),
            'command': cmd
        }
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'returncode': -1,
            'stdout': '',
            'stderr': f'命令超時 ({timeout}秒)',
            'command': cmd
        }
    except Exception as e:
        return {
            'success': False,
            'returncode': -1,
            'stdout': '',
            'stderr': str(e),
            'command': cmd
        }

def parse_gitmodules() -> List[Dict]:
    """從 .gitmodules 文件讀取子模組配置"""
    if not os.path.exists('.gitmodules'):
        print("❌ 找不到 .gitmodules 文件")
        return []
        
    result = run_command("git config -f .gitmodules --list")
    
    if not result['success']:
        print(f"❌ 無法讀取 .gitmodules: {result['stderr']}")
        return []
        
    submodules = []
    current_path = None
    current_url = None
    
    for line in result['stdout'].split('\n'):
        if line.startswith('submodule.'):
            parts = line.split('=', 1)
            if len(parts) == 2:
                key = parts[0].strip()
                value = parts[1].strip()
                
                if key.endswith('.path'):
                    current_path = value
                elif key.endswith('.url'):
                    current_url = value
                    
                # 當有了 path 和 url 就可以添加
                if current_path and current_url:
                    submodules.append({'path': current_path, 'url': current_url})
                    current_path = None
                    current_url = None
    
    return submodules

def get_submodule_status() -> List[Dict]:
    """獲取所有 submodule 的狀態"""
    print("📋 獲取 submodule 狀態...")
    
    # 從 .gitmodules 獲取子模組列表
    submodules = parse_gitmodules()
    if not submodules:
        return []
    
    for submodule in submodules:
        path = submodule['path']
        # 獲取子模組狀態
        status_result = run_command(f"git submodule status {path}")
        if status_result['success'] and status_result['stdout']:
            line = status_result['stdout'].strip()
            status_char = line[0] if line[0] in [' ', '-', '+', 'U'] else ' '
            commit_hash = line[1:41] if len(line) > 41 else ''
            # 更新子模組資訊g95
            submodule.update({
                'commit': commit_hash,
                'status_char': status_char,
                'initialized': status_char != '-',
                'up_to_date': status_char == ' ',
                'has_changes': status_char == '+',
                'uninitialized': status_char == '-',
                'merge_conflict': status_char == 'U'
            })
        else:
            # 如果無法獲取狀態，設置預設值
            submodule.update({
                'commit': '',
                'status_char': '-',
                'initialized': False,
                'up_to_date': False,
                'has_changes': False,
                'uninitialized': True,
                'merge_conflict': False
            })
    
    return submodules

# def update_submodule(submodule: Dict, force: bool = False) -> Dict:
#     """更新單個 submodule"""
#     path = submodule['path']
#     print(f"🔄 更新 {path}...", end=' ')

#     start_time = time.time()
    
#     return submodule

def update_submodule(submodule: Dict, force: bool = False) -> Dict:
    """更新單個 submodule"""
    path = submodule['path']
    print(f"🔄 更新 {path}...", end=' ')
    
    start_time = time.time()
    
    # 如果未初始化，先初始化
    if submodule['uninitialized']:
        print("(初始化)", end=' ')
        init_result = run_command(f"git submodule update --init {path}")
        if not init_result['success']:
            duration = time.time() - start_time
            print(f"❌ 初始化失敗 ({duration:.1f}s)")
            return {
                'path': path,
                'success': False,
                'action': 'init',
                'error': init_result['stderr'],
                'duration': duration
            }
    
    # 更新到最新版本
    if force:
        update_result = run_command(f"git submodule update --remote --force {path}")
        action = 'force_update'
    else:
        update_result = run_command(f"git submodule update --remote {path}")
        action = 'update'
    
    duration = time.time() - start_time
    
    if update_result['success']:
        print(f"✅ 成功 ({duration:.1f}s)")
        return {
            'path': path,
            'success': True,
            'action': action,
            'duration': duration,
            'output': update_result['stdout']
        }
    else:
        print(f"❌ 失敗 ({duration:.1f}s)")
        return {
            'path': path,
            'success': False,
            'action': action,
            'error': update_result['stderr'],
            'duration': duration
        }

def save_update_log(results: List[Dict], filename: str = 'submodule_update_log.json'):
    """保存更新日誌"""
    log_data = {
        'timestamp': datetime.now().isoformat(),
        'total_count': len(results),
        'success_count': sum(1 for r in results if r['success']),
        'failed_count': sum(1 for r in results if not r['success']),
        'total_duration': sum(r['duration'] for r in results),
        'results': results
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(log_data, f, ensure_ascii=False, indent=2)
    
    return log_data

def clean_orphaned_submodules() -> None:
    """清理不在 .gitmodules 中的 submodule 目錄"""
    print("🧹 檢查孤立的 submodule 目錄...")
    
    # 獲取 .gitmodules 中的有效路徑
    valid_submodules = parse_gitmodules()
    valid_paths = {sm['path'] for sm in valid_submodules}
    
    # 掃描現有目錄
    existing_dirs = set()
    for base_dir in ['plugins', 'scripts', 'modules']:
        if os.path.exists(base_dir):
            for item in os.listdir(base_dir):
                item_path = os.path.join(base_dir, item)
                if os.path.isdir(item_path) and not item.startswith('.'):
                    existing_dirs.add(item_path)
    
    # 找出孤立的目錄
    orphaned_dirs = existing_dirs - valid_paths
    
    if not orphaned_dirs:
        print("✅ 沒有發現孤立的 submodule 目錄")
        return
    
    print(f"🗑️ 發現 {len(orphaned_dirs)} 個孤立的目錄:")
    for dir_path in sorted(orphaned_dirs):
        print(f"  • {dir_path}")
    
    if input("\n是否確認刪除這些目錄? (y/N): ").lower() != 'y':
        print("❌ 取消刪除操作")
        return
    
    # 刪除孤立目錄
    success_count = 0
    for dir_path in orphaned_dirs:
        try:
            if os.path.exists(dir_path):
                import shutil
                shutil.rmtree(dir_path)
                print(f"✅ 已刪除: {dir_path}")
                success_count += 1
                
                # 同時清理 .git/modules 中的相關文件
                modules_path = f".git/modules/{dir_path}"
                if os.path.exists(modules_path):
                    shutil.rmtree(modules_path)
                    print(f"🧹 已清理: {modules_path}")
                    
        except Exception as e:
            print(f"❌ 刪除失敗 {dir_path}: {e}")
    
    print(f"\n📊 清理完成: 成功刪除 {success_count} 個目錄")

def main():
    """主函數"""
    # 解析命令行參數
    force_update = '--force' in sys.argv
    skip_failed = '--skip-failed' in sys.argv
    clean_orphaned = '--clean' in sys.argv  # 新增清理選項
    retry_count = 1
    
    if '--retry' in sys.argv:
        try:
            retry_index = sys.argv.index('--retry')
            retry_count = int(sys.argv[retry_index + 1])
        except (IndexError, ValueError):
            retry_count = 2
    
    print("🔄 批量更新 Git Submodules")
    print("=" * 60)
    print(f"選項: 強制更新={force_update}, 跳過失敗={skip_failed}, 清理孤立目錄={clean_orphaned}, 重試次數={retry_count}")
    print()
    
    # 確認在 git 倉庫中
    if not os.path.exists('.git'):
        print("❌ 當前目錄不是 Git 倉庫")
        return
    
    # 如果指定了清理選項，先執行清理
    if clean_orphaned:
        clean_orphaned_submodules()
        print()
    
    # 獲取 submodule 狀態
    submodules = get_submodule_status()
    if not submodules:
        print("📭 沒有找到任何 submodule")
        return
    
    print(f"找到 {len(submodules)} 個 submodule")
    
    # 顯示狀態統計
    status_counts = {
        'initialized': sum(1 for s in submodules if s['initialized']),
        'up_to_date': sum(1 for s in submodules if s['up_to_date']),
        'has_changes': sum(1 for s in submodules if s['has_changes']),
        'uninitialized': sum(1 for s in submodules if s['uninitialized']),
        'merge_conflict': sum(1 for s in submodules if s['merge_conflict'])
    }
    
    print("📊 狀態統計:")
    print(f"  • 已初始化: {status_counts['initialized']}")
    print(f"  • 最新狀態: {status_counts['up_to_date']}")
    print(f"  • 有變更: {status_counts['has_changes']}")
    print(f"  • 未初始化: {status_counts['uninitialized']}")
    print(f"  • 衝突: {status_counts['merge_conflict']}")
    print()
    
    # 開始更新
    all_results = []
    failed_modules = []
    
    for attempt in range(retry_count):
        if attempt > 0:
            print(f"\n🔁 第 {attempt + 1} 次重試 (處理 {len(failed_modules)} 個失敗的模組)")
            submodules_to_process = [s for s in submodules if s['path'] in failed_modules]
        else:
            print("🚀 開始更新所有 submodule...")
            submodules_to_process = submodules
    
        current_results = []
        
        for i, submodule in enumerate(submodules_to_process):
            print(f"[{i+1}/{len(submodules_to_process)}] ", end='')
            
            result = update_submodule(submodule, force_update)
            current_results.append(result)
            
            # 短暫延遲避免過載
            if i < len(submodules_to_process) - 1:
                time.sleep(0.5)
        
        # 更新失敗列表
        if attempt == 0:
            all_results = current_results
        else:
            # 更新之前的結果
            for new_result in current_results:
                for j, old_result in enumerate(all_results):
                    if old_result['path'] == new_result['path']:
                        all_results[j] = new_result
                        break
        
        failed_modules = [r['path'] for r in all_results if not r['success']]
        
        if not failed_modules or skip_failed:
            break
    
    print()
    print("=" * 60)
    print("📊 更新完成統計")
    print("=" * 60)
    
    # 保存日誌
    log_data = save_update_log(all_results)
    
    successful = [r for r in all_results if r['success']]
    failed = [r for r in all_results if not r['success']]
    
    print(f"✅ 成功: {len(successful)}")
    print(f"❌ 失敗: {len(failed)}")
    print(f"⏱️  總耗時: {log_data['total_duration']:.1f} 秒")
    print(f"📄 日誌已保存到: submodule_update_log.json")
    
    if successful:
        avg_time = sum(r['duration'] for r in successful) / len(successful)
        print(f"⚡ 平均更新時間: {avg_time:.1f} 秒")
    
    # 顯示失敗的模組
    if failed:
        print("\n❌ 失敗的模組:")
        for result in failed:
            print(f"  • {result['path']}: {result.get('error', 'Unknown error')}")
        
        print(f"\n🔁 重試失敗的模組:")
        failed_paths = ' '.join(f'"{r["path"]}"' for r in failed)
        print(f"   git submodule update --init --recursive {failed_paths}")
    
    # 建議後續操作
    if successful:
        print("\n📝 建議後續操作:")
        print("1. 檢查更新結果:")
        print("   git status")
        print("2. 提交 submodule 更新:")
        print("   git add .")
        print('   git commit -m "Update submodules"')
        print("3. 推送到遠端:")
        print("   git push")

def remove_failed_submodule(path: str) -> bool:
    """移除失敗的 submodule"""
    print(f"🗑️ 移除失敗的 submodule: {path}")
    
    try:
        # 1. 從 .gitmodules 移除
        result1 = run_command(f"git config -f .gitmodules --remove-section submodule.{path}")
        
        # 2. 從 .git/config 移除
        result2 = run_command(f"git config --remove-section submodule.{path}")
        
        # 3. 從 Git 索引移除
        result3 = run_command(f"git rm --cached {path}")
        
        # 4. 刪除目錄
        if os.path.exists(path):
            import shutil
            shutil.rmtree(path)
        
        # 5. 刪除 .git/modules 中的文件
        modules_path = f".git/modules/{path}"
        if os.path.exists(modules_path):
            import shutil
            shutil.rmtree(modules_path)
        
        print(f"✅ 成功移除 {path}")
        return True
        
    except Exception as e:
        print(f"❌ 移除 {path} 時發生錯誤: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print("用法: python3 update_submodules.py [選項]")
        print("")
        print("選項:")
        print("  --force        強制更新 (git submodule update --force)")
        print("  --skip-failed  跳過失敗的模組，不進行重試")
        print("  --retry N      失敗模組重試 N 次 (預設 1 次)")
        print("  --clean        清理不在 .gitmodules 中的孤立目錄")
        print("  -h, --help     顯示此說明")
        print("")
        print("範例:")
        print("  python3 update_submodules.py")
        print("  python3 update_submodules.py --force")
        print("  python3 update_submodules.py --clean")
        print("  python3 update_submodules.py --retry 3 --clean")
        sys.exit(0)
    
    main()
