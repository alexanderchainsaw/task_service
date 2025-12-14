## Сервис асинхронных задач

Сервис на FastAPI для создания задач через REST API. Задачи создаются со статусом NEW, затем воркер-паблишер ставит их в очередь RabbitMQ, а воркер-консьюмер обрабатывает их асинхронно.

### Стек технологий
- FastAPI
- PostgreSQL в качестве основной БД, SQLAlchemy, asyncpg alembic для миграций
- RabbitMQ + aio-pika
- Docker, docker-compose для локальной отладки
- testcontainers для автоматического запуска PostgreSQL в тестах

### Архитектура

- **API Сервис** (`app`): FastAPI сервис, который создает задачи со статусом NEW
- **Воркер-паблишер** (`publisher`): Воркер, который опрашивает задачи со статусом NEW и публикует их в RabbitMQ (помечает как PENDING)
- **Воркер-консьюмер** (`consumer`): Воркер, который потребляет задачи из RabbitMQ и обрабатывает их

### Запуск локально
Сборка и запуск одной командой
```
make run
```

3) Документация API: http://localhost:8000/docs

Сервис запускает 5 сервисов:
- `rabbitmq` - Брокер сообщений
- `postgres` - База данных
- `app`: FastAPI инстанс на uvicorn
- `publisher`: Воркер, который публикует задачи со статусом PENDING в очередь (в 3 инстансах)
- `consumer`: Воркер, который обрабатывает задачи из очереди (в 3 инстансах)

**Примечание**: кол-во инстансов publisher и consumer можно изменить через значение replicas в docker-compose.yml

### Тесты

Набор тестов включает как модульные, так и интеграционные тесты:

- **Модульные тесты** (`tests/unit/`):
  - `test_task_model.py` - Методы модели Task и переходы статусов
  - `test_task_service.py` - Бизнес-логика TaskService (create, list, get, cancel)
  - `test_repository.py` - Тесты репозитория для работы с БД
  - `test_task_registry.py` - Реестр типов задач
  - `test_task_implementations.py` - Реализации различных типов задач
  - `test_publisher.py` - RabbitMQ издатель с мокированием
  - `test_consumer.py` - Тесты потребителя задач

- **Интеграционные тесты** (`tests/integration/`):
  - `test_api_tasks.py` - Полное тестирование API endpoints с HTTP клиентом

**Особенности тестового окружения:**
- Используется **testcontainers** для автоматического запуска PostgreSQL контейнера
- Не требуется ручная настройка PostgreSQL - контейнер запускается и останавливается автоматически
- Тесты используют реальную PostgreSQL БД для максимальной совместимости с production

**Требования для запуска тестов:**
- Docker должен быть запущен (для testcontainers)
- Python 3.13+

**Запуск тестов:**
```bash
make test
```

Или напрямую:
```bash
pytest tests
```


### API
- POST `/api/v1/tasks` — создать задачу
- GET `/api/v1/tasks` — список задач с фильтрами и пагинацией
- GET `/api/v1/tasks/{task_id}` — детали задачи
- GET `/api/v1/tasks/{task_id}/status` — только статус
- DELETE `/api/v1/tasks/{task_id}` — отменить
