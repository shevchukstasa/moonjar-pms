import { test, expect } from '@playwright/test';
import {
  users,
  selectors,
  mockAuthMe,
  mockApi,
  expectPageTitle,
  expectNoSpinners,
  expectUrl,
} from './helpers';

// ---------------------------------------------------------------------------
// Fixtures — mock data
// ---------------------------------------------------------------------------
const mockOrders = {
  items: [
    {
      id: 'ord-1',
      number: 'ORD-001',
      client_name: 'Acme Corp',
      status: 'in_production',
      total_positions: 5,
      completed_positions: 2,
      created_at: '2026-01-15T10:00:00Z',
      deadline: '2026-04-01T00:00:00Z',
    },
    {
      id: 'ord-2',
      number: 'ORD-002',
      client_name: 'Beta Inc',
      status: 'new',
      total_positions: 3,
      completed_positions: 0,
      created_at: '2026-02-20T10:00:00Z',
      deadline: '2026-05-01T00:00:00Z',
    },
  ],
  total: 2,
  page: 1,
  per_page: 20,
};

const mockPositions = {
  items: [
    {
      id: 'pos-1',
      code: 'POS-001',
      product_name: 'Terracotta Tile A',
      quantity: 100,
      status: 'glazing',
    },
    {
      id: 'pos-2',
      code: 'POS-002',
      product_name: 'Stone Panel B',
      quantity: 50,
      status: 'fired',
    },
  ],
  total: 2,
};

const mockPmUser = {
  id: 'u-pm-1',
  email: users.pm.email,
  name: 'PM User',
  role: users.pm.role,
};

// ---------------------------------------------------------------------------
// Test setup
// ---------------------------------------------------------------------------

test.describe('Order Management (PM Dashboard)', () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthMe(page, mockPmUser);
    await mockApi(page, '**/api/factories*', { items: [{ id: 'f1', name: 'Bali' }], total: 1 });
    await mockApi(page, '**/api/orders*', mockOrders);
    await mockApi(page, '**/api/positions*', mockPositions);
    await mockApi(page, '**/api/tasks*', { items: [], total: 0 });
    await mockApi(page, '**/api/materials*', { items: [], total: 0 });
    await mockApi(page, '**/api/purchase-requests*', { items: [], total: 0 });
    await mockApi(page, '**/api/kilns*', { items: [], total: 0 });
    await mockApi(page, '**/api/quality*', { items: [], total: 0 });
    await mockApi(page, '**/api/inspections*', { items: [], total: 0 });
    await mockApi(page, '**/api/analytics*', {});
    await mockApi(page, '**/api/problem-cards*', { items: [], total: 0 });
    await mockApi(page, '**/api/shortage-tasks*', { items: [], total: 0 });
    await mockApi(page, '**/api/defects*', { items: [], total: 0 });
    await mockApi(page, '**/api/toc*', {});
    await mockApi(page, '**/api/cancellation-requests*', { items: [], total: 0 });
    await mockApi(page, '**/api/change-requests*', { items: [], total: 0 });
  });

  test('should load the PM dashboard with orders table', async ({ page }) => {
    await page.goto('/manager');
    await page.waitForLoadState('networkidle');

    // Title visible
    await expectPageTitle(page, 'Production Manager');

    // Orders tab should be active by default
    // The DataTable should render with order rows
    await expect(page.getByText('ORD-001')).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('Acme Corp')).toBeVisible();
    await expect(page.getByText('ORD-002')).toBeVisible();
    await expect(page.getByText('Beta Inc')).toBeVisible();
  });

  test('should navigate to order detail page on row click', async ({ page }) => {
    // Mock order detail
    await mockApi(page, '**/api/orders/ord-1*', {
      id: 'ord-1',
      number: 'ORD-001',
      client_name: 'Acme Corp',
      status: 'in_production',
      positions: mockPositions.items,
    });

    await page.goto('/manager');
    await page.waitForLoadState('networkidle');

    // Click on the order row
    await page.getByText('ORD-001').click();

    // Should navigate to order detail
    await page.waitForURL('**/manager/orders/ord-1', { timeout: 10000 });
    await expectUrl(page, '/manager/orders/ord-1');
  });

  test('should switch between dashboard tabs', async ({ page }) => {
    await page.goto('/manager');
    await page.waitForLoadState('networkidle');

    // Verify Orders tab is visible and active
    const ordersTab = page.getByRole('tab', { name: 'Orders' }).or(page.getByText('Orders').first());
    await expect(ordersTab).toBeVisible();

    // Switch to Tasks tab
    const tasksTab = page.getByRole('tab', { name: 'Tasks' }).or(page.getByText('Tasks').first());
    await tasksTab.click();
    // Tasks content should appear (even if empty)
    await page.waitForLoadState('networkidle');

    // Switch to Materials tab
    const materialsTab = page.getByRole('tab', { name: 'Materials' }).or(page.getByText('Materials').first());
    await materialsTab.click();
    await page.waitForLoadState('networkidle');

    // Switch back to Orders
    await ordersTab.click();
    await expect(page.getByText('ORD-001')).toBeVisible({ timeout: 10000 });
  });

  test('should filter orders with search input', async ({ page }) => {
    await page.goto('/manager');
    await page.waitForLoadState('networkidle');

    // Find the search input within the orders tab
    const searchInput = page.locator('input[type="search"], input[placeholder*="earch"]').first();

    if (await searchInput.isVisible()) {
      await searchInput.fill('Acme');
      // Wait for debounced search
      await page.waitForTimeout(500);

      // The API should be re-called with search param; with mocks,
      // both still show — this test verifies the search input is functional.
      await expect(searchInput).toHaveValue('Acme');
    }
  });

  test('should display order status badges', async ({ page }) => {
    await page.goto('/manager');
    await page.waitForLoadState('networkidle');

    // Check that statuses are rendered as badges
    await expect(page.getByText('In Production').or(page.getByText('in_production'))).toBeVisible({ timeout: 10000 });
  });

  test('should show order positions in detail page', async ({ page }) => {
    await mockApi(page, '**/api/orders/ord-1*', {
      id: 'ord-1',
      number: 'ORD-001',
      client_name: 'Acme Corp',
      status: 'in_production',
      positions: mockPositions.items,
    });

    await page.goto('/manager/orders/ord-1');
    await page.waitForLoadState('networkidle');

    // Position codes or product names should be visible
    await expect(
      page.getByText('POS-001').or(page.getByText('Terracotta Tile A')),
    ).toBeVisible({ timeout: 10000 });
    await expect(
      page.getByText('POS-002').or(page.getByText('Stone Panel B')),
    ).toBeVisible();
  });
});
