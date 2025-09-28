
import { test } from '@playwright/test';
import { expect } from '@playwright/test';

test('MCPViewer_2025-09-26', async ({ page, context }) => {
  
    // Navigate to URL
    await page.goto('http://127.0.0.1:8765/', { waitUntil: 'networkidle' });
});