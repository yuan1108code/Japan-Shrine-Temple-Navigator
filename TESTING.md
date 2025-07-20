# 福井神社導航系統 - 測試指南

## 測試架構

本專案使用多層次的測試策略，確保系統品質和穩定性。

### 測試類型

1. **單元測試** - Python 後端邏輯測試
2. **API 測試** - FastAPI 端點測試
3. **整合測試** - 資料庫和服務整合測試
4. **E2E 測試** - Playwright 前端測試

## Playwright 測試設定

### 安裝依賴

```bash
# 安裝 Node.js 依賴
npm install

# 安裝 Playwright 瀏覽器
npx playwright install

# 或使用 Python
pip install playwright
python -m playwright install
```

### 運行測試

```bash
# 執行所有測試
npm test

# 使用可視化模式
npm run test:headed

# 使用 UI 模式
npm run test:ui

# 查看測試報告
npm run test:report

# 只測試特定瀏覽器
npx playwright test --project=chromium

# 測試特定檔案
npx playwright test tests/test_web_interface.py
```

### Python 測試

```bash
# 安裝測試依賴
pip install -e ".[testing]"

# 運行 Playwright 測試
python tests/test_web_interface.py

# 使用 pytest
pytest tests/test_web_interface.py -v
```

## 測試環境準備

### 1. 啟動伺服器

```bash
# 使用啟動腳本
python tools/start_server.py

# 或手動啟動
python -m uvicorn src.main.python.app:app --reload --port 8000
```

### 2. 設定環境變數

```bash
export OPENAI_API_KEY="your-api-key"
```

### 3. 初始化向量資料庫

```bash
python tools/setup_vector_db.py
```

## 測試範圍

### 前端測試 (Playwright)

- ✅ 頁面載入和渲染
- ✅ 響應式設計 (桌面、平板、手機)
- ✅ 搜尋功能
- ✅ AI 問答功能
- ✅ 推薦系統
- ✅ 地理位置服務
- ✅ API 狀態監控
- ✅ 錯誤處理
- ✅ 載入狀態

### API 測試

- ✅ 健康檢查端點
- ✅ 搜尋端點
- ✅ 問答端點
- ✅ 推薦端點
- ✅ 地理柵欄端點
- ✅ 統計資訊端點

### 整合測試

- ✅ 向量資料庫連接
- ✅ OpenAI API 整合
- ✅ 地理位置計算
- ✅ 檔案服務

## 測試資料

### 測試地點座標

```javascript
// 福井市中心
const fukuiCenter = { latitude: 36.0612, longitude: 136.2236 };

// 測試用神社位置
const testShrine = { latitude: 36.0620, longitude: 136.2240 };
```

### 測試查詢

- "福井神社" - 基本搜尋測試
- "福井有哪些著名的神社？" - AI 問答測試
- "歷史, 文化" - 推薦系統測試

## 持續整合

### GitHub Actions

```yaml
name: 測試
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - uses: actions/setup-node@v4
        with:
          node-version: '18'
      - run: pip install -e ".[testing]"
      - run: npm install
      - run: npx playwright install
      - run: python tools/setup_vector_db.py
      - run: npm test
```

## 效能測試

### 載入時間基準

- 首頁載入: < 2 秒
- API 回應: < 5 秒
- 搜尋結果: < 3 秒
- AI 問答: < 10 秒

### 測試工具

```bash
# 使用 Lighthouse
npx lighthouse http://localhost:8000/web --output=html

# 使用 Playwright 效能測試
npx playwright test --reporter=html --project=chromium
```

## 偵錯技巧

### 1. 截圖和錄影

```javascript
// 在測試中添加截圖
await page.screenshot({ path: 'debug.png' });

// 錄製影片
await page.video().path();
```

### 2. 瀏覽器控制台

```javascript
// 監聽控制台訊息
page.on('console', msg => console.log(msg.text()));

// 監聽網路請求
page.on('request', request => console.log(request.url()));
```

### 3. 暫停執行

```javascript
// 暫停測試用於偵錯
await page.pause();
```

## 測試最佳實踐

### 1. 測試隔離

- 每個測試獨立運行
- 使用新的瀏覽器頁面
- 清理測試資料

### 2. 穩定的選擇器

```javascript
// 好的選擇器
await page.locator('[data-testid="search-button"]').click();

// 避免的選擇器
await page.locator('.btn.btn-primary').click();
```

### 3. 等待策略

```javascript
// 等待元素可見
await page.waitForSelector('#results');

// 等待網路請求完成
await page.waitForLoadState('networkidle');

// 等待 API 回應
await page.waitForResponse('**/api/search');
```

## 故障排除

### 常見問題

1. **伺服器未啟動**
   - 檢查 `http://localhost:8000/health`
   - 確認 Python 依賴已安裝

2. **瀏覽器未安裝**
   - 運行 `npx playwright install`

3. **API 金鑰問題**
   - 設定 `OPENAI_API_KEY` 環境變數

4. **向量資料庫未初始化**
   - 運行 `python tools/setup_vector_db.py`

### 日誌分析

```bash
# 查看伺服器日誌
python tools/start_server.py

# 查看測試日誌
npx playwright test --reporter=list

# 詳細偵錯資訊
DEBUG=pw:api npx playwright test
```

## 報告和監控

### 測試報告

- HTML 報告: `playwright-report/index.html`
- JSON 結果: `test-results/results.json`
- 截圖: `test-results/`

### 覆蓋率報告

```bash
# Python 覆蓋率
pip install coverage
coverage run -m pytest
coverage html

# JavaScript 覆蓋率 (如果有前端 JS 測試)
npx nyc playwright test
```

## 效能監控

### 核心指標

- **首次內容繪製 (FCP)**: < 1.5s
- **最大內容繪製 (LCP)**: < 2.5s
- **累計版面位移 (CLS)**: < 0.1
- **首次輸入延遲 (FID)**: < 100ms

### 監控工具

```bash
# Web Vitals 測試
npx web-vitals-cli http://localhost:8000/web

# 效能分析
npx playwright test --trace=on
```

---

## 結論

完整的測試策略確保福井神社導航系統的品質和可靠性。透過自動化測試，我們可以：

- 🔍 及早發現問題
- 🚀 加速開發流程  
- 📊 監控系統效能
- 🛡️ 確保用戶體驗

定期執行測試並監控結果，持續改進系統品質。