import { serverMessages } from './serverMessages';

const messages: Record<string, string> = {
  ...serverMessages,
  'Request validation failed.': 'Проверьте введённые данные.',
  'An account with this email already exists.':
    'Аккаунт с таким адресом электронной почты уже существует.',
  'This answer is required.': 'Необходимо ответить на этот вопрос.',
  'A currency is required for the budget.': 'Укажите валюту бюджета.',
  'The document exceeds the 20 MiB upload limit.': 'Размер документа превышает допустимые 20 МиБ.',
  'Enter a three-letter currency code.': 'Введите трёхбуквенный код валюты.',
  'Enter a valid number.': 'Введите корректное число.',
  'Enter a value within the allowed range.': 'Введите значение в допустимом диапазоне.',
  'Enter a number with fewer digits.': 'Введите число с меньшим количеством цифр.',
  'Enter a number with fewer decimal places.':
    'Введите число с меньшим количеством знаков после запятой.',
  'Enter text.': 'Введите текст.',
  'Enter a longer answer.': 'Введите более длинный ответ.',
  'Enter a shorter answer.': 'Сократите ответ.',
  'Choose yes or no.': 'Выберите «Да» или «Нет».',
  'Choose an available option.': 'Выберите один из доступных вариантов.',
  'Enter a valid HTTP(S) address.': 'Введите корректный адрес HTTP или HTTPS.',
  'Enter a date in YYYY-MM-DD format.': 'Введите дату в формате ГГГГ-ММ-ДД.',
  'Enter a list of text values.': 'Введите список текстовых значений.',
  'Remove blank items from the list.': 'Удалите пустые элементы из списка.',
  'Remove some list items.': 'Сократите список.',
  'Clear integrations when the answer is no.':
    'Очистите список интеграций, если выбран ответ «Нет».',
  'List at least one integration.': 'Укажите хотя бы одну интеграцию.',
  'The minimum budget cannot exceed the maximum budget.':
    'Минимальный бюджет не может превышать максимальный.',
  'This field is required.': 'Это поле обязательно.',
  'This field may not be blank.': 'Это поле не может быть пустым.',
  'This field may not be null.': 'Это поле не может быть пустым.',
  'Enter a valid email address.': 'Введите корректный адрес электронной почты.',
  'Enter a valid URL.': 'Введите корректный адрес ссылки.',
  'Enter a valid date.': 'Введите корректную дату.',
  'A valid integer is required.': 'Введите целое число.',
  'A valid number is required.': 'Введите корректное число.',
  'The verification token is invalid or expired.':
    'Ссылка подтверждения недействительна или срок её действия истёк.',
  'Unable to log in with provided credentials.': 'Неверный адрес электронной почты или пароль.',
};

const statusMessages: Record<number, string> = {
  400: 'Проверьте введённые данные.',
  401: 'Не удалось войти. Проверьте данные или войдите снова.',
  403: 'У вас нет доступа к этому действию.',
  404: 'Запрошенные данные не найдены.',
  409: 'Данные изменились или действие сейчас недоступно. Обновите страницу и попробуйте снова.',
  429: 'Слишком много запросов. Попробуйте позже.',
};

export function apiErrorMessage(status: number, detail: unknown): string {
  if (typeof detail === 'string' && Object.hasOwn(messages, detail)) return messages[detail];
  return statusMessages[status] ?? 'Не удалось выполнить запрос. Попробуйте ещё раз.';
}

export function apiFieldErrorMessage(message: string): string {
  if (Object.hasOwn(messages, message)) return messages[message];
  const messageLimit = /^Message content must not exceed (\d+) characters\.$/.exec(message);
  if (messageLimit) return `Сообщение не должно превышать ${messageLimit[1]} символов.`;
  const markdownLimit = /^Markdown must be (\d+) characters or fewer\.$/.exec(message);
  if (markdownLimit) return `Текст не должен превышать ${markdownLimit[1]} символов.`;
  const maxLength = /^Ensure this field has no more than (\d+) characters\.$/.exec(message);
  if (maxLength) return `Допустимо не более ${maxLength[1]} символов.`;
  const minLength = /^Ensure this field has at least (\d+) characters\.$/.exec(message);
  if (minLength) return `Необходимо не менее ${minLength[1]} символов.`;
  return 'Проверьте значение этого поля.';
}
