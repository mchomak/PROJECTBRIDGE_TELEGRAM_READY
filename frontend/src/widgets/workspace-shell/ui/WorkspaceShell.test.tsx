import { cleanup, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { afterEach, expect, test, vi } from 'vitest';
import type { User } from '../../../entities/user';
import { WorkspaceShell } from './WorkspaceShell';

const data = vi.hoisted(() => ({ role: 'executor' }));
vi.mock('../../../entities/project', () => ({
  useProject: () => ({ data: { name: 'Проект' } }),
  useProjectMembers: () => ({ data: [{ user_id: 'user', role: data.role }] }),
}));
vi.mock('../../../features/auth', () => ({ useLogout: () => ({ mutate: vi.fn() }) }));

const user: User = {
  id: 'user',
  email: 'test@example.com',
  first_name: '',
  last_name: '',
  email_verified: true,
  email_verified_at: null,
};
afterEach(() => {
  cleanup();
  data.role = 'executor';
});

test('project navigation respects the member role', () => {
  data.role = 'customer';
  render(
    <MemoryRouter initialEntries={['/app/projects/123/chat']}>
      <WorkspaceShell user={user}>Контент</WorkspaceShell>
    </MemoryRouter>,
  );
  expect(screen.getAllByRole('link', { name: 'Чат' })[0].getAttribute('href')).toBe(
    '/app/projects/123/chat',
  );
  expect(screen.queryByRole('link', { name: 'AI-анализ' })).toBeNull();
});

test('documents link waits for the asynchronous panel', async () => {
  const scroll = vi.fn();
  const { container } = render(
    <MemoryRouter initialEntries={['/app/projects/123#documents']}>
      <WorkspaceShell user={user}>Контент</WorkspaceShell>
    </MemoryRouter>,
  );
  const panel = document.createElement('section');
  panel.id = 'documents';
  panel.scrollIntoView = scroll;
  container.append(panel);
  await waitFor(() => expect(scroll).toHaveBeenCalledOnce());
  expect(screen.getAllByRole('link', { name: 'AI-анализ' })).toHaveLength(2);
});

test('documents is the current section instead of overview when the hash is selected', () => {
  render(
    <MemoryRouter initialEntries={['/app/projects/123#documents']}>
      <WorkspaceShell user={user}>Контент</WorkspaceShell>
    </MemoryRouter>,
  );
  expect(screen.getAllByRole('link', { name: 'Документы', current: 'page' })).toHaveLength(2);
  expect(screen.queryByRole('link', { name: 'Обзор', current: 'page' })).toBeNull();
});
