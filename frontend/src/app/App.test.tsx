import { render, screen } from '@testing-library/react';
import { afterEach, expect, test } from 'vitest';

afterEach(() => {
  window.history.replaceState({}, '', '/');
});

test('the root route renders the minimal application shell', async () => {
  window.history.replaceState({}, '', '/');
  const appModule = await import('./App').catch(() => null);
  expect(appModule).not.toBeNull();
  if (!appModule) return;

  render(<appModule.App />);

  expect(screen.getByRole('main').textContent).toContain('ProjectBridge');
});

test('an unmatched route renders a not-found state', async () => {
  window.history.replaceState({}, '', '/unmatched-route');
  const appModule = await import('./App').catch(() => null);
  expect(appModule).not.toBeNull();
  if (!appModule) return;

  render(<appModule.App />);

  expect(screen.getByRole('heading', { name: 'Page not found' })).toBeTruthy();
});
