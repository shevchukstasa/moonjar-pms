import { type Page, type Route, expect } from '@playwright/test';

// ---------------------------------------------------------------------------
// Test credentials — override via E2E_PM_EMAIL / E2E_PM_PASSWORD etc.
// ---------------------------------------------------------------------------
export const users = {
  pm: {
    email: process.env.E2E_PM_EMAIL || 'pm@moonjar.test',
    password: process.env.E2E_PM_PASSWORD || 'test1234',
    role: 'production_manager',
    dashboardPath: '/manager',
  },
  admin: {
    email: process.env.E2E_ADMIN_EMAIL || 'admin@moonjar.test',
    password: process.env.E2E_ADMIN_PASSWORD || 'test1234',
    role: 'administrator',
    dashboardPath: '/admin',
  },
  sorter: {
    email: process.env.E2E_SORTER_EMAIL || 'sorter@moonjar.test',
    password: process.env.E2E_SORTER_PASSWORD || 'test1234',
    role: 'sorter_packer',
    dashboardPath: '/packing',
  },
  owner: {
    email: process.env.E2E_OWNER_EMAIL || 'owner@moonjar.test',
    password: process.env.E2E_OWNER_PASSWORD || 'test1234',
    role: 'owner',
    dashboardPath: '/owner',
  },
} as const;

export type UserKey = keyof typeof users;

// ---------------------------------------------------------------------------
// Login helper — fills the email/password form and submits
// ---------------------------------------------------------------------------
export async function login(page: Page, userKey: UserKey) {
  const u = users[userKey];
  await page.goto('/login');
  await page.waitForSelector('form');

  // The Input component renders <label>Email</label> + <input>
  await page.getByLabel('Email').fill(u.email);
  await page.getByLabel('Password').fill(u.password);
  await page.getByRole('button', { name: /sign in/i }).click();

  // Wait for navigation away from /login
  await page.waitForURL((url) => !url.pathname.includes('/login'), {
    timeout: 10000,
  });
}

// ---------------------------------------------------------------------------
// Navigation helpers
// ---------------------------------------------------------------------------
export async function navigateTo(page: Page, path: string) {
  await page.goto(path);
  await page.waitForLoadState('networkidle');
}

export async function waitForPageReady(page: Page) {
  // Wait until no spinner is visible
  await page.waitForFunction(() => {
    const spinners = document.querySelectorAll('[class*="animate-spin"]');
    return spinners.length === 0;
  }, { timeout: 15000 });
}

// ---------------------------------------------------------------------------
// Common selectors
// ---------------------------------------------------------------------------
export const selectors = {
  // Header
  header: 'header',
  notificationsButton: 'button[aria-label="Notifications"]',
  userAvatar: 'header img, header [class*="Avatar"]',

  // Login page
  loginForm: 'form',
  emailInput: 'input[type="email"]',
  passwordInput: 'input[type="password"]',
  signInButton: 'button[type="submit"]',
  loginError: '.text-red-500',
  googleLoginButton: '[data-testid="google-login"], iframe[src*="accounts.google"]',

  // Dashboard common
  pageTitle: 'h1',
  spinner: '[class*="animate-spin"]',
  tabsContainer: '[role="tablist"], nav',

  // Orders
  ordersTable: 'table',
  searchInput: 'input[type="search"], input[placeholder*="Search"], input[placeholder*="search"]',

  // Cards
  card: '[class*="rounded"][class*="bg-white"], [class*="Card"]',

  // Factory selector
  factorySelector: 'select, [class*="FactorySelector"]',

  // Error states
  errorBanner: '[class*="bg-red-50"], [class*="border-red"]',
} as const;

// ---------------------------------------------------------------------------
// API mock helpers — intercept backend calls for isolated tests
// ---------------------------------------------------------------------------

interface MockUser {
  id: string;
  email: string;
  name: string;
  role: string;
}

/**
 * Mock the /auth/login endpoint to return a fake user.
 * Useful when testing against a frontend without a running backend.
 */
export async function mockAuthLogin(page: Page, user: MockUser) {
  await page.route('**/api/auth/login', async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ user }),
    });
  });
}

/**
 * Mock the /auth/me endpoint (session restore) so the app
 * does not redirect to login before our test even starts.
 */
export async function mockAuthMe(page: Page, user: MockUser | null) {
  await page.route('**/api/auth/me', async (route: Route) => {
    if (user) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(user),
      });
    } else {
      await route.fulfill({ status: 401, body: '{"detail":"Not authenticated"}' });
    }
  });
}

/**
 * Mock the /auth/logout endpoint.
 */
export async function mockAuthLogout(page: Page) {
  await page.route('**/api/auth/logout', async (route: Route) => {
    await route.fulfill({ status: 200, body: '{"ok":true}' });
  });
}

/**
 * Generic API mock — fulfill any route with a JSON body.
 */
export async function mockApi(
  page: Page,
  urlPattern: string,
  body: unknown,
  status = 200,
) {
  await page.route(urlPattern, async (route: Route) => {
    await route.fulfill({
      status,
      contentType: 'application/json',
      body: JSON.stringify(body),
    });
  });
}

// ---------------------------------------------------------------------------
// Assertion helpers
// ---------------------------------------------------------------------------

export async function expectPageTitle(page: Page, text: string | RegExp) {
  const heading = page.locator('h1').first();
  await expect(heading).toBeVisible({ timeout: 10000 });
  if (typeof text === 'string') {
    await expect(heading).toContainText(text);
  } else {
    await expect(heading).toHaveText(text);
  }
}

export async function expectNoSpinners(page: Page) {
  await expect(page.locator(selectors.spinner)).toHaveCount(0, { timeout: 15000 });
}

export async function expectUrl(page: Page, path: string | RegExp) {
  if (typeof path === 'string') {
    await expect(page).toHaveURL(new RegExp(path.replace(/\//g, '\\/')));
  } else {
    await expect(page).toHaveURL(path);
  }
}
