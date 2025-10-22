import { test, expect } from '@playwright/test'

test.describe('GitHub User Clarification Modal', () => {
  test('should show modal dialog when GitHub session needs clarification', async ({ page }) => {
    // Navigate to the sessions page
    await page.goto('http://127.0.0.1:8765/sessions')
    
    // Wait for page to load
    await page.waitForLoadState('networkidle')
    
    // Create a new GitHub session
    await page.click('button:has-text("+ New Session")')
    
    // Fill in session details
    await page.fill('input[placeholder="Task (required)"]', 'list repo')
    await page.selectOption('select', { label: 'github' })
    
    // Create the session
    await page.click('button:has-text("Create")')
    
    // Wait for session to be created
    await page.waitForTimeout(1000)
    
    // Find the GitHub session card and start it
    const sessionCard = page.locator('div.tab:has-text("github")').first()
    await sessionCard.click()
    await sessionCard.locator('button:has-text("Start")').click()
    
    // Wait for agent to start and recognize missing info
    await page.waitForTimeout(5000)
    
    // Check if Live Viewer section appears
    const liveViewer = page.locator('text=Live Viewers')
    await expect(liveViewer).toBeVisible({ timeout: 10000 })
    
    // Check if MCPSessionViewer is loaded
    const sessionViewer = page.locator('text=GITHUB Society of Mind')
    await expect(sessionViewer).toBeVisible({ timeout: 5000 })
    
    // Wait for the clarification modal to appear
    const modal = page.locator('div:has-text("Agent benötigt Information")').first()
    await expect(modal).toBeVisible({ timeout: 15000 })
    
    // Verify modal content
    await expect(page.locator('text=Welcher GitHub')).toBeVisible()
    
    // Test answering the modal
    await page.fill('input[placeholder="Ihre Antwort hier..."]', 'microsoft/vscode')
    await page.click('button:has-text("Absenden")')
    
    // Modal should close
    await expect(modal).not.toBeVisible({ timeout: 5000 })
    
    // Agent should receive answer and continue
    await expect(page.locator('text=User antwortete: microsoft/vscode')).toBeVisible({ timeout: 5000 })
  })
  
  test('should handle suggested answers', async ({ page }) => {
    await page.goto('http://127.0.0.1:8765/sessions')
    await page.waitForLoadState('networkidle')
    
    // Create and start GitHub session (simplified)
    await page.click('button:has-text("+ New Session")')
    await page.fill('input[placeholder="Task (required)"]', 'search repos')
    await page.selectOption('select', { label: 'github' })
    await page.click('button:has-text("Create")')
    await page.waitForTimeout(1000)
    
    const sessionCard = page.locator('div.tab:has-text("github")').first()
    await sessionCard.click()
    await sessionCard.locator('button:has-text("Start")').click()
    
    // Wait for modal with suggested answers
    const modal = page.locator('div:has-text("Agent benötigt Information")')
    await expect(modal).toBeVisible({ timeout: 15000 })
    
    // Click on a suggested answer (if available)
    const suggestion = modal.locator('button').first()
    if (await suggestion.isVisible()) {
      await suggestion.click()
      
      // Modal should close
      await expect(modal).not.toBeVisible({ timeout: 5000 })
    }
  })
})