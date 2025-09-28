import { test, expect } from '@playwright/test';

const BASE = process.env.GUI_BASE_URL || 'http://localhost:8765';

test('GUI lädt Startseite und zeigt Tabs', async ({ page }) => {
  await page.goto(`${BASE}/`, { waitUntil: 'domcontentloaded' });
  await expect(page.locator('header')).toContainText('Sakana Desktop Assistant');
  await expect(page.locator('#tab-chat')).toBeVisible();
  await expect(page.locator('#tab-playwright')).toBeVisible();
});

test('Playwright-Tab umschalten und Iframe sichtbar', async ({ page }) => {
  await page.goto(`${BASE}/`, { waitUntil: 'domcontentloaded' });
  await page.locator('#tab-playwright').click();
  const iframe = page.locator('#playwright-frame');
  await expect(iframe).toBeVisible();
});