import { expect, test } from '@playwright/test'

test('ask page accepts submitted question', async ({ page }) => {
  await page.goto('/login')
  await page.locator('input[autocomplete="email"]').fill('admin@local.test')
  await page.locator('input[autocomplete="current-password"]').fill('admin123')
  await page.getByRole('button', { name: 'Sign In' }).click()
  await expect(page).toHaveURL(/\/$/)
  await page.goto('/ask')
  await page.getByPlaceholder('Ask a question about your knowledge base...').fill('zzzz unsupported unknown corporate policy 2099')
  await page.locator('form button[type="submit"]').click()
  await expect(page.locator('p.text-sm', { hasText: 'zzzz unsupported unknown corporate policy 2099' }).last()).toBeVisible()
})
