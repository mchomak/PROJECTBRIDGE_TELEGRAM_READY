import { useMutation, useQueryClient } from '@tanstack/react-query';
import type { components } from '../../../shared/api/generated/schema';
import { apiJson } from '../../../shared/api';
import { currentUserQueryKey, type User } from '../../../entities/user';

type Credentials = components['schemas']['Credentials'];
type ResendVerificationRequest = components['schemas']['ResendVerificationRequest'];
type ResendVerificationResponse = components['schemas']['ResendVerificationResponse'];
type ConfirmVerificationRequest = components['schemas']['ConfirmVerificationRequest'];
type ConfirmVerificationResponse = components['schemas']['ConfirmVerificationResponse'];

function postJson<T>(path: string, body?: unknown): Promise<T> {
  return apiJson<T>(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
}

export function useLogin() {
  const queryClient = useQueryClient();

  return useMutation<User, Error, Credentials>({
    mutationFn: (credentials) => postJson('/api/v1/auth/login/', credentials),
    onSuccess: (user) => queryClient.setQueryData(currentUserQueryKey, user),
  });
}

export function useRegister() {
  return useMutation<User, Error, Credentials>({
    mutationFn: (credentials) => postJson('/api/v1/auth/register/', credentials),
  });
}

export function useLogout() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, void>({
    mutationFn: () => postJson('/api/v1/auth/logout/'),
    onSuccess: () => queryClient.removeQueries({ queryKey: currentUserQueryKey }),
  });
}

export function useResendVerification() {
  return useMutation<ResendVerificationResponse, Error, ResendVerificationRequest>({
    mutationFn: (request) => postJson('/api/v1/auth/email-verification/resend/', request),
  });
}

export function useConfirmVerification() {
  return useMutation<ConfirmVerificationResponse, Error, ConfirmVerificationRequest>({
    mutationFn: (request) => postJson('/api/v1/auth/email-verification/confirm/', request),
  });
}
