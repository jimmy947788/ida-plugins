# GitHub 專案資訊檢查腳本使用說明

## 概述
`check_repos.py` 是一個用於檢查 `.gitmodules` 中所有 GitHub 專案星星數和最後更新日期的腳本。

## 功能特色
- 解析 `.gitmodules` 檔案中的所有 submodule
- 檢查每個 GitHub 專案的：
  - ⭐ 星星數量
  - 📅 最後更新日期
  - 📋 專案描述
- 支援多種 HTTP 方法（urllib、curl、wget）
- 生成 JSON 格式的詳細報告
- 自動處理 GitHub API 限制

## 使用方法

### 基本使用
```bash
python3 check_repos.py
```

### 輸出檔案
腳本會生成以下檔案：
- `repo_info.json` - 詳細的 JSON 格式報告
- `repo_summary.txt` - 簡潔的文字格式摘要

## GitHub API 限制與 Token 設定

### 未授權限制
- GitHub API 對未授權請求的限制：**每小時 60 次**
- 當觸發限制時，需要等待重置時間

### 設定 GitHub Token（推薦）
使用 GitHub Personal Access Token 可以將限制提升到**每小時 5000 次**。

#### 步驟：
1. 前往 GitHub Settings > Developer settings > Personal access tokens
2. 創建新的 token（不需要特殊權限，只需要 public repository 讀取權限）
3. 修改腳本中的 token 設定：

```python
# 在 main() 函數中找到這一行並修改
github_token = "your_github_token_here"  # 替換為您的 token
```

### 備用 HTTP 方法
如果 urllib 遇到問題，腳本會自動嘗試：
1. `curl` 命令
2. `wget` 命令

## 輸出格式範例

### 控制台輸出
```
🔍 檢查 .gitmodules 中的 GitHub 專案...
🌐 HTTP 方法: urllib (Python 內建)
找到 81 個 submodule
其中 80 個是 GitHub 專案
正在獲取專案資訊...

[1/80] 檢查 alexhude/uEmu... ⭐ 156 📅 2024-01-15
[2/80] 檢查 polymorf/findcrypt-yara... ⭐ 89 📅 2023-12-20
```

### JSON 報告範例
```json
{
  "summary": {
    "total_repos": 80,
    "successful": 75,
    "failed": 5,
    "scan_date": "2024-01-20 14:30:00"
  },
  "repositories": [
    {
      "name": "uEmu",
      "path": "plugins/uEmu",
      "url": "https://github.com/alexhude/uEmu.git",
      "stars": 156,
      "last_updated": "2024-01-15T10:30:00Z",
      "description": "Tiny cute emulator plugin for IDA",
      "status": "success"
    }
  ]
}
```

## 故障排除

### API 限制錯誤
```
❌ API 限制，剩餘: 0 次，重置: 32 分鐘後
```
**解決方案：**
- 等待重置時間，或
- 設定 GitHub Token

### 網路連線問題
如果遇到網路問題，腳本會自動嘗試不同的 HTTP 方法。

### 非 GitHub 專案
對於非 GitHub 的 submodule，腳本會標記為 `not_github` 並跳過。

## 技術細節
- **語言：** Python 3
- **依賴：** 僅使用 Python 內建模組
- **API：** GitHub REST API v3
- **限制處理：** 自動重試和錯誤處理

## 檔案結構
```
ida-plugins/
├── check_repos.py          # 主腳本
├── repo_info.json          # 生成的 JSON 報告
├── repo_summary.txt        # 生成的文字摘要
├── .gitmodules            # Git submodule 設定檔
└── README_check_repos.md  # 本說明檔案
```
