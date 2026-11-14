export const serverMessages: Record<string, string> = {
  'The file extension and detected content must be supported.':
    'Поддерживаются только файлы PDF, DOCX, TXT и Markdown; содержимое должно соответствовать расширению.',
  'Invalid email or password.': 'Неверный адрес электронной почты или пароль.',
  'Authentication is required.': 'Войдите в аккаунт, чтобы продолжить.',
  'Currency must contain exactly three ASCII letters.':
    'Код валюты должен содержать ровно три латинские буквы.',
  'The project passport was updated by another request.':
    'Паспорт проекта уже изменён. Обновите страницу и повторите действие.',
  'Documents can only be uploaded to draft or active projects.':
    'Документы можно загружать только в проекты в статусе черновика или активные проекты.',
  'The document lifecycle state does not allow this action.':
    'Текущее состояние документа не позволяет выполнить это действие.',
  'Document or lifecycle request not found.':
    'Документ или запрос на изменение его состояния не найден.',
  'Only the other active project member may decide.':
    'Решение может принять только второй активный участник проекта.',
  'A valid uploaded file is required.': 'Выберите файл для загрузки.',
  'The uploaded file could not be read.': 'Не удалось прочитать загруженный файл.',
  'Select a valid choice.': 'Выберите допустимый вариант.',
  'Enter a valid integer.': 'Введите целое число.',
  'Enter a positive integer.': 'Введите положительное целое число.',
  'Enter a valid page number.': 'Введите корректный номер страницы.',
  'Page size must be between 1 and 100.': 'Размер страницы должен быть от 1 до 100.',
  'Page size must be positive.': 'Размер страницы должен быть положительным.',
  'This invitation has expired.': 'Срок действия приглашения истёк.',
  'This invitation has been revoked.': 'Приглашение отозвано.',
  'This project no longer accepts invitations.': 'Этот проект больше не принимает приглашения.',
  'The invitation email was not delivered.': 'Не удалось отправить письмо с приглашением.',
  'Project invitation not found.': 'Приглашение в проект не найдено.',
  'Only the project executor can manage invitations.':
    'Управлять приглашениями может только исполнитель проекта.',
  'Invitation rate limit exceeded. Try again later.':
    'Слишком много запросов на приглашение. Попробуйте позже.',
  'The invitation cannot be changed in its current state.':
    'Приглашение нельзя изменить в текущем состоянии.',
  'You may request verification only for your email.':
    'Можно запросить подтверждение только своего адреса электронной почты.',
  'Email verification is required to create projects.':
    'Чтобы создать проект, подтвердите адрес электронной почты.',
  'Project metadata cannot be changed in its current state.':
    'Данные проекта нельзя изменить в текущем состоянии.',
  'The project cannot transition from its current state.':
    'Текущий статус проекта не позволяет выполнить это действие.',
  'The project passport cannot be changed in its current state.':
    'Паспорт проекта нельзя изменить в текущем состоянии.',
  'Project passport not found.': 'Паспорт проекта не найден.',
  'Only an executor can update project metadata.':
    'Изменять данные проекта может только исполнитель.',
  'Only an executor can change project status.':
    'Изменять статус проекта может только исполнитель.',
  'Only an executor can update the project passport.':
    'Изменять паспорт проекта может только исполнитель.',
  'At least one metadata field is required.': 'Укажите хотя бы одно поле проекта.',
  'At least one passport field is required.': 'Укажите хотя бы одно поле паспорта.',
  'A positive version is required.': 'Требуется положительный номер версии.',
  'Confirm the prefilled answers before submitting.':
    'Подтвердите предварительно заполненные ответы перед отправкой.',
  'The project passport changed after this questionnaire draft started.':
    'Паспорт проекта изменился после создания черновика анкеты.',
  'The project passport contains data that blocks this questionnaire mapping. Ask the executor to review the passport before trying again.':
    'Данные паспорта препятствуют переносу ответов. Попросите исполнителя проверить паспорт и повторите попытку.',
  'The questionnaire draft cannot be changed in its current state.':
    'Черновик анкеты нельзя изменить в текущем состоянии.',
  'This answer belongs to an inactive branch.': 'Этот ответ относится к неактивной ветке анкеты.',
  'This question is not part of the schema.': 'Этот вопрос отсутствует в схеме анкеты.',
  'At least one answer is required.': 'Укажите хотя бы один ответ.',
  'Choose an available conflict decision.': 'Выберите доступный способ разрешения конфликта.',
  'A positive passport version is required.': 'Требуется положительный номер версии паспорта.',
  'The questionnaire is unavailable to your account.': 'Анкета недоступна вашему аккаунту.',
  'You do not have permission for this questionnaire action.':
    'У вас нет доступа к этому действию с анкетой.',
  'The specification changed after it was loaded.':
    'Спецификация изменилась после загрузки. Обновите страницу.',
  'The specification changed or cannot be modified in its current state.':
    'Спецификация изменилась или недоступна для редактирования в текущем состоянии.',
  'Provide Markdown text.': 'Введите текст в формате Markdown.',
  'Provide the current specification version.': 'Укажите текущую версию спецификации.',
  'Only the project executor can generate or edit the specification.':
    'Создавать и редактировать спецификацию может только исполнитель проекта.',
  'The specification is unavailable to your account.': 'Спецификация недоступна вашему аккаунту.',
  'Enter a valid message.': 'Введите корректное сообщение.',
  'Message content cannot be blank.': 'Сообщение не может быть пустым.',
  'The message cursor is invalid.': 'Не удалось загрузить эту часть переписки. Обновите страницу.',
  'Chat send rate limit exceeded. Try again in the next minute.':
    'Слишком много сообщений. Попробуйте в следующую минуту.',
  'Project chat is unavailable to your account.': 'Чат проекта недоступен вашему аккаунту.',
  'The message ID or project state conflicts with this request.':
    'Идентификатор сообщения или состояние проекта не позволяет отправить сообщение.',
  'The Project State change conflicts with its current state.':
    'Текущее состояние проекта не позволяет выполнить изменение.',
  'Only the project executor can change Project State.':
    'Изменять состояние проекта может только исполнитель.',
  'Only the executor can select conflict evidence.':
    'Выбирать основания для конфликта может только исполнитель.',
  'The AI workspace action conflicts with the current state.':
    'Текущее состояние не позволяет выполнить действие с ИИ.',
  'Only the project executor can access the AI workspace.':
    'Рабочая область ИИ доступна только исполнителю проекта.',
  'This proposal type is unavailable.': 'Этот тип предложения недоступен.',
};
