# notification-service — what to build

## Responsibility
**Consumer-only.** No public business endpoints. Subscribes to domain events and sends notifications (email/log/webhook — your choice; for the project, logging to stdout + a Mongo-backed history is enough).

## Endpoints to implement
| Method | Path              | Purpose                          | Auth |
|--------|-------------------|----------------------------------|------|
| GET    | `/healthz`        | Already done                     | none |
| GET    | `/notifications`  | (optional) list recent notifications for debugging/grading | none |

That's it. No POST/PATCH — input comes from RabbitMQ.

## What it does internally
On startup, it already binds queue `notification.queue` to exchange `events.exchange` with routing key `#` (catch-all). Implement the message handler (`_on_message` in `app/core/rabbitmq.py`) to:
1. Parse the message body (JSON).
2. Branch on routing key:
   - `user.registered`   → "Welcome" notification.
   - `event.created`     → broadcast to interested users (MVP: log it).
   - `event.cancelled`   → "Event cancelled" to all bookers.
   - `registration.created`   → "Booking confirmed".
   - `registration.cancelled` → "Booking cancelled".
3. (Optional) write a row to a `notifications` Mongo collection for the history endpoint.
4. `await message.ack()` is automatic via the `async with message.process():` block.

## Failure handling
- If your handler raises, the message is NACK'd and re-queued. Wrap risky work in try/except and decide: log + ack, or NACK + DLX (out of scope for MVP).
- Use idempotent handlers — RabbitMQ may redeliver.

## How it talks to other services
- **Sync HTTP**: none (outbound or inbound).
- **Async (RabbitMQ)**: consume only — see above.
- **No JWT** needed (no public protected routes).

## Env you already have
`RABBITMQ_URL`, `QUEUE_NAME=notification.queue`, `PORT=8000`. If you add Mongo for notification history, also add `MONGO_URL` + `DB_NAME=notification_db` and update the infra compose + k8s configs.

---

## How to run locally

You need the infra stack up. The infra repo orchestrates everything.

### Option A — full stack via infra
```
cd ../infra
bash scripts/up-dev.sh
```
notification-service is at **http://localhost:8004**.
Logs: `docker compose -p events-dev logs -f notification-service`

### Option B — code-reload while iterating
1. Start RabbitMQ + (optional) the publishers:
   ```
   cd ../infra
   docker compose -p events-dev -f compose/docker-compose.yml -f compose/docker-compose.dev.yml up -d rabbitmq registration-service event-service user-service
   ```
2. Run notification-service on the host:
   ```
   cd ../notification-service
   python -m venv .venv && source .venv/Scripts/activate
   pip install -r requirements.txt
   export RABBITMQ_URL=amqp://guest:guest@localhost:5672/
   export QUEUE_NAME=notification.queue SERVICE_NAME=notification-service
   uvicorn app.main:app --reload --port 8000
   ```

## How to test it without the publishers
1. Open RabbitMQ UI: `http://localhost:15672` (guest/guest).
2. Exchanges → `events.exchange` → Publish message:
   - Routing key: `registration.created`
   - Payload: `{"user_id":"u1","event_id":"e1"}`
3. Watch notification-service logs — your handler should fire.

## After you change code
```
cd ../infra
docker compose -p events-dev -f compose/docker-compose.yml -f compose/docker-compose.dev.yml up -d --build notification-service
```

## Definition of done
- Service starts, queue is visible in RabbitMQ UI bound to `events.exchange`.
- Publishing any of the 5 routing keys above triggers the handler (visible in logs).
- `/healthz` returns 200.
- (If implemented) `GET /notifications` returns recent processed messages.
