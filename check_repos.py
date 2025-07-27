#!/usr/bin/env python3
"""
檢查 .gitmodules 中每個 GitHub 專案的星星數和最後更新日期
"""

import re
import requests
import time
from datetime import datetime
from typing import List, Dict, Tuple
import sys
import json

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

def extract_github_info(url: str) -> Tuple[str, str]:
    """從 URL 提取 GitHub 用戶名和專案名"""
    # 支援不同的 GitHub URL 格式
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
            # 檢查是否是速率限制
            if 'X-RateLimit-Remaining' in response.headers:
                remaining = response.headers.get('X-RateLimit-Remaining', '0')
                reset_time = response.headers.get('X-RateLimit-Reset', '0')
                formatted_reset = format_reset_time(reset_time)
                return {'status': 'rate_limited', 'error': f'API 限制，剩餘: {remaining} 次，重置: {formatted_reset}'}
            else:
                return {'status': 'rate_limited', 'error': 'API 限制，請設定 GitHub token'}
        else:
            return {'status': 'error', 'error': f'HTTP {response.status_code}'}
            
    except requests.exceptions.RequestException as e:
        return {'status': 'error', 'error': str(e)}

def format_date(date_str: str) -> str:
    """格式化日期字串"""
    if not date_str:
        return 'N/A'
    
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d')
    except:
        return date_str

def format_reset_time(reset_timestamp: str) -> str:
    """格式化重置時間戳"""
    try:
        reset_dt = datetime.fromtimestamp(int(reset_timestamp))
        now = datetime.now()
        diff = reset_dt - now
        
        if diff.total_seconds() > 0:
            minutes = int(diff.total_seconds() // 60)
            return f"{minutes} 分鐘後 ({reset_dt.strftime('%H:%M')})"
        else:
            return "已重置"
    except:
        return reset_timestamp

def main():
    """主函數"""
    print("🔍 檢查 .gitmodules 中的 GitHub 專案...")
    print("=" * 80)
    
    # 解析 .gitmodules
    try:
        submodules = parse_gitmodules('.gitmodules')
        print(f"找到 {len(submodules)} 個 submodule")
    except Exception as e:
        print(f"❌ 無法讀取 .gitmodules: {e}")
        return
    
    # GitHub token (可選，用於提高 API 限制)
    github_token = None  # 您可以在這裡設定您的 GitHub token
    
    results = []
    github_repos = []
    
    # 篩選出 GitHub 專案
    for sub in submodules:
        owner, repo = extract_github_info(sub['url'])
        if owner and repo:
            github_repos.append((sub, owner, repo))
        else:
            results.append({
                'name': sub['name'],
                'path': sub['path'],
                'url': sub['url'],
                'status': 'not_github',
                'error': '非 GitHub 專案'
            })
    
    print(f"其中 {len(github_repos)} 個是 GitHub 專案")
    print("正在獲取專案資訊...")
    print("⏰ 使用 2 秒間隔避免 API 限制...")
    print()
    
    # 獲取每個 GitHub 專案的資訊
    for i, (sub, owner, repo) in enumerate(github_repos):
        print(f"[{i+1}/{len(github_repos)}] 檢查 {owner}/{repo}...", end=' ')
        
        info = get_repo_info(owner, repo, github_token)
        
        result = {
            'name': sub['name'],
            'path': sub['path'],
            'url': sub['url'],
            'owner': owner,
            'repo': repo,
            **info
        }
        
        if info['status'] == 'success':
            print(f"⭐ {info['stars']} 📅 {format_date(info['last_updated'])}")
        else:
            print(f"❌ {info.get('error', 'Unknown error')}")
        
        results.append(result)
        
        # 避免觸發 GitHub API 限制
        if i < len(github_repos) - 1:
            time.sleep(2.0)  # 增加到 2 秒間隔
    
    print()
    print("=" * 80)
    print("📊 統計結果")
    print("=" * 80)
    
    # 排序結果（按星星數排序）
    successful_results = [r for r in results if r.get('status') == 'success']
    successful_results.sort(key=lambda x: x.get('stars', 0), reverse=True)
    
    # 顯示結果表格
    print(f"{'專案名稱':<40} {'⭐ 星星':<8} {'📅 更新日期':<12} {'🏷️ 語言':<12} {'📝 描述':<50}")
    print("-" * 120)
    
    for result in successful_results:
        name = result['name'][:39]
        stars = result.get('stars', 0)
        last_updated = format_date(result.get('last_updated', ''))
        language = (result.get('language') or 'N/A')[:11]
        description = (result.get('description') or '')[:49]
        
        # 標記特殊狀態
        flags = []
        if result.get('archived'):
            flags.append('🗄️')
        if result.get('fork'):
            flags.append('🍴')
        
        flag_str = ''.join(flags)
        
        print(f"{name:<40} {stars:<8} {last_updated:<12} {language:<12} {description:<50} {flag_str}")
    
    # 顯示錯誤的專案
    error_results = [r for r in results if r.get('status') != 'success']
    if error_results:
        print()
        print("⚠️  有問題的專案:")
        print("-" * 80)
        for result in error_results:
            print(f"❌ {result['name']}: {result.get('error', 'Unknown error')}")
    
    # 統計資訊
    print()
    print("📈 統計資訊:")
    print(f"• 總專案數: {len(submodules)}")
    print(f"• GitHub 專案: {len(github_repos)}")
    print(f"• 成功獲取資訊: {len(successful_results)}")
    print(f"• 有問題的專案: {len(error_results)}")
    
    if successful_results:
        total_stars = sum(r.get('stars', 0) for r in successful_results)
        avg_stars = total_stars / len(successful_results)
        print(f"• 總星星數: {total_stars}")
        print(f"• 平均星星數: {avg_stars:.1f}")
    
    # 保存結果到 JSON 文件
    output_file = 'repo_info.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 詳細結果已保存到: {output_file}")

if __name__ == "__main__":
    main()
