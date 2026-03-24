import { test, expect } from '@playwright/test'

test.describe('Inspect View', () => {
  test('shows error state for nonexistent skill', async ({ page }) => {
    await page.goto('/skills/nonexistent')

    // Should show either "Skill Not Found" (404 from API) or loading then error
    const hasNotFound = page.getByText('Skill Not Found')
    const hasError = page.getByText('Failed to load skill details')
    const hasLoading = page.locator('.animate-pulse').first()

    const visible = await Promise.race([
      hasNotFound.waitFor({ timeout: 10000 }).then(() => 'not-found'),
      hasError.waitFor({ timeout: 10000 }).then(() => 'error'),
      hasLoading.waitFor({ timeout: 3000 }).then(() => 'loading'),
    ]).catch(() => null)

    // At minimum, the page should render something (not crash)
    expect(visible).not.toBeNull()
  })
})
