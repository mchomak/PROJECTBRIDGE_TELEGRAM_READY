import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react';
import { Link, useOutletContext, useParams } from 'react-router';
import {
  projectStatusLabels,
  useProject,
  useProjectMembers,
  type ProjectMember,
} from '../../../entities/project';
import {
  useProjectMessages,
  type ChatMessage,
  type ChatMessageCreate,
} from '../../../entities/chat';
import { useSendProjectMessage } from '../../../features/chat';
import type { User } from '../../../entities/user';
import { ApiError } from '../../../shared/api';

type DeliveryState = 'sending' | 'sent' | 'failed';
type ChatEntry = ChatMessage & {
  delivery_state: DeliveryState;
  delivery_error?: string;
};

function createClientMessageId(): string {
  return crypto.randomUUID();
}

function senderLabel(message: ChatMessage, members: ProjectMember[], currentUserId: string) {
  if (message.sender_id === currentUserId) return 'Вы';
  const sender = members.find((member) => member.user_id === message.sender_id);
  const name = [sender?.first_name, sender?.last_name].filter(Boolean).join(' ');
  return name || 'Участник проекта';
}

function messageTime(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

function messageFromEvent(data: string, projectId: string): ChatMessage | null {
  try {
    const event: unknown = JSON.parse(data);
    if (typeof event !== 'object' || event === null) return null;
    const envelope = event as { type?: unknown; message?: ChatMessage };
    if (
      envelope.type !== 'message.created' ||
      !envelope.message ||
      envelope.message.project_id !== projectId ||
      typeof envelope.message.id !== 'string'
    ) {
      return null;
    }
    return envelope.message;
  } catch {
    return null;
  }
}

export function ChatPage() {
  const { projectId = '' } = useParams();
  return <ProjectChat key={projectId} projectId={projectId} />;
}

function ProjectChat({ projectId }: { projectId: string }) {
  const user = useOutletContext<User>();
  const projectQuery = useProject(projectId);
  const membersQuery = useProjectMembers(projectId);
  const historyQuery = useProjectMessages(projectId);
  const sendMessage = useSendProjectMessage(projectId);
  const [draft, setDraft] = useState('');
  const draftRevision = useRef(0);
  const pendingDraftRevisions = useRef(new Map<string, number>());
  const [localMessages, setLocalMessages] = useState<ChatEntry[]>([]);

  const project = projectQuery.data;
  const members = membersQuery.data ?? [];
  const currentMember = members.find((member) => member.user_id === user.id);
  const hasActiveMembership = Boolean(currentMember);
  const historyRefetch = useRef(historyQuery.refetch);
  historyRefetch.current = historyQuery.refetch;
  const canSend = project?.status === 'active';

  const confirmDraft = useCallback((clientMessageId: string) => {
    const revision = pendingDraftRevisions.current.get(clientMessageId);
    if (revision === undefined) return;
    pendingDraftRevisions.current.delete(clientMessageId);
    if (revision === draftRevision.current) setDraft('');
  }, []);

  useEffect(() => {
    for (const page of historyQuery.data?.pages ?? []) {
      for (const message of page.results) {
        if (message.sender_id === user.id) confirmDraft(message.client_message_id);
      }
    }
  }, [historyQuery.data, user.id, confirmDraft]);

  useEffect(() => {
    if (!projectId || !hasActiveMembership) return;

    let disposed = false;
    let reconnectTimer: ReturnType<typeof setTimeout> | undefined;
    let reconnectDelay = 250;
    let socket: WebSocket | undefined;

    function connect() {
      if (disposed) return;
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const nextSocket = new WebSocket(
        `${protocol}//${window.location.host}/ws/v1/projects/${encodeURIComponent(projectId)}/chat/`,
      );
      socket = nextSocket;
      nextSocket.onopen = () => {
        void historyRefetch.current();
        reconnectDelay = 250;
      };
      nextSocket.onmessage = (event) => {
        const message = messageFromEvent(event.data, projectId);
        if (!message) return;
        if (message.sender_id === user.id) confirmDraft(message.client_message_id);
        setLocalMessages((current) => {
          const existingIndex = current.findIndex(
            (entry) =>
              entry.id === message.id ||
              (entry.sender_id === message.sender_id &&
                entry.client_message_id === message.client_message_id),
          );
          const delivered: ChatEntry = { ...message, delivery_state: 'sent' };
          if (existingIndex === -1) return [...current, delivered];
          return current.map((entry, index) => (index === existingIndex ? delivered : entry));
        });
      };
      nextSocket.onclose = (event) => {
        if (disposed || event.code === 4401 || event.code === 4403) return;
        reconnectTimer = setTimeout(connect, reconnectDelay);
        reconnectDelay = Math.min(reconnectDelay * 2, 5000);
      };
      nextSocket.onerror = () => nextSocket.close();
    }

    connect();
    return () => {
      disposed = true;
      if (reconnectTimer !== undefined) clearTimeout(reconnectTimer);
      socket?.close();
    };
  }, [hasActiveMembership, projectId, user.id, confirmDraft]);

  function retryPage() {
    void Promise.all([projectQuery.refetch(), membersQuery.refetch(), historyQuery.refetch()]);
  }

  async function deliverMessage(content: string, existingClientMessageId?: string) {
    if (!canSend || sendMessage.isPending) return;
    const clientMessageId = existingClientMessageId ?? createClientMessageId();
    const payload: ChatMessageCreate = {
      client_message_id: clientMessageId,
      content,
    };
    const timestamp = new Date().toISOString();
    if (!pendingDraftRevisions.current.has(clientMessageId)) {
      pendingDraftRevisions.current.set(clientMessageId, draftRevision.current);
    }

    setLocalMessages((current) => {
      const existing = current.find(
        (message) => message.sender_id === user.id && message.client_message_id === clientMessageId,
      );
      const pending: ChatEntry = {
        id: existing?.id ?? `pending:${clientMessageId}`,
        project_id: projectId,
        sender_id: user.id,
        content,
        message_type: 'text',
        client_message_id: clientMessageId,
        created_at: existing?.created_at ?? timestamp,
        updated_at: null,
        delivery_state: 'sending',
      };
      return existing
        ? current.map((message) =>
            message.sender_id === user.id && message.client_message_id === clientMessageId
              ? pending
              : message,
          )
        : [...current, pending];
    });
    try {
      const saved = await sendMessage.mutateAsync(payload);
      setLocalMessages((current) =>
        current.map((message) =>
          message.sender_id === user.id && message.client_message_id === clientMessageId
            ? { ...saved, delivery_state: 'sent' }
            : message,
        ),
      );
      confirmDraft(clientMessageId);
    } catch (error) {
      setLocalMessages((current) =>
        current.map((message) =>
          message.sender_id === user.id &&
          message.client_message_id === clientMessageId &&
          message.delivery_state !== 'sent'
            ? {
                ...message,
                delivery_state: 'failed',
                delivery_error:
                  error instanceof Error
                    ? error.message
                    : 'Не удалось отправить сообщение. Попробуйте снова.',
              }
            : message,
        ),
      );
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const content = draft.trim();
    if (!content) return;
    void deliverMessage(content);
  }

  if (projectQuery.isError || membersQuery.isError || historyQuery.isError) {
    const error = projectQuery.error ?? membersQuery.error ?? historyQuery.error;
    return (
      <main className="workspace-page workspace-page--narrow">
        <Link className="back-link" to={`/app/projects/${projectId}`}>
          ← К проекту
        </Link>
        <section className="state-message state-message--error" aria-labelledby="chat-error-title">
          <h1 id="chat-error-title">Не удалось открыть чат</h1>
          <p>
            {error instanceof ApiError && error.status === 404
              ? 'Чат проекта недоступен вашему аккаунту.'
              : error?.message || 'Проверьте подключение и попробуйте снова.'}
          </p>
          <button className="button button--secondary" onClick={retryPage} type="button">
            Попробовать снова
          </button>
        </section>
      </main>
    );
  }

  if (projectQuery.isPending || membersQuery.isPending || historyQuery.isPending || !project) {
    return (
      <main className="workspace-page">
        <p className="state-message" role="status">
          Загрузка чата проекта…
        </p>
      </main>
    );
  }

  if (!currentMember) {
    return (
      <main className="workspace-page workspace-page--narrow">
        <section className="state-message state-message--error" role="alert">
          <h1>Нет доступа к чату проекта</h1>
          <p>Не удалось подтвердить ваше участие в проекте.</p>
          <Link className="button button--secondary" to="/app/projects">
            К проектам
          </Link>
        </section>
      </main>
    );
  }

  const serverMessages = historyQuery.data.pages.flatMap((page) => page.results);
  const entriesById = new Map<string, ChatEntry>();
  for (const message of serverMessages) {
    entriesById.set(message.id, { ...message, delivery_state: 'sent' });
  }
  for (const localMessage of localMessages) {
    const savedMessage = serverMessages.find(
      (message) =>
        message.sender_id === localMessage.sender_id &&
        message.client_message_id === localMessage.client_message_id,
    );
    entriesById.set(
      savedMessage?.id ?? localMessage.id,
      savedMessage ? { ...savedMessage, delivery_state: 'sent' } : localMessage,
    );
  }
  const messages = [...entriesById.values()].sort((first, second) => {
    const timeDifference = Date.parse(first.created_at) - Date.parse(second.created_at);
    return timeDifference || first.id.localeCompare(second.id);
  });

  return (
    <main className="workspace-page workspace-page--chat">
      <Link className="back-link" to={`/app/projects/${project.id}`}>
        ← Назад к {project.name}
      </Link>
      <div className="page-heading chat-heading">
        <div>
          <p className="project-overview-heading__type">Чат проекта</p>
          <h1>{project.name}</h1>
          <p className="page-heading__description">
            Сообщения доступны всем активным участникам проекта.
          </p>
        </div>
        <span className={`status-badge status-badge--large status-badge--${project.status}`}>
          {projectStatusLabels[project.status]}
        </span>
      </div>

      <section className="project-panel chat-panel" aria-labelledby="chat-title">
        <div className="section-heading">
          <div>
            <h2 id="chat-title">Обсуждение</h2>
            <p className="section-heading__description">
              Ваша роль в чате: {currentMember.role === 'executor' ? 'исполнитель' : 'заказчик'}.
            </p>
          </div>
        </div>

        {historyQuery.hasNextPage && (
          <div className="chat-history-actions">
            <button
              className="button button--secondary"
              disabled={historyQuery.isFetchingNextPage}
              onClick={() => void historyQuery.fetchNextPage()}
              type="button"
            >
              {historyQuery.isFetchingNextPage
                ? 'Загрузка предыдущих сообщений…'
                : 'Загрузить предыдущие сообщения'}
            </button>
          </div>
        )}

        {messages.length === 0 ? (
          <div className="empty-state chat-empty-state">
            <h2>Сообщений пока нет</h2>
            <p>Начните обсуждение с другим участником проекта.</p>
          </div>
        ) : (
          <ol className="chat-messages" aria-label="Сообщения проекта">
            {messages.map((message) => (
              <li
                className={`chat-message${message.sender_id === user.id ? ' chat-message--own' : ''}`}
                key={message.id}
              >
                <article className="chat-message__bubble">
                  <header className="chat-message__meta">
                    <strong>{senderLabel(message, members, user.id)}</strong>
                    <time dateTime={message.created_at}>{messageTime(message.created_at)}</time>
                  </header>
                  <p className="chat-message__content">{message.content}</p>
                  <div
                    className={`chat-message__delivery chat-message__delivery--${message.delivery_state}`}
                  >
                    {message.delivery_state === 'sending' && <span role="status">Отправка…</span>}
                    {message.delivery_state === 'sent' && <span>Отправлено</span>}
                    {message.delivery_state === 'failed' && (
                      <div>
                        <span role="alert">
                          {message.delivery_error || 'Не удалось отправить сообщение.'}
                        </span>
                        <button
                          className="button button--quiet"
                          disabled={sendMessage.isPending || !canSend}
                          onClick={() =>
                            void deliverMessage(message.content, message.client_message_id)
                          }
                          type="button"
                        >
                          Повторить отправку
                        </button>
                      </div>
                    )}
                  </div>
                </article>
              </li>
            ))}
          </ol>
        )}

        {historyQuery.isFetching && !historyQuery.isFetchingNextPage && (
          <p className="chat-refreshing" role="status">
            Обновление истории…
          </p>
        )}

        {canSend ? (
          <form className="chat-composer" onSubmit={submit}>
            <label className="form-field" htmlFor="chat-message-input">
              Сообщение
              <textarea
                id="chat-message-input"
                maxLength={10_000}
                onChange={(event) => {
                  draftRevision.current += 1;
                  setDraft(event.currentTarget.value);
                }}
                placeholder="Напишите сообщение"
                rows={3}
                value={draft}
              />
              <span className="chat-composer__count">{draft.length}/10,000</span>
            </label>
            <button
              className="button button--primary"
              disabled={sendMessage.isPending || !draft.trim()}
              type="submit"
            >
              {sendMessage.isPending ? 'Отправка…' : 'Отправить сообщение'}
            </button>
          </form>
        ) : (
          <p className="chat-readonly" role="status">
            Статус проекта: {projectStatusLabels[project.status]}. История чата доступна только для
            чтения.
          </p>
        )}
      </section>
    </main>
  );
}
