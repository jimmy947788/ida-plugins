#!/usr/bin/env python3
"""
檢查 .gitmodules 中每個 GitHub 專案的星星數和最後更新日期（批量版本）
支援分批處理和從失敗處繼續
"""

import re
import requests
import time
import json
import sys
from datetime import datetime
from typing import List, Dict, Tuple, Optional

def parse_gitmodules(file_path: str) -> List[Dict[str, str]]:
    """解析 .gitmodules 文件，提取 submodule 資訊"""
    submodules = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 使用正則表達式匹配 submodule 區塊
    pattern = r'\[submodule\s+"([^"]+)"\]\s*\n\s*path\s*=\s*([^\n]+)\s*\n\s*url\s*=\s*([^\n]+)'
    matches = re.findall(pattern, content)
    
    for match in matches:
        name = match[0].strip()
        path = match[1].strip()
        url = match[2].strip()
        
        submodules.append({
            'name': name,
            'path': path,
            'url': url
        })
    
    return submodules

def extract_github_info(url: str) -> Tuple[Optional[str], Optional[str]]:
    """從 URL 提取 GitHub 用戶名和專案名"""
    patterns = [
        r'https://github\.com/([^/]+)/([^/]+)(?:\.git)?/?$',
        r'git@github\.com:([^/]+)/([^/]+)(?:\.git)?/?$'
    ]
    
    for pattern in patterns:
        match = re.match(pattern, url.strip())
        if match:
            return match.group(1), match.group(2).replace('.git', '')
    
    return None, None

def get_repo_info(owner: str, repo: str, token: str = None) -> Dict:
    """獲取 GitHub 專案資訊"""
    url = f"https://api.github.com/repos/{owner}/{repo}"
    
    headers = {
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'ida-plugins-checker'
    }
    
    if token:
        headers['Authorization'] = f'token {token}'
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            return {
                'stars': data.get('stargazers_count', 0),
                'last_updated': data.get('updated_at', ''),
                'description': data.get('description', ''),
                'language': data.get('language', ''),
                'archived': data.get('archived', False),
                'fork': data.get('fork', False),
                'status': 'success'
            }
        elif response.status_code == 404:
            return {'status': 'not_found', 'error': '專案不存在或已刪除'}
        elif response.status_code == 403:
            remaining = response.headers.get('X-RateLimit-Remaining', '0')
            reset_time = response.headers.get('X-RateLimit-Reset', '0')
            return {'status': 'rate_limited', 'error': f'API 限制，剩餘: {remaining}', 'reset_time': reset_time}
        else:
            return {'status': 'error', 'error': f'HTTP {response.status_code}'}
            
    except requests.exceptions.RequestException as e:
        return {'status': 'error', 'error': str(e)}

def load_progress(filename: str = 'repo_progress.json') -> Dict:
    """載入進度"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {'processed': [], 'last_index': 0}

def save_progress(data: Dict, filename: str = 'repo_progress.json'):
    """保存進度"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def main():
    """主函數"""
    # 命令行參數
    start_index = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    batch_size = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    
    print(f"🔍 批量檢查 GitHub 專案 (從第 {start_index} 個開始，批量大小: {batch_size})")
    print("=" * 80)
    
    # 解析 .gitmodules
    submodules = parse_gitmodules('.gitmodules')
    github_repos = []
    
    for sub in submodules:
        owner, repo = extract_github_info(sub['url'])
        if owner and repo:
            github_repos.append((sub, owner, repo))
    
    print(f"找到 {len(github_repos)} 個 GitHub 專案")
    
    # 載入進度
    progress = load_progress()
    processed_repos = {f"{r['owner']}/{r['repo']}" for r in progress['processed']}
    
    # 從指定位置開始處理
    to_process = github_repos[start_index:start_index + batch_size]
    
    print(f"本次處理範圍: {start_index} - {start_index + len(to_process) - 1}")
    print(f"已處理過的專案: {len(processed_repos)} 個")
    print()
    
    results = []
    
    for i, (sub, owner, repo) in enumerate(to_process):
        actual_index = start_index + i
        repo_key = f"{owner}/{repo}"
        
        # 跳過已處理的
        if repo_key in processed_repos:
            print(f"[{actual_index + 1}] 跳過 {repo_key} (已處理)")
            continue
        
        print(f"[{actual_index + 1}/{len(github_repos)}] 檢查 {repo_key}...", end=' ')
        
        info = get_repo_info(owner, repo)
        
        result = {
            'name': sub['name'],
            'path': sub['path'],
            'url': sub['url'],
            'owner': owner,
            'repo': repo,
            **info
        }
        
        if info['status'] == 'success':
            print(f"⭐ {info['stars']} 📅 {info['last_updated'][:10]}")
        elif info['status'] == 'rate_limited':
            print(f"❌ {info['error']}")
            if 'reset_time' in info:
                reset_dt = datetime.fromtimestamp(int(info['reset_time']))
                print(f"   API 重置時間: {reset_dt.strftime('%Y-%m-%d %H:%M:%S')}")
            break  # 遇到速率限制就停止
        else:
            print(f"❌ {info.get('error', 'Unknown error')}")
        
        results.append(result)
        progress['processed'].append(result)
        progress['last_index'] = actual_index + 1
        
        # 保存進度
        save_progress(progress)
        
        # 間隔
        if i < len(to_process) - 1:
            print("   ⏰ 等待 3 秒...")
            time.sleep(3.0)
    
    print()
    print("📊 本次結果:")
    print(f"• 處理了 {len(results)} 個專案")
    print(f"• 總進度: {progress['last_index']}/{len(github_repos)}")
    
    # 顯示成功的結果
    successful = [r for r in results if r.get('status') == 'success']
    if successful:
        print("\n成功獲取的專案:")
        for r in sorted(successful, key=lambda x: x.get('stars', 0), reverse=True):
            print(f"  ⭐ {r['stars']:4d} - {r['owner']}/{r['repo']}")
    
    # 建議下次運行的命令
    if progress['last_index'] < len(github_repos):
        print(f"\n📝 繼續處理請運行:")
        print(f"   python3 {sys.argv[0]} {progress['last_index']} {batch_size}")
    else:
        print("\n🎉 所有專案都已處理完成！")

if __name__ == "__main__":
    main()
