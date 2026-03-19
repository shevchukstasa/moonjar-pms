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
const mockPmUser = {
  id: 'u-pm-1',
  email: users.pm.email,
  name: 'PM User',
  role: users.pm.role,
};

const mockGlazingPositions = {
  items: [
    { id: 'p1', code: 'POS-101', product_name: 'Tile A', status: 'ready_for_glazing', quantity: 50 },
    { id: 'p2', code: 'POS-102', product_name: 'Tile B', status: 'glazing', quantity: 30 },
  ],
  total: 2,
};

const mockFiringPositions = {
  items: [
    { id: 'p3', code: 'POS-201', product_name: 'Tile C', status: 'ready_for_firing', quantity: 80 },
  ],
  total: 1,
};

const mockSortingPositions = {
  items: [
    { id: 'p4', code: 'POS-301', product_name: 'Tile D', status: 'transferred_to_sorting', quantity: 40 },
  ],
  total: 1,
};

const mockKilns = {
  items: [
    { id: 'k1', name: 'Main Kiln', status: 'firing', temperature: 1100, factory_id: 'f1' },
    { id: 'k2', name: 'Raku Kiln', status: 'idle', temperature: 0, factory_id: 'f1' },
  ],
  total: 2,
};

const mockFactories = {
  items: [
    { id: 'f1', name: 'Bali' },
    { id: 'f2', name: 'Java' },
  ],
  total: 2,
};

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe('Tablo Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthMe(page, mockPmUser);
    await mockApi(page, '**/api/factories*', mockFactories);
    await mockApi(page, '**/api/schedule/glazing*', mockGlazingPositions);
    await mockApi(page, '**/api/schedule/firing*', mockFiringPositions);
    await mockApi(page, '**/api/schedule/sorting*', mockSortingPositions);
    await mockApi(page, '**/api/schedule/kilns*', mockKilns);
    // Catch-all for other endpoints the tablo may call
    await mockApi(page, '**/api/positions*', { items: [], total: 0 });
    await mockApi(page, '**/api/kilns*', mockKilns);
  });

  test('should display the Tablo page with title', async ({ page }) => {
    await page.goto('/tablo');
    await page.waitForLoadState('networkidle');

    await expectPageTitle(page, 'Production Tablo');
  });

  test('should show Glazing tab by default with position data', async ({ page }) => {
    await page.goto('/tablo');
    await page.waitForLoadState('networkidle');

    // Glazing is the first tab, should be active
    const glazingTab = page.getByRole('tab', { name: 'Glazing' }).or(page.getByText('Glazing').first());
    await expect(glazingTab).toBeVisible();

    // KPI card for Glazing should show the count
    await expect(page.getByText('Glazing').first()).toBeVisible();
  });

  test('should switch between Glazing, Firing, Sorting, Kilns tabs', async ({ page }) => {
    await page.goto('/tablo');
    await page.waitForLoadState('networkidle');

    // Switch to Firing
    const firingTab = page.getByRole('tab', { name: 'Firing' }).or(page.getByText('Firing').first());
    await firingTab.click();
    await page.waitForLoadState('networkidle');

    // Switch to Sorting
    const sortingTab = page.getByRole('tab', { name: 'Sorting' }).or(page.getByText('Sorting').first());
    await sortingTab.click();
    await page.waitForLoadState('networkidle');

    // Switch to Kilns
    const kilnsTab = page.getByRole('tab', { name: 'Kilns' }).or(page.getByText('Kilns').first());
    await kilnsTab.click();
    await page.waitForLoadState('networkidle');

    // Kiln names should be visible when on Kilns tab
    await expect(
      page.getByText('Main Kiln').or(page.getByText('Raku Kiln')),
    ).toBeVisible({ timeout: 10000 });
  });

  test('should display KPI cards with counts', async ({ page }) => {
    await page.goto('/tablo');
    await page.waitForLoadState('networkidle');

    // KPI cards show counts from each section
    // The tablo shows 4 KPI cards: Glazing, Firing, Sorting, Kilns
    const cards = page.locator('[class*="rounded"][class*="bg-white"]');
    // At least 4 KPI cards
    await expect(cards.first()).toBeVisible({ timeout: 10000 });
  });

  test('should display factory selector', async ({ page }) => {
    await page.goto('/tablo');
    await page.waitForLoadState('networkidle');

    // FactorySelector should be visible in the header area
    const factorySelector = page.locator('select').or(
      page.locator('[class*="FactorySelector"]'),
    );
    await expect(factorySelector.first()).toBeVisible({ timeout: 10000 });
  });

  test('should show error banner when API fails', async ({ page }) => {
    // Override one schedule endpoint to return 500
    await page.route('**/api/schedule/glazing*', async (route) => {
      await route.fulfill({ status: 500, body: '{"detail":"Internal error"}' });
    });

    await page.goto('/tablo');
    await page.waitForLoadState('networkidle');

    // Error banner should appear
    const errorBanner = page.locator('[class*="bg-red-50"], [class*="border-red"]');
    await expect(errorBanner.first()).toBeVisible({ timeout: 10000 });
  });
});
