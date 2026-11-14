import { expect, test } from 'vitest';
import { projectStatusLabels, projectTypeOptions } from '../../entities/project/model/types';
import { ApiError, getApiFieldErrors } from '../api';
import { questionnaireOptionLabel, questionnaireQuestionLabel } from './questionnaire';

test('localizes known schema labels by version and stable keys without changing unknown labels', () => {
  expect(questionnaireQuestionLabel('website', 1, 'functional_scope', 'original')).toBe(
    'Что пользователи смогут делать на сайте?',
  );
  expect(questionnaireQuestionLabel('automation', 1, 'functional_scope', 'original')).toBe(
    'Что должна делать автоматизация?',
  );
  expect(questionnaireOptionLabel('automation', 1, 'trigger_type', 'scheduled', 'original')).toBe(
    'По расписанию',
  );
  expect(questionnaireQuestionLabel('website', 2, 'goal', 'Future label')).toBe('Future label');
  expect(questionnaireOptionLabel('automation', 1, 'trigger_type', 'future', 'Future option')).toBe(
    'Future option',
  );
});

test('preserves actionable server validation details in Russian', () => {
  const payload = {
    code: 'validation_error',
    detail: 'Request validation failed.',
    errors: {
      currency: ['Enter a three-letter currency code.'],
      email: ['An account with this email already exists.'],
    },
    request_id: 'id',
  };
  const error = new ApiError(400, payload);
  expect(getApiFieldErrors(error)).toEqual({
    currency: ['Введите трёхбуквенный код валюты.'],
    email: ['Аккаунт с таким адресом электронной почты уже существует.'],
  });
  expect(error.payload).toEqual(payload);
  expect(
    new ApiError(413, { ...payload, detail: 'The document exceeds the 20 MiB upload limit.' })
      .message,
  ).toBe('Размер документа превышает допустимые 20 МиБ.');
});

test('explains supported documents and specific authorization and validation failures', () => {
  const payload = { code: 'request_failed', detail: '', errors: null, request_id: 'id' };
  expect(
    new ApiError(415, {
      ...payload,
      detail: 'The file extension and detected content must be supported.',
    }).message,
  ).toBe(
    'Поддерживаются только файлы PDF, DOCX, TXT и Markdown; содержимое должно соответствовать расширению.',
  );
  expect(new ApiError(401, { ...payload, detail: 'Invalid email or password.' }).message).toBe(
    'Неверный адрес электронной почты или пароль.',
  );
  expect(
    new ApiError(409, {
      ...payload,
      detail: 'The project passport was updated by another request.',
    }).message,
  ).toBe('Паспорт проекта уже изменён. Обновите страницу и повторите действие.');
  const error = new ApiError(400, {
    ...payload,
    errors: { currency: ['Currency must contain exactly three ASCII letters.'] },
  });
  expect(getApiFieldErrors(error).currency).toEqual([
    'Код валюты должен содержать ровно три латинские буквы.',
  ]);
});

test('project types and statuses have readable Russian labels', () => {
  expect(projectTypeOptions.map(({ label }) => label)).toEqual([
    'Сайт',
    'Telegram-бот',
    'Автоматизация',
    'Другое',
  ]);
  expect(projectStatusLabels).toEqual({
    draft: 'Черновик',
    active: 'Активен',
    completed: 'Завершён',
    archived: 'В архиве',
  });
});

test('preserves numeric validation limits without displaying arbitrary server text', () => {
  const payload = {
    code: 'validation_error',
    detail: 'Request validation failed.',
    request_id: 'id',
    errors: {
      content: ['Message content must not exceed 4000 characters.'],
      name: ['Ensure this field has no more than 100 characters.'],
      other: ['Unexpected internal data'],
    },
  };
  expect(getApiFieldErrors(new ApiError(400, payload))).toEqual({
    content: ['Сообщение не должно превышать 4000 символов.'],
    name: ['Допустимо не более 100 символов.'],
    other: ['Проверьте значение этого поля.'],
  });
});

test('localizes API errors without changing the server payload and hides unknown server messages', () => {
  const payload = {
    code: 'validation_error',
    detail: 'Request validation failed.',
    errors: { email: ['Enter a valid email address.'], title: ['server secret'] },
    request_id: 'id',
  };
  const error = new ApiError(400, payload);
  expect(error.message).toBe('Проверьте введённые данные.');
  expect(getApiFieldErrors(error)).toEqual({
    email: ['Введите корректный адрес электронной почты.'],
    title: ['Проверьте значение этого поля.'],
  });
  expect(error.payload).toEqual(payload);
  expect(new ApiError(500, { ...payload, detail: 'secret' }).message).toBe(
    'Не удалось выполнить запрос. Попробуйте ещё раз.',
  );
});
