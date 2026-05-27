# mSite 專案

這是棋新企業社的內部系統專案，包含轉檔、品項庫存與成本分析功能。

---

## 💻 本地端開發與執行

### 1. 啟動虛擬環境與安裝依賴
```powershell
# 啟動虛擬環境 (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# 安裝套件
pip install -r requirements.txt
```

### 2. 啟動開發伺服器
```powershell
python app.py
```
啟動後可在瀏覽器開啟 `http://127.0.0.1:5000` 進行測試。

---

## 🚀 伺服器部署說明 (vultr2)

本專案在 `vultr2` 伺服器上使用 **Gunicorn + Nginx + Systemd** 運行，並已配置自動部署腳本。

### 部署步驟

當您在本地修改好程式並準備部署至線上時：

#### 步驟 1：在本機將程式推送至 GitHub
```bash
git push origin master
```

#### 步驟 2：SSH 連線至 vultr2 伺服器
```bash
ssh vultr2
```

#### 步驟 3：執行自動部署腳本
登入伺服器後，直接以 `smallken` 身份執行位於其家目錄下的部署腳本：
```bash
sudo -u smallken /home/smallken/deploy.sh
```

---

### 📂 部署腳本運作邏輯說明
位於伺服器 `/home/smallken/deploy.sh` 的腳本會自動完成以下操作：
1. 切換至 `/home/smallken/mSite` 專案目錄。
2. 執行 `git stash` 暫存任何伺服器上的臨時修改。
3. 執行 `git pull origin master` 拉取最新程式碼。
4. 若 `requirements.txt` 有更新，自動使用虛擬環境的 pip 安裝新套件。
5. 執行 `sudo systemctl restart mSite` 重啟服務。
6. 顯示 `mSite` 服務狀態，確保運行無誤。
