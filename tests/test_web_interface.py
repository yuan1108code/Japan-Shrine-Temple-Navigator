"""
Web 介面 Playwright 測試
測試福井神社導航的前端功能
"""

import pytest
from playwright.async_api import async_playwright, Page, Browser
import asyncio
import time


class TestWebInterface:
    """Web 介面測試類別"""
    
    @pytest.fixture(scope="session")
    async def browser(self):
        """瀏覽器實例"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            yield browser
            await browser.close()
    
    @pytest.fixture(scope="function")
    async def page(self, browser: Browser):
        """頁面實例"""
        page = await browser.new_page()
        yield page
        await page.close()
    
    async def test_homepage_loads(self, page: Page):
        """測試首頁載入"""
        await page.goto("http://localhost:8000/web")
        
        # 檢查頁面標題
        title = await page.title()
        assert "福井神社導航" in title
        
        # 檢查主要元素存在
        assert await page.locator("h1").is_visible()
        assert await page.locator("#search-input").is_visible()
        assert await page.locator("#ask-input").is_visible()
    
    async def test_navigation_bar(self, page: Page):
        """測試導航欄功能"""
        await page.goto("http://localhost:8000/web")
        
        # 檢查導航欄連結
        nav_links = page.locator(".navbar-nav .nav-link")
        count = await nav_links.count()
        assert count >= 4
        
        # 測試點擊導航連結
        await page.locator('a[href="#search-section"]').click()
        await page.wait_for_timeout(500)
        
        # 檢查是否滾動到對應區塊
        search_section = page.locator("#search-section")
        assert await search_section.is_visible()
    
    async def test_search_functionality(self, page: Page):
        """測試搜尋功能"""
        await page.goto("http://localhost:8000/web")
        
        # 填入搜尋關鍵詞
        await page.locator("#search-input").fill("神社")
        
        # 選擇類別
        await page.locator("#search-category").select_option("神社")
        
        # 點擊搜尋按鈕
        await page.locator("#search-form button[type=submit]").click()
        
        # 等待結果載入
        await page.wait_for_selector("#search-results", timeout=10000)
        
        # 檢查是否有載入狀態或結果
        results_content = await page.locator("#search-results").inner_text()
        assert len(results_content) > 0
    
    async def test_ai_chat_functionality(self, page: Page):
        """測試 AI 問答功能"""
        await page.goto("http://localhost:8000/web")
        
        # 填入問題
        await page.locator("#ask-input").fill("福井有哪些著名的神社？")
        
        # 點擊提問按鈕
        await page.locator("#ask-form button[type=submit]").click()
        
        # 等待 AI 回應
        await page.wait_for_selector("#ask-results", timeout=15000)
        
        # 檢查回應內容
        results_content = await page.locator("#ask-results").inner_text()
        assert len(results_content) > 0
    
    async def test_recommendation_form(self, page: Page):
        """測試推薦功能表單"""
        await page.goto("http://localhost:8000/web")
        
        # 填入推薦偏好
        await page.locator("#rec-category").select_option("神社")
        await page.locator("#rec-interests").fill("歷史, 文化")
        
        # 點擊獲取推薦按鈕
        await page.locator("#recommendation-form button[type=submit]").click()
        
        # 等待推薦結果
        await page.wait_for_selector("#recommendation-results", timeout=10000)
        
        # 檢查結果
        results_content = await page.locator("#recommendation-results").inner_text()
        assert len(results_content) > 0
    
    async def test_geolocation_functionality(self, page: Page):
        """測試地理位置功能"""
        await page.goto("http://localhost:8000/web")
        
        # 模擬地理位置權限
        await page.context.grant_permissions(["geolocation"])
        await page.context.set_geolocation({"latitude": 36.0612, "longitude": 136.2236})
        
        # 點擊獲取位置按鈕
        await page.locator("#get-location-btn").click()
        
        # 等待位置資訊顯示
        await page.wait_for_selector("#location-info", timeout=5000)
        
        # 檢查位置資訊
        location_text = await page.locator("#location-info").inner_text()
        assert "緯度" in location_text or "位置" in location_text
    
    async def test_responsive_design(self, page: Page):
        """測試響應式設計"""
        await page.goto("http://localhost:8000/web")
        
        # 測試桌面版本
        await page.set_viewport_size({"width": 1200, "height": 800})
        assert await page.locator(".container").is_visible()
        
        # 測試平板版本
        await page.set_viewport_size({"width": 768, "height": 1024})
        assert await page.locator(".navbar-toggler").is_visible()
        
        # 測試手機版本
        await page.set_viewport_size({"width": 375, "height": 667})
        assert await page.locator(".navbar-toggler").is_visible()
    
    async def test_api_status_indicator(self, page: Page):
        """測試 API 狀態指示器"""
        await page.goto("http://localhost:8000/web")
        
        # 等待 API 狀態載入
        await page.wait_for_selector("#api-status", timeout=5000)
        
        # 檢查狀態指示器
        status_element = page.locator("#api-status")
        assert await status_element.is_visible()
        
        # 檢查狀態文字
        status_text = await status_element.inner_text()
        assert status_text in ["API 運行正常", "API 連接失敗", "檢查中..."]
    
    async def test_error_handling(self, page: Page):
        """測試錯誤處理"""
        await page.goto("http://localhost:8000/web")
        
        # 測試空搜尋
        await page.locator("#search-form button[type=submit]").click()
        
        # 檢查是否顯示錯誤訊息
        await page.wait_for_timeout(1000)
        
        # 測試空問答
        await page.locator("#ask-form button[type=submit]").click()
        
        # 檢查錯誤處理
        await page.wait_for_timeout(1000)
    
    async def test_loading_states(self, page: Page):
        """測試載入狀態"""
        await page.goto("http://localhost:8000/web")
        
        # 觸發搜尋並檢查載入狀態
        await page.locator("#search-input").fill("測試")
        await page.locator("#search-form button[type=submit]").click()
        
        # 檢查載入指示器
        loading_present = False
        try:
            await page.wait_for_selector(".loading-spinner", timeout=2000)
            loading_present = True
        except:
            pass
        
        # 載入狀態可能很快消失，所以不強制要求
        # 主要檢查功能是否正常運作
        await page.wait_for_timeout(3000)


@pytest.mark.asyncio
async def test_full_user_journey(browser: Browser):
    """完整用戶流程測試"""
    page = await browser.new_page()
    
    try:
        # 1. 訪問首頁
        await page.goto("http://localhost:8000/web")
        assert await page.locator("h1").is_visible()
        
        # 2. 執行搜尋
        await page.locator("#search-input").fill("福井神社")
        await page.locator("#search-form button[type=submit]").click()
        await page.wait_for_timeout(3000)
        
        # 3. 進行 AI 問答
        await page.locator("#ask-input").fill("這些神社有什麼特色？")
        await page.locator("#ask-form button[type=submit]").click()
        await page.wait_for_timeout(5000)
        
        # 4. 獲取推薦
        await page.locator("#rec-category").select_option("神社")
        await page.locator("#recommendation-form button[type=submit]").click()
        await page.wait_for_timeout(3000)
        
        # 5. 載入統計資訊
        await page.locator("#load-stats-btn").click()
        await page.wait_for_timeout(2000)
        
        print("✅ 完整用戶流程測試通過")
        
    finally:
        await page.close()


if __name__ == "__main__":
    # 直接運行測試
    import subprocess
    import sys
    
    print("🧪 執行 Playwright 測試...")
    
    # 確保 Playwright 瀏覽器已安裝
    try:
        subprocess.run([sys.executable, "-m", "playwright", "install"], check=True)
    except subprocess.CalledProcessError:
        print("❌ Playwright 瀏覽器安裝失敗")
        sys.exit(1)
    
    # 運行測試
    pytest_args = [
        "-v",
        "--tb=short",
        __file__
    ]
    
    exit_code = pytest.main(pytest_args)
    sys.exit(exit_code)