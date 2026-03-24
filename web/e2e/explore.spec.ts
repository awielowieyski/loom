import { test, expect } from '@playwright/test'

test.describe('Explore View', () => {
  test('shows map container or loading state', async ({ page }) => {
    await page.goto('/explore')

    // Should show either the SVG map, loading state, or empty state
    const hasSvg = page.locator('svg').first()
    const hasLoading = page.getByText('Loading semantic map...')
    const hasEmpty = page.getByText('No skills or capabilities')

    const visible = await Promise.race([
      hasSvg.waitFor({ timeout: 5000 }).then(() => 'svg'),
      hasLoading.waitFor({ timeout: 5000 }).then(() => 'loading'),
      hasEmpty.waitFor({ timeout: 5000 }).then(() => 'empty'),
    ]).catch(() => null)

    expect(visible).not.toBeNull()
  })

  test('shows search filter input', async ({ page }) => {
    await page.goto('/explore')
    const searchInput = page.getByPlaceholder('Filter by name or slug...')
    await expect(searchInput).toBeVisible()
  })
})
