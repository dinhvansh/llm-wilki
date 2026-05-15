import { expect, test } from '@playwright/test'

const routes = ['/', '/sources', '/pages', '/ask', '/review', '/graph', '/lint', '/collections']

test.describe('primary route smoke', () => {
  for (const route of routes) {
    test(`renders ${route}`, async ({ page }) => {
      await page.goto(route)
      await expect(page.locator('body')).toBeVisible()
      await expect(page.locator('body')).not.toHaveText(/^$/)
    })
  }
})

test('login user menu and protected settings route render', async ({ page }) => {
  await page.goto('/login')
  await page.locator('input[autocomplete="email"]').fill('admin@local.test')
  await page.locator('input[autocomplete="current-password"]').fill('admin123')
  await page.getByRole('button', { name: 'Sign In' }).click()
  await expect(page).toHaveURL(/\/$/)
  await page.goto('/settings')
  await expect(page.getByRole('heading', { name: 'Settings' })).toBeVisible()
})
