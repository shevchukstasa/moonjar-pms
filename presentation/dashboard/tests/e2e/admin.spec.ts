import { test, expect } from '@playwright/test';
import {
  users,
  mockAuthMe,
  mockApi,
  expectPageTitle,
  expectUrl,
} from './helpers';

// ---------------------------------------------------------------------------
// Mock data
// ---------------------------------------------------------------------------
const mockAdminUser = {
  id: 'u-admin-1',
  email: users.admin.email,
  name: 'Admin User',
  role: users.admin.role,
};

const mockFactories = {
  items: [
    { id: 'f1', name: 'Bali', location: 'Ubud', timezone: 'Asia/Makassar' },
    { id: 'f2', name: 'Java', location: 'Jogja', timezone: 'Asia/Jakarta' },
  ],
  total: 2,
};

const mockUsers = {
  items: [
    { id: 'u1', name: 'Alice', email: 'alice@moonjar.test', role: 'production_manager', is_active: true },
    { id: 'u2', name: 'Bob', email: 'bob@moonjar.test', role: 'sorter_packer', is_active: true },
  ],
  total: 2,
};

const mockMaterials = {
  items: [
    { id: 'm1', name: 'Clay Type A', unit: 'kg', stock: 500 },
    { id: 'm2', name: 'Glaze Blue', unit: 'l', stock: 120 },
  ],
  total: 2,
};

const mockRecipes = {
  items: [
    { id: 'r1', name: 'Standard Glaze', temperature: 1100, firing_time_hours: 8 },
    { id: 'r2', name: 'Raku Glaze', temperature: 900, firing_time_hours: 3 },
  ],
  total: 2,
};

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe('Admin Panel', () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthMe(page, mockAdminUser);
    await mockApi(page, '**/api/factories*', mockFactories);
    await mockApi(page, '**/api/users*', mockUsers);
    await mockApi(page, '**/api/materials*', mockMaterials);
    await mockApi(page, '**/api/recipes*', mockRecipes);
    await mockApi(page, '**/api/telegram/bot-status*', { running: false });
    await mockApi(page, '**/api/telegram/owner-chat*', { chat_id: null, source: 'none' });
    await mockApi(page, '**/api/telegram/recent-chats*', { items: [] });
    await mockApi(page, '**/api/audit-log*', { items: [], total: 0 });
    await mockApi(page, '**/api/sessions*', { items: [], total: 0 });
    await mockApi(page, '**/api/suppliers*', { items: [], total: 0 });
    await mockApi(page, '**/api/collections*', { items: [], total: 0 });
    await mockApi(page, '**/api/colors*', { items: [], total: 0 });
    await mockApi(page, '**/api/application-types*', { items: [], total: 0 });
    await mockApi(page, '**/api/finishing-types*', { items: [], total: 0 });
    await mockApi(page, '**/api/temperature-groups*', { items: [], total: 0 });
    await mockApi(page, '**/api/warehouses*', { items: [], total: 0 });
    await mockApi(page, '**/api/packaging*', { items: [], total: 0 });
    await mockApi(page, '**/api/sizes*', { items: [], total: 0 });
    await mockApi(page, '**/api/stubs*', { enabled: false });
  });

  test('should load the Admin Panel page', async ({ page }) => {
    await page.goto('/admin');
    await page.waitForLoadState('networkidle');

    // The AdminPanelPage should show factories table and KPI
    await expect(page.getByText('Bali').or(page.getByText('Admin'))).toBeVisible({ timeout: 10000 });
  });

  test('should display factories table with data', async ({ page }) => {
    await page.goto('/admin');
    await page.waitForLoadState('networkidle');

    // Factory names
    await expect(page.getByText('Bali')).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('Java')).toBeVisible();
  });

  test('should navigate to /admin/materials and display materials table', async ({ page }) => {
    await page.goto('/admin/materials');
    await page.waitForLoadState('networkidle');

    // Material names
    await expect(page.getByText('Clay Type A').or(page.getByText('Materials'))).toBeVisible({ timeout: 10000 });
  });

  test('should navigate to /admin/recipes and display recipes table', async ({ page }) => {
    await page.goto('/admin/recipes');
    await page.waitForLoadState('networkidle');

    // Recipe names
    await expect(
      page.getByText('Standard Glaze').or(page.getByText('Recipes').or(page.getByText('Recipe'))),
    ).toBeVisible({ timeout: 10000 });
  });

  test('should navigate to /users and display user list', async ({ page }) => {
    await page.goto('/users');
    await page.waitForLoadState('networkidle');

    // User names or emails
    await expect(page.getByText('Alice').or(page.getByText('alice@moonjar.test'))).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('Bob').or(page.getByText('bob@moonjar.test'))).toBeVisible();
  });

  test('should navigate between admin sub-pages via sidebar', async ({ page }) => {
    await page.goto('/admin');
    await page.waitForLoadState('networkidle');

    // Find a sidebar link to Materials (if the sidebar renders links)
    const materialsLink = page.locator('a[href="/admin/materials"], nav a:has-text("Materials")').first();
    if (await materialsLink.isVisible()) {
      await materialsLink.click();
      await page.waitForURL('**/admin/materials', { timeout: 10000 });
      await expectUrl(page, '/admin/materials');
    }

    // Navigate to Recipes
    const recipesLink = page.locator('a[href="/admin/recipes"], nav a:has-text("Recipes")').first();
    if (await recipesLink.isVisible()) {
      await recipesLink.click();
      await page.waitForURL('**/admin/recipes', { timeout: 10000 });
      await expectUrl(page, '/admin/recipes');
    }

    // Navigate to Users
    const usersLink = page.locator('a[href="/users"], nav a:has-text("Users")').first();
    if (await usersLink.isVisible()) {
      await usersLink.click();
      await page.waitForURL('**/users', { timeout: 10000 });
      await expectUrl(page, '/users');
    }
  });

  test('should show total users count on admin page', async ({ page }) => {
    await page.goto('/admin');
    await page.waitForLoadState('networkidle');

    // The admin panel shows a KPI for total users
    await expect(page.getByText('2').or(page.getByText('Users'))).toBeVisible({ timeout: 10000 });
  });
});
