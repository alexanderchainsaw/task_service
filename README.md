## Сервис асинхронных задач

Сервис на FastAPI для создания задач через REST API. Задачи создаются со статусом NEW, затем воркер-издатель ставит их в очередь RabbitMQ, а воркер-потребитель обрабатывает их асинхронно.

### Стек технологий
- FastAPI + Pydantic v2
- PostgreSQL в качестве основной БД, SQLAlchemy, alembic для миграций
- RabbitMQ + aio-pika
- Docker, docker-compose для локальной отладки

### Архитектура

- **API Сервис** (`app`): FastAPI сервис, который создает задачи со статусом NEW
- **Воркер-издатель** (`publisher`): Фоновый воркер, который опрашивает задачи со статусом NEW и публикует их в RabbitMQ (помечает как PENDING)
- **Воркер-потребитель** (`worker`): Фоновый воркер, который потребляет задачи из RabbitMQ и обрабатывает их

### Запуск локально
1) Скопируйте `.env.example` в `.env` и при необходимости настройте.
2) Соберите и запустите:
```
make run
```
3) Документация API: http://localhost:8000/docs

Сервис запускает 5 контейнеров:
- `rabbitmq` - Брокер сообщений
- `postgres` - База данных
- `app`: FastAPI инстанс на uvicorn
- `publisher`: Воркер, который публикует задачи со статусом PENDING в очередь
- `consumer`: Воркер, который обрабатывает задачи из очереди

* Примечание: и publisher и consumer можно запустить в нескольких инстансах, поменяв значение replicas в docker-compose.yml

### Тесты

Набор тестов включает как модульные, так и интеграционные тесты:

- **Модульные тесты** (`tests/unit/`):
  - `test_task_model.py` - Методы модели Task и переходы статусов
  - `test_task_service.py` - Бизнес-логика TaskService (create, list, get, cancel)
  - `test_publisher.py` - RabbitMQ издатель с мокированием

- **Интеграционные тесты** (`tests/integration/`):
  - `test_api_tasks.py` - Полное тестирование API endpoints с HTTP клиентом

Запуск тестов:
```bash
make test
```


### API
- POST `/api/v1/tasks` — создать задачу
- GET `/api/v1/tasks` — список задач с фильтрами и пагинацией
- GET `/api/v1/tasks/{task_id}` — детали задачи
- GET `/api/v1/tasks/{task_id}/status` — только статус
- DELETE `/api/v1/tasks/{task_id}` — отменить
