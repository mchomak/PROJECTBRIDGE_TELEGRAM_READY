const common: Record<string, string> = {
  goal: 'Какова главная цель проекта?',
  target_audience: 'Кто целевая аудитория?',
  expected_result: 'Какой результат должен дать проект?',
  has_integrations: 'Нужны ли интеграции с другими сервисами?',
  integrations: 'Какие сервисы нужно подключить?',
  constraints: 'Какие ограничения или требования нужно учесть?',
  deadline: 'К какой дате нужен результат?',
  budget_min: 'Какой минимальный бюджет?',
  budget_max: 'Какой максимальный бюджет?',
  currency: 'В какой валюте указан бюджет?',
};

const questions: Record<string, Record<string, string>> = {
  website: {
    functional_scope: 'Что пользователи смогут делать на сайте?',
    has_existing_site: 'Нужно обновить или заменить существующий сайт?',
    existing_site_url: 'Какой адрес существующего сайта?',
  },
  telegram_bot: {
    functional_scope: 'Что пользователи смогут делать в боте?',
    has_existing_bot: 'Нужно обновить или заменить существующего бота?',
    existing_bot_url: 'Какой адрес существующего бота?',
  },
  automation: {
    functional_scope: 'Что должна делать автоматизация?',
    trigger_type: 'Что запускает автоматизацию?',
    schedule_details: 'Как часто её нужно запускать?',
    event_source: 'Какое событие должно её запускать?',
  },
  other: {
    functional_scope: 'Что должен делать проект?',
    project_area: 'Какую область работы охватывает проект?',
  },
};

export function questionnaireQuestionLabel(
  schemaKey: string,
  version: number,
  questionKey: string,
  fallback: string,
): string {
  if (version !== 1 || !Object.hasOwn(questions, schemaKey)) return fallback;
  const schemaQuestions = questions[schemaKey];
  if (Object.hasOwn(schemaQuestions, questionKey)) return schemaQuestions[questionKey];
  return Object.hasOwn(common, questionKey) ? common[questionKey] : fallback;
}

export function questionnaireOptionLabel(
  schemaKey: string,
  version: number,
  questionKey: string,
  optionValue: string,
  fallback: string,
): string {
  if (schemaKey !== 'automation' || version !== 1 || questionKey !== 'trigger_type')
    return fallback;
  const options: Record<string, string> = {
    scheduled: 'По расписанию',
    event: 'При наступлении события',
    manual: 'Вручную',
  };
  return Object.hasOwn(options, optionValue) ? options[optionValue] : fallback;
}
