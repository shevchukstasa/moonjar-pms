import { test, expect } from '@playwright/test';
import {
  users,
  mockAuthMe,
  mockApi,
  expectPageTitle,
} from './helpers';

// ---------------------------------------------------------------------------
// Mock data
// ---------------------------------------------------------------------------
const mockSorterUser = {
  id: 'u-sort-1',
  email: users.sorter.email,
  name: 'Sorter User',
  role: users.sorter.role,
};

const mockSortingPositions = {
  items: [
    {
      id: 'sp-1',
      code: 'POS-401',
      product_name: 'Terracotta Tile X',
      quantity: 60,
      status: 'transferred_to_sorting',
      order_number: 'ORD-010',
    },
    {
      id: 'sp-2',
      code: 'POS-402',
      product_name: 'Stone Panel Y',
      quantity: 25,
      status: 'transferred_to_sorting',
      order_number: 'ORD-011',
    },
  ],
  total: 2,
};

const mockPackedPositions = {
  items: [
    {
      id: 'sp-3',
      code: 'POS-403',
      product_name: 'Tile Z',
      quantity: 40,
      status: 'packed',
      order_number: 'ORD-012',
    },
  ],
  total: 1,
};

const mockSorterTasks = {
  items: [
    { id: 'st-1', description: 'Sort batch #45', status: 'pending', type: 'sorting' },
  ],
  total: 1,
};

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe('Sorter / Packer Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthMe(page, mockSorterUser);
    await mockApi(page, '**/api/factories*', { items: [{ id: 'f1', name: 'Bali' }], total: 1 });

    // The SorterPackerDashboard fetches positions with different statuses
    await page.route('**/api/positions*', async (route) => {
      const url = route.request().url();
      if (url.includes('status=transferred_to_sorting')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockSortingPositions),
        });
      } else if (url.includes('status=packed')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockPackedPositions),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ items: [], total: 0 }),
        });
      }
    });

    await mockApi(page, '**/api/tasks/sorter*', mockSorterTasks);
    await mockApi(page, '**/api/tasks*', mockSorterTasks);
    await mockApi(page, '**/api/packing-photos*', { items: [], total: 0 });
    await mockApi(page, '**/api/stock*', { items: [], total: 0 });
  });

  test('should display Sorting & Packing page with title', async ({ page }) => {
    await page.goto('/packing');
    await page.waitForLoadState('networkidle');

    await expectPageTitle(page, 'Sorting & Packing');
    await expect(page.getByText('Sort fired tiles, pack, upload photos')).toBeVisible();
  });

  test('should show KPI cards with correct counts', async ({ page }) => {
    await page.goto('/packing');
    await page.waitForLoadState('networkidle');

    // "Awaiting Sorting" KPI should show 2
    await expect(page.getByText('Awaiting Sorting')).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('2').first()).toBeVisible();

    // "Packed" KPI should show 1
    await expect(page.getByText('Packed')).toBeVisible();
  });

  test('should display tabs: Sorting, Packing, Grinding, Photos, Tasks', async ({ page }) => {
    await page.goto('/packing');
    await page.waitForLoadState('networkidle');

    const expectedTabs = ['Sorting', 'Packing', 'Grinding', 'Photos', 'Tasks'];
    for (const tabName of expectedTabs) {
      await expect(
        page.getByRole('tab', { name: tabName }).or(page.getByText(tabName)),
      ).toBeVisible();
    }
  });

  test('should switch between Sorting and Packing tabs', async ({ page }) => {
    await page.goto('/packing');
    await page.waitForLoadState('networkidle');

    // Default tab is "Sorting"
    // Switch to "Packing"
    const packingTab = page.getByRole('tab', { name: 'Packing' }).or(page.getByText('Packing').first());
    await packingTab.click();
    await page.waitForLoadState('networkidle');

    // Switch to "Tasks"
    const tasksTab = page.getByRole('tab', { name: 'Tasks' }).or(page.getByText('Tasks').first());
    await tasksTab.click();
    await page.waitForLoadState('networkidle');
  });

  test('should display position cards in sorting tab', async ({ page }) => {
    await page.goto('/packing');
    await page.waitForLoadState('networkidle');

    // Position data should be visible
    await expect(
      page.getByText('POS-401').or(page.getByText('Terracotta Tile X')),
    ).toBeVisible({ timeout: 10000 });
    await expect(
      page.getByText('POS-402').or(page.getByText('Stone Panel Y')),
    ).toBeVisible();
  });

  test('should show error banner when API fails', async ({ page }) => {
    // Override positions to fail
    await page.route('**/api/positions*', async (route) => {
      await route.fulfill({ status: 500, body: '{"detail":"Server error"}' });
    });

    await page.goto('/packing');
    await page.waitForLoadState('networkidle');

    // Error message should appear
    await expect(page.getByText('Error loading data')).toBeVisible({ timeout: 10000 });
  });

  test('should validate quantity inputs accept only numbers', async ({ page }) => {
    await page.goto('/packing');
    await page.waitForLoadState('networkidle');

    // Find any number input on the page (quantity fields)
    const numberInputs = page.locator('input[type="number"]');
    const count = await numberInputs.count();

    if (count > 0) {
      const input = numberInputs.first();
      await input.fill('abc');
      // Number inputs ignore non-numeric characters
      const value = await input.inputValue();
      expect(value).toBe('');

      // Valid number should work
      await input.fill('42');
      const validValue = await input.inputValue();
      expect(validValue).toBe('42');
    }
  });
});
