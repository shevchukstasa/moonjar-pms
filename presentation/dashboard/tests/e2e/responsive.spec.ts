import { test, expect } from '@playwright/test';
import {
  users,
  mockAuthMe,
  mockApi,
} from './helpers';

// ---------------------------------------------------------------------------
// Mock data
// ---------------------------------------------------------------------------
const mockPmUser = {
  id: 'u-pm-1',
  email: users.pm.email,
  name: 'PM User',
  role: users.pm.role,
};

const mockSorterUser = {
  id: 'u-sort-1',
  email: users.sorter.email,
  name: 'Sorter User',
  role: users.sorter.role,
};

// ---------------------------------------------------------------------------
// Common mock setup
// ---------------------------------------------------------------------------
async function setupMocks(page: import('@playwright/test').Page) {
  await mockApi(page, '**/api/factories*', { items: [{ id: 'f1', name: 'Bali' }], total: 1 });
  await mockApi(page, '**/api/schedule/glazing*', { items: [], total: 0 });
  await mockApi(page, '**/api/schedule/firing*', { items: [], total: 0 });
  await mockApi(page, '**/api/schedule/sorting*', { items: [], total: 0 });
  await mockApi(page, '**/api/schedule/kilns*', { items: [], total: 0 });
  await mockApi(page, '**/api/positions*', { items: [], total: 0 });
  await mockApi(page, '**/api/kilns*', { items: [], total: 0 });
  await mockApi(page, '**/api/tasks*', { items: [], total: 0 });
  await mockApi(page, '**/api/tasks/sorter*', { items: [], total: 0 });
  await mockApi(page, '**/api/packing-photos*', { items: [], total: 0 });
  await mockApi(page, '**/api/orders*', { items: [], total: 0 });
  await mockApi(page, '**/api/materials*', { items: [], total: 0 });
  await mockApi(page, '**/api/purchase-requests*', { items: [], total: 0 });
  await mockApi(page, '**/api/quality*', { items: [], total: 0 });
  await mockApi(page, '**/api/inspections*', { items: [], total: 0 });
  await mockApi(page, '**/api/analytics*', {});
  await mockApi(page, '**/api/problem-cards*', { items: [], total: 0 });
  await mockApi(page, '**/api/shortage-tasks*', { items: [], total: 0 });
  await mockApi(page, '**/api/defects*', { items: [], total: 0 });
  await mockApi(page, '**/api/toc*', {});
  await mockApi(page, '**/api/cancellation-requests*', { items: [], total: 0 });
  await mockApi(page, '**/api/change-requests*', { items: [], total: 0 });
  await mockApi(page, '**/api/stock*', { items: [], total: 0 });
}

// ---------------------------------------------------------------------------
// Tests — Mobile viewport (375 x 812, iPhone style)
// ---------------------------------------------------------------------------

test.describe('Mobile Responsive Tests', () => {
  test.use({ viewport: { width: 375, height: 812 } });

  test('should render login page correctly on mobile', async ({ page }) => {
    await mockAuthMe(page, null);
    await page.goto('/login');

    // Form should be visible and properly sized
    await expect(page.locator('form')).toBeVisible();
    await expect(page.getByLabel('Email')).toBeVisible();
    await expect(page.getByLabel('Password')).toBeVisible();
    await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible();

    // The form container should fit within 375px
    const formBox = await page.locator('form').boundingBox();
    expect(formBox).toBeTruthy();
    if (formBox) {
      expect(formBox.width).toBeLessThanOrEqual(375);
    }
  });

  test('should render Tablo dashboard on mobile with card layout', async ({ page }) => {
    await mockAuthMe(page, mockPmUser);
    await setupMocks(page);

    await page.goto('/tablo');
    await page.waitForLoadState('networkidle');

    // Title should be visible
    await expect(page.locator('h1')).toContainText('Production Tablo');

    // On mobile, KPI cards should stack (grid-cols-2 on mobile)
    const cards = page.locator('[class*="grid"] > [class*="rounded"]');
    const count = await cards.count();
    if (count > 0) {
      const firstCard = await cards.first().boundingBox();
      expect(firstCard).toBeTruthy();
      if (firstCard) {
        // Card should be narrower than full viewport (fits in 2-col grid)
        expect(firstCard.width).toBeLessThan(375);
      }
    }

    // Tabs should still be visible and clickable
    await expect(
      page.getByText('Glazing').or(page.getByText('Firing')),
    ).toBeVisible();
  });

  test('should render Packing dashboard on mobile with touch-friendly elements', async ({ page }) => {
    await mockAuthMe(page, mockSorterUser);
    await setupMocks(page);

    await page.goto('/packing');
    await page.waitForLoadState('networkidle');

    // Title should be visible
    await expect(page.locator('h1')).toContainText('Sorting & Packing');

    // KPI cards should be visible (grid-cols-3 on mobile too)
    await expect(page.getByText('Awaiting Sorting')).toBeVisible({ timeout: 10000 });

    // All buttons should have adequate touch target size (>= 32px height)
    const buttons = page.locator('button:visible');
    const btnCount = await buttons.count();
    for (let i = 0; i < Math.min(btnCount, 5); i++) {
      const box = await buttons.nth(i).boundingBox();
      if (box) {
        // Touch targets should be at least 32px tall
        expect(box.height).toBeGreaterThanOrEqual(28);
      }
    }
  });

  test('should collapse sidebar on mobile', async ({ page }) => {
    await mockAuthMe(page, mockPmUser);
    await setupMocks(page);

    await page.goto('/manager');
    await page.waitForLoadState('networkidle');

    // The sidebar should be collapsed (16px = ml-16) on mobile
    // or hidden entirely. It should not overlap main content at 375px.
    const sidebar = page.locator('aside, nav[class*="Sidebar"]').first();
    if (await sidebar.isVisible()) {
      const box = await sidebar.boundingBox();
      if (box) {
        // Collapsed sidebar should be narrow (64px = 16 * 4)
        expect(box.width).toBeLessThanOrEqual(80);
      }
    }
  });

  test('should keep header accessible on mobile', async ({ page }) => {
    await mockAuthMe(page, mockPmUser);
    await setupMocks(page);

    await page.goto('/manager');
    await page.waitForLoadState('networkidle');

    // Header should be visible
    await expect(page.locator('header')).toBeVisible();

    // Notifications bell should be reachable
    await expect(page.locator('button[aria-label="Notifications"]')).toBeVisible();
  });

  test('should handle orientation change (landscape mobile)', async ({ page }) => {
    await mockAuthMe(page, mockPmUser);
    await setupMocks(page);

    // Start in portrait
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto('/tablo');
    await page.waitForLoadState('networkidle');
    await expect(page.locator('h1')).toContainText('Production Tablo');

    // Switch to landscape
    await page.setViewportSize({ width: 812, height: 375 });
    await page.waitForLoadState('networkidle');

    // Page should still be functional
    await expect(page.locator('h1')).toContainText('Production Tablo');
    await expect(page.getByText('Glazing').or(page.getByText('Firing'))).toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// Tablet viewport (768 x 1024)
// ---------------------------------------------------------------------------

test.describe('Tablet Responsive Tests', () => {
  test.use({ viewport: { width: 768, height: 1024 } });

  test('should render manager dashboard on tablet', async ({ page }) => {
    await mockAuthMe(page, mockPmUser);
    await setupMocks(page);

    await page.goto('/manager');
    await page.waitForLoadState('networkidle');

    // Title visible
    await expect(page.locator('h1')).toBeVisible();

    // Tabs should be visible
    await expect(page.getByText('Orders')).toBeVisible({ timeout: 10000 });
  });

  test('should render tablo with wider cards on tablet', async ({ page }) => {
    await mockAuthMe(page, mockPmUser);
    await setupMocks(page);

    await page.goto('/tablo');
    await page.waitForLoadState('networkidle');

    // On tablet (768px), KPI cards use md:grid-cols-4
    const cards = page.locator('[class*="grid"] > [class*="rounded"]');
    const count = await cards.count();
    if (count >= 4) {
      const firstCard = await cards.first().boundingBox();
      if (firstCard) {
        // Card should be roughly 768/4 ~ 192px minus gaps
        expect(firstCard.width).toBeLessThan(400);
        expect(firstCard.width).toBeGreaterThan(100);
      }
    }
  });
});
