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
  await page.goto('/')
  await page.getByLabel('Email').fill('admin@local.test')
  await page.getByLabel('Password').fill('admin123')
  await page.getByRole('button', { name: 'Login' }).click()
  await expect(page.getByText('Dev Admin')).toBeVisible()
  await page.goto('/settings')
  await expect(page.getByText('Runtime Settings')).toBeVisible()
})

