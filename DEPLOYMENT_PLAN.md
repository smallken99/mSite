# 商城模組 — 正式環境上線計劃書 (Deployment Plan)

> 專案名稱：mSite（棋新企業社）  
> 更新版本：商品多規格架構（蝦皮風格）與即時庫存管理升級  
> 更新日期：2026/08/22  
> 適用伺服器：`vultr2`（Production）

---

## 📋 一、本次上線變更概覽

| 檢查項目 | 說明 / 狀態 |
|---|---|
| **商品多規格架構** | `ShopProduct` 轉為主品項，新增 `ProductVariant`（支援各規格獨立價格、即時庫存、專屬圖片）。 |
| **蝦皮風格下單流程** | 點擊商品卡片開啟底部詳情彈窗；規格 Pill 支援微縮圖；點擊即時切換大圖；加入購物車後**保留在原商品頁**可連續加購多種規格。 |
| **即時庫存扣減防超賣** | 訂單送出時，後端即時校驗並扣減該規格庫存，同步更新主品項總庫存與價格區間。 |
| **管理者通知信箱變更** | 正式環境管理者通知信箱配置為 **`oioi7211@gmail.com`**，後台提供「測試發信」診斷功能。 |
| **線上資料庫相容性** | 準備專屬遷移腳本 `migrate_add_variants.py`，支援自動新增 `product_variant` 表與擴充欄位，現有商品資料自動轉為「預設」規格，歷史資料零遺失。 |

---

## 🛠️ 二、正式部署標準作業程序（SOP）

### 步驟 1：本機提交並推送程式碼至 GitHub

在 Windows 本機終端機（VS Code / Antigravity IDE 終端）中執行：

```powershell
# 1. 檢視檔案異動狀態
git status

# 2. 加入所有新增與修改的檔案
git add .

# 3. 提交變更
git commit -m "feat: 升級商品多規格架構(蝦皮模式)、即時庫存扣減與規格圖片管理"

# 4. 推送至 GitHub
git push origin master
```

---

### 步驟 2：SSH 連線至線上伺服器（vultr2）

在終端機中透過 SSH 登入生產伺服器：

```bash
ssh vultr2
```

---

### 步驟 3：在伺服器上拉取最新程式與執行資料庫遷移

登入伺服器後，依序執行以下指令：

```bash
# 1. 切換至專案目錄
cd /home/smallken/mSite

# 2. 拉取 GitHub 最新程式碼
git pull origin master

# 3. 執行正式資料庫遷移腳本 (自動升級表結構、建立規格表並配置通知信箱為 oioi7211@gmail.com)
/home/smallken/venv/bin/python migrate_add_variants.py

# 4. 確保商品圖片目錄存在且具備正確寫入權限
mkdir -p /home/smallken/mSite/mSite/static/shop/products
chmod -R 775 /home/smallken/mSite/mSite/static/shop/products
chown -R smallken:smallken /home/smallken/mSite/mSite/static/shop/products
```

---

### 步驟 4：重啟 Gunicorn 服務

重啟 Systemd 服務使新程式碼與設定正式生效：

```bash
# 1. 重啟 mSite 服務
sudo systemctl restart mSite

# 2. 檢查服務運行狀態 (確認為 active (running))
sudo systemctl status mSite --no-pager
```

---

## 🧪 三、上線後功能驗證清單（Verification Checklist）

部署完成後，請至線上站點（`https://store.smallken.site`）依序執行以下 6 項檢查：

- [ ] **1. 後台設定與測試發信**：
  - 前往後台 `商城管理` → `商城設定` (https://store.smallken.site/shop/admin/settings)。
  - 確認管理者通知 Email 顯示為 **`oioi7211@gmail.com`**。
  - 點擊「**測試發信**」按鈕，確認收到綠色成功提示，並檢查 `oioi7211@gmail.com` 收件匣是否收到測試信。
- [ ] **2. 後台商品與規格管理**：
  - 進入「**商品管理**」，表格清單顯示「規格數」與「價格區間」。
  - 點擊既有商品的「**編輯**」，確認庫存與售價數字清晰顯示（加減按鈕置右），且能為每個規格獨立上傳圖片或新增規格。
- [ ] **3. 前台商品列表與價格區間**：
  - 手機瀏覽前台 `https://store.smallken.site/shop`。
  - 多規格商品顯示價格區間（如 `NT$ 35 ~ 75`），點擊商品卡片順暢由底部滑出詳情彈窗。
- [ ] **4. 規格選擇與連續加購流程**：
  - 點選不同規格 Pill，確認按鈕左側顯示小縮圖，且上方大圖與價格即時切換。
  - 點擊「**➕ 加入購物車**」，確認**畫面停留在原商品頁**並彈出成功提示，可直接點選另一規格繼續加購。
- [ ] **5. 成立訂單與即時庫存扣減**：
  - 點擊底部左側「**🛒 購物車 (N)**」開啟購物車抽屜，送出訂單。
  - 確認訂單成立後跳出純文字複製框（明細品名呈現為「商品名 - 規格名」）。
  - 返回商品列表，確認該規格的**庫存數字已即時扣減**。
- [ ] **6. 管理者 Email 訂單通知**：
  - 檢查 **`oioi7211@gmail.com`** 信箱是否收到該筆訂單格式化 HTML 明細通知信。

---

## 🔄 四、應變與回滾計劃（Rollback Plan）

若上線後遇到任何非預期問題需要緊急復原：

```bash
# 1. 在伺服器上回復至上一個 Commit
cd /home/smallken/mSite
git reset --hard HEAD~1

# 2. 重啟服務即可立即回到更新前的狀態
sudo systemctl restart mSite
```

> **備註**：本次資料庫升級採**向下相容**設計（新增 `product_variant` 表與獨立欄位），舊版程式碼依然相容運行，回滾時無需刪除資料庫欄位。
