import { test, expect } from '@playwright/test';
import {
  login,
  users,
  selectors,
  mockAuthLogin,
  mockAuthMe,
  mockAuthLogout,
  mockApi,
  expectUrl,
} from './helpers';

test.describe('Authentication Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Ensure the app does NOT restore a session before our login test
    await mockAuthMe(page, null);
  });

  test('should display the login page correctly', async ({ page }) => {
    await page.goto('/login');

    // Heading
    await expect(page.locator('h1')).toContainText('Moonjar PMS');
    await expect(page.getByText('Production Management System')).toBeVisible();

    // Form elements
    await expect(page.getByLabel('Email')).toBeVisible();
    await expect(page.getByLabel('Password')).toBeVisible();
    await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible();

    // Google button / divider
    await expect(page.getByText('or')).toBeVisible();
  });

  test('should login with valid credentials and redirect to dashboard', async ({ page }) => {
    const mockUser = {
      id: 'u-pm-1',
      email: users.pm.email,
      name: 'Test PM',
      role: users.pm.role,
    };

    await mockAuthLogin(page, mockUser);
    // After login, the app calls /auth/me — mock it to return the user
    // so RequireAuth allows through.
    // Note: login() in helper fills the form and clicks submit.
    // We also need factories and other initial data the dashboard fetches.
    await mockApi(page, '**/api/factories*', { items: [], total: 0 });
    await mockApi(page, '**/api/orders*', { items: [], total: 0 });
    await mockApi(page, '**/api/positions*', { items: [], total: 0 });
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

    await page.goto('/login');
    await page.waitForSelector('form');

    await page.getByLabel('Email').fill(mockUser.email);
    await page.getByLabel('Password').fill('test1234');
    await page.getByRole('button', { name: /sign in/i }).click();

    // Should redirect to /manager for production_manager
    await page.waitForURL('**/manager', { timeout: 10000 });
    await expectUrl(page, '/manager');
  });

  test('should show error message for invalid credentials', async ({ page }) => {
    // Mock a 401 from the login endpoint
    await page.route('**/api/auth/login', async (route) => {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Invalid email or password' }),
      });
    });

    await page.goto('/login');
    await page.waitForSelector('form');

    await page.getByLabel('Email').fill('bad@example.com');
    await page.getByLabel('Password').fill('wrongpassword');
    await page.getByRole('button', { name: /sign in/i }).click();

    // Error message should appear
    const errorMsg = page.locator(selectors.loginError);
    await expect(errorMsg).toBeVisible({ timeout: 5000 });
    await expect(errorMsg).toContainText('Invalid email or password');

    // Should remain on login page
    await expectUrl(page, '/login');
  });

  test('should disable submit button while loading', async ({ page }) => {
    // Delay the response so we can check the loading state
    await page.route('**/api/auth/login', async (route) => {
      await new Promise((r) => setTimeout(r, 2000));
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          user: { id: '1', email: 'a@b.com', name: 'Test', role: 'production_manager' },
        }),
      });
    });

    await page.goto('/login');
    await page.waitForSelector('form');

    await page.getByLabel('Email').fill('a@b.com');
    await page.getByLabel('Password').fill('test1234');
    await page.getByRole('button', { name: /sign in/i }).click();

    // Button should show "Signing in..." and be disabled
    const btn = page.getByRole('button', { name: /signing in/i });
    await expect(btn).toBeVisible();
    await expect(btn).toBeDisabled();
  });

  test('should logout and redirect to login page', async ({ page }) => {
    const mockUser = {
      id: 'u-pm-1',
      email: users.pm.email,
      name: 'Test PM',
      role: users.pm.role,
    };

    // Simulate an authenticated session
    await mockAuthMe(page, mockUser);
    await mockAuthLogout(page);
    await mockApi(page, '**/api/factories*', { items: [], total: 0 });
    await mockApi(page, '**/api/orders*', { items: [], total: 0 });
    await mockApi(page, '**/api/positions*', { items: [], total: 0 });
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

    await page.goto('/manager');
    await page.waitForLoadState('networkidle');

    // Open the user dropdown (click the avatar in the header)
    const avatar = page.locator('header').locator('[class*="cursor-pointer"]').first();
    await avatar.click();

    // Click Logout
    const logoutItem = page.getByText('Logout');
    await expect(logoutItem).toBeVisible();
    await logoutItem.click();

    // Should redirect to /login
    await page.waitForURL('**/login', { timeout: 10000 });
    await expectUrl(page, '/login');
  });

  test('should redirect unauthenticated user to /login', async ({ page }) => {
    await page.goto('/manager');

    // RequireAuth should redirect to /login
    await page.waitForURL('**/login', { timeout: 10000 });
    await expectUrl(page, '/login');
  });
});
