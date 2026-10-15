# event-payment-service
 Сервис принимает запросы на оплату, обрабатывает их через внешний платежный шлюз (эмуляцию) и уведомляет клиента о результате через webhook.

## :hammer_and_wrench: Технологии

- **Python 3.12**
- **FastAPI** - REST API
- **Pydantic v2** - валидация
- **SQLAlchemy 2.0** (async) -ORM
- **PostgreSQL** - база данных
- **Alembic** - миграции
- **HTTPX** — отправка webhook-уведомлений
- **RabbitMQ (FastStream)** - брокер сообщений
- **Docker / Docker Compose** - контейнеризация
- **uv** — управление зависимостями

## Архитектура

Приложение состоит из трёх независимых процессов:

**API** — принимает HTTP-запросы, проверяет API-ключ, создаёт платежи и предоставляет информацию об их статусе.

**Outbox Publisher** — периодически получает неопубликованные события из PostgreSQL, отправляет их в RabbitMQ и отмечает опубликованные записи.

**Consumer** — получает сообщения из RabbitMQ, обрабатывает платежи, обновляет их статусы и отправляет webhook-уведомления.

Схема взаимодействия:

```text
                  Client
                    |
                    v
               FastAPI (API)
                    |
                    v
                PostgreSQL
              /            \
         Payments         Outbox
                            |
                            v
                      Publisher
                            |
                            v
                        RabbitMQ
                            |
                            v
                        Consumer
                         /    \
                        v      v
                   PostgreSQL  Webhook
                                 |
                             HTTP POST
```

Все процессы запускаются в отдельных контейнерах и используют общую базу данных и брокер сообщений.

## Функциональность

### Создание платежа

`POST /api/v1/payments`

Принимает данные платежа и создаёт запись со статусом `pending`.

В рамках одной транзакции PostgreSQL сохраняются:

1. Запись платежа.
2. Событие `payment.created` в таблице Outbox.

API возвращает HTTP `202 Accepted`, не дожидаясь завершения фоновой обработки.

### Получение платежа

`GET /api/v1/payments/{payment_id}`

Позволяет получить информацию о платеже по UUID, включая его текущий статус.

### Аутентификация

Для доступа к API используется заголовок:

```http
X-API-Key: your-api-key
```

### Идемпотентность

При создании платежа обязателен заголовок:

```http
Idempotency-Key: unique-request-key
```

Повторный запрос с тем же ключом не создаёт новый платёж. Идемпотентность обеспечивается в том числе уникальным ограничением на уровне PostgreSQL.

Это защищает от создания дубликатов при повторных запросах клиента.

### Обработка платежей

Consumer получает идентификатор платежа из RabbitMQ и выполняет фоновую обработку:

- Имитирует обработку в течение 2–5 секунд.
- С вероятностью 90% устанавливает статус `succeeded`.
- С вероятностью 10% устанавливает статус `failed`.
- Сохраняет время обработки.
- Отправляет webhook на адрес, указанный при создании платежа.

Оба финальных статуса являются допустимыми результатами бизнес-обработки. Статус `failed` сам по себе не считается технической ошибкой и не требует повторного проведения платежа.

## Transactional Outbox

Паттерн Transactional Outbox используется для согласованного сохранения платежа и события, необходимого для фоновой обработки.

При создании платежа запись в таблице `payments` и соответствующее событие в `outbox` сохраняются в одной транзакции.

Отдельный Publisher выбирает неопубликованные события и отправляет их в RabbitMQ.

Для параллельной безопасной обработки записей используется блокировка PostgreSQL `FOR UPDATE SKIP LOCKED`.

Такой подход исключает ситуацию, когда платёж успешно сохранён, но приложение не успело записать событие для его публикации.

При этом доставка сообщений может быть повторной, поэтому обработка должна быть идемпотентной.

## Retry и Dead Letter Queue

Для обработки технических ошибок используется механизм повторных попыток на основе RabbitMQ.

При временной ошибке сообщение направляется в retry-очередь с задержкой:

| Попытка               | Задержка  |
| --------------------- | --------- |
| Первая повторная      | 2 секунды |
| Вторая повторная      | 4 секунды |
| После третьей неудачи | DLQ       |

Количество уже выполненных повторных попыток хранится в заголовке сообщения `x-attempt`.

Для отложенной доставки применяются TTL очередей и Dead Letter Exchange (DLX).

Используются следующие очереди:

- `payments.new` — основная очередь обработки.
- `payments.retry.2s` — первая повторная доставка.
- `payments.retry.4s` — вторая повторная доставка.
- `payments.dlq` — сообщения, которые невозможно успешно обработать.

Постоянные ошибки направляются в DLQ без повторных попыток.

Ошибки отправки webhook также обрабатываются механизмом Retry. При повторной доставке сообщения уже завершённый платёж не должен обрабатываться повторно.

## :arrow_up: Запуск проекта

### Требования

Для запуска необходимы:

- Docker
- Docker Compose

### 1. Клонирование репозитория

```bash
git clone https://github.com/DanilZheltikov/event-payment-service.git
cd event-payment-service
```

### 2. Настройка окружения

Создайте файл `.env` в корне проекта и заполните его своими данными по образцу `.env.example`

### 3. Запуск

```bash
docker compose up --build -d
```

Команда собирает образы и запускает:

- PostgreSQL
- RabbitMQ
- Alembic migrations
- FastAPI
- Outbox Publisher
- Consumer

Миграции применяются отдельным одноразовым сервисом `migrate` до запуска основных процессов приложения.

### 4. Проверка контейнеров

```bash
docker compose ps -a
```

Просмотр логов:

```bash
docker compose logs -f api publisher consumer
```

### 5. Доступ к сервисам

| Сервис              | Адрес                              |
| ------------------- | ---------------------------------- |
| Swagger UI          | http://localhost:8000/docs         |
| OpenAPI JSON        | http://localhost:8000/openapi.json |
| RabbitMQ Management | http://localhost:15672             |
| PostgreSQL          | localhost:5433                     |

Учётные данные RabbitMQ Management определяются конфигурацией сервиса `rabbitmq` в Docker Compose.

## :twisted_rightwards_arrows: Использование API

### Создание платежа

```bash
curl -X POST http://localhost:8000/api/v1/payments \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-api-key" \
  -H "Idempotency-Key: order-12345" \
  -d '{
    "amount": "1500.00",
    "currency": "RUB",
    "description": "Оплата заказа",
    "webhook_url": "https://example.com/webhook"
  }'
```

При успешном принятии запроса API возвращает HTTP `202 Accepted`.

Для проверки webhook можно использовать [webhook.site](https://webhook.site/), подставив предоставленный URL в поле `webhook_url`.

### Получение статуса платежа

```bash
curl -X GET \
  http://localhost:8000/api/v1/payments/<payment_uuid> \
  -H "X-API-Key: your-secret-api-key"
```

Возможные статусы:

| Статус      | Описание                                |
| ----------- | --------------------------------------- |
| `pending`   | Платёж ожидает обработки                |
| `succeeded` | Платёж успешно обработан                |
| `failed`    | Обработка платежа завершилась неуспешно |


## :file_folder: Структура проекта

```text
event-payment-service/
├── app/                              # Исходный код приложения
│   ├── core/                         # Конфигурация, константы и RabbitMQ
│   │   ├── broker.py                 # Настройка брокера и очередей
│   │   ├── config.py                 # Настройки приложения
│   │   └── constants.py              # Константы проекта
│   ├── db/                           # Работа с PostgreSQL
│   │   ├── base.py                   # Базовая модель SQLAlchemy
│   │   ├── mixins.py                 # Общие поля моделей
│   │   ├── repository.py             # Базовый репозиторий
│   │   └── session.py                # Асинхронные сессии БД
│   ├── payments/                     # Создание и получение платежей
│   │   ├── models.py                 # Модель платежа
│   │   ├── schemas.py                # Pydantic-схемы
│   │   ├── repository.py             # Запросы к БД
│   │   ├── service.py                # Бизнес-логика платежей
│   │   ├── router.py                 # REST API
│   │   └── enums.py                  # Статусы платежей
│   ├── outbox/                       # Паттерн Transactional Outbox
│   │   ├── models.py                 # Модель события
│   │   ├── repository.py             # Работа с событиями
│   │   ├── publisher.py              # Публикация в RabbitMQ
│   │   └── worker.py                 # Запуск Publisher
│   ├── processing/                   # Фоновая обработка платежей
│   │   ├── consumer.py               # Получение сообщений
│   │   ├── service.py                # Обработка платежей и webhook
│   │   ├── handlers.py               # Retry, ACK/NACK и DLQ
│   │   ├── exceptions.py             # Исключения обработки
│   │   ├── schemas.py                # Схемы сообщений
│   │   └── worker.py                 # Запуск Consumer
│   ├── dependencies.py               # Зависимости FastAPI
│   └── main.py                       # Точка входа FastAPI
├── migrations/                       # Миграции Alembic
│   ├── versions/                     # История миграций
│   ├── env.py                        # Конфигурация миграций
│   └── script.py.mako                # Шаблон миграций
├── alembic.ini                       # Настройки Alembic
├── Dockerfile                        # Сборка Docker-образа
├── docker-compose.yml                # Запуск всех сервисов
├── .dockerignore                     # Исключения при сборке образа
├── .env.example                      # Пример переменных окружения
├── pyproject.toml                    # Зависимости и настройки проекта
├── uv.lock                           # Зафиксированные зависимости
├── LICENSE                           # Лицензия
└── README.md                         # Документация
```
## :arrow_down: Остановка приложения

Остановить контейнеры:

```bash
docker compose down
```

Данные PostgreSQL и RabbitMQ сохраняются в Docker volumes.

Для полного удаления контейнеров и томов:

```bash
docker compose down -v
```

**Внимание:** команда с `-v` удаляет локальные данные PostgreSQL и RabbitMQ.

-----
### :technologist: Автор
[DanilZheltikov](https://github.com/DanilZheltikov)