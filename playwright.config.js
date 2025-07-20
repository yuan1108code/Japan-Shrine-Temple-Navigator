// Playwright 測試配置
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  
  // 全域測試超時
  timeout: 30 * 1000,
  expect: {
    timeout: 5000
  },
  
  // 失敗時重試次數
  retries: process.env.CI ? 2 : 0,
  
  // 並行執行的 worker 數量
  workers: process.env.CI ? 1 : undefined,
  
  // 報告器
  reporter: [
    ['html'],
    ['list'],
    ['json', { outputFile: 'test-results/results.json' }]
  ],
  
  // 全域設定
  use: {
    baseURL: 'http://localhost:8000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },

  // 專案配置
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
    
    // 行動裝置測試
    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'] },
    },
    {
      name: 'Mobile Safari',
      use: { ...devices['iPhone 12'] },
    },
    
    // 平板測試
    {
      name: 'Tablet',
      use: { ...devices['iPad Pro'] },
    },
  ],

  // Web 伺服器配置 (如果需要自動啟動)
  webServer: {
    command: 'python -m uvicorn src.main.python.app:app --host 0.0.0.0 --port 8000',
    port: 8000,
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000,
  },
});