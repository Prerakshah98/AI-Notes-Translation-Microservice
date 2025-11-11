# AI Notes & Translation Microservice

This project is a scalable, containerized Django-based backend microservice. It allows users to create text-based notes, asynchronously translate them into other languages using a background AI model, and retrieve analytics. The entire application is containerized with Docker for easy and reliable local deployment.

This project was built as a backend SDE-2 assignment.

---

## 🚀 Tech Stack

* **Backend:** Python 3.10, Django, Django REST Framework
* **Database:** PostgreSQL
* **Async Task Queue:** Celery
* **Cache / Message Broker:** Redis
* **AI / Translation:** Hugging Face `transformers` library
* **Containerization:** Docker & Docker Compose
* **Production Server:** Gunicorn

---

## ⚙️ Setup & Local Deployment

This project is designed to run locally using Docker Compose. This is the simplest and most reliable way to run the entire application stack.

**Prerequisites:**
* Docker
* Docker Compose

**Steps:**

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/your-username/ai-notes-service.git](https://github.com/your-username/ai-notes-service.git)
    cd ai-notes-service
    ```

2.  **Create the environment file:**
    Create a file named `.env` in the project root. This file holds all configuration and secrets.
    ```env
    DEBUG=1
    SECRET_KEY=your-django-secret-key-here # Use a real one!
    
    POSTGRES_DB=notesdb
    POSTGRES_USER=notesuser
    POSTGRES_PASSWORD=supersecretpassword
    POSTGRES_HOST=db
    POSTGRES_PORT=5432
    
    REDIS_HOST=redis
    REDIS_PORT=6379
    ```

3.  **Build and run the containers:**
    This single command will build the Django image and start all 4 services (`web`, `db`, `redis`, `celery`).
    ```bash
    docker-compose up --build
    ```

4.  **Run database migrations:**
    In a **new terminal window**, run this command to set up the database tables inside the `db` container:
    ```bash
    docker-compose exec web python manage.py migrate
    ```

The application is now running and accessible at `http://127.0.0.1:8000`.

---

## 🕹️ API Documentation (Postman Examples)

All endpoints are prefixed with `/api/v1/`.

### 1. Create a Note
* **Method:** `POST`
* **URL:** `http://127.0.0.1:8000/api/v1/notes/`
* **Body:** Go to the **Body** tab, select **raw**, and choose **JSON**.
    ```json
    {
        "title": "My Note",
        "original_text": "Hello world",
        "original_language": "en"
    }
    ```

### 2. List All Notes
* **Method:** `GET`
* **URL:** `http://127.0.0.1:8000/api/v1/notes/`

### 3. Get a Single Note
* **Method:** `GET`
* **URL:** `http://127.0.0.1:8000/api/v1/notes/1/` (Use the ID of the note you want)

### 4. Update a Note
* **Method:** `PATCH`
* **URL:** `http://127.0.0.1:8000/api/v1/notes/1/`
* **Body:** (**raw** / **JSON**)
    ```json
    {
        "title": "My Updated Title"
    }
    ```

### 5. Delete a Note
* **Method:** `DELETE`
* **URL:** `http://127.0.0.1:8000/api/v1/notes/1/`

### 6. Start a Translation
* **Method:** `POST`
* **URL:** `http://127.0.0.1:8000/api/v1/notes/1/translate/`
* **Body:** (**raw** / **JSON**)
    ```json
    {
        "target_language": "es"
    }
    ```
* **Response:** You will get a `202 Accepted` status immediately.
    ```json
    {
        "status": "Translation in progress"
    }
    ```

### 7. Get Analytics
* **Method:** `GET`
* **URL:** `http://127.0.0.1:8000/api/v1/stats/`

---

## 🏛️ Architecture & Design

### High-Level Design (HLD)

The system is orchestrated by Docker Compose, which runs four distinct services in an isolated network on the local machine.



1.  **User:** Interacts with the API (e.g., via Postman).
2.  **Web (Django/Gunicorn):** Handles all synchronous API requests. For fast requests (like CRUD), it talks directly to Postgres and Redis. For slow requests (like `/translate`), it schedules a job with Celery and returns a `202 Accepted` response immediately.
3.  **PostgreSQL (db):** The primary database (System of Record) for storing all note data.
4.  **Redis:** Serves two critical functions:
    * **Celery Broker:** Manages the queue of translation jobs to be processed.
    * **Cache:** Stores results of `GET /notes/<id>` for fast retrieval.
5.  **Celery (worker):** A separate background process that listens to the Redis queue. It picks up translation jobs, runs the slow AI model, and saves the result to Postgres.

### Low-Level Design (LLD)



**Async Translation Flow:**
1.  A `POST` request hits the `/api/v1/notes/1/translate/` endpoint.
2.  The `NoteViewSet`'s `translate` action is triggered.
3.  It calls `translate_note_task.delay(note.id, target_language)`. This places a job message in the Redis queue (DB 0).
4.  The view immediately returns `202 Accepted` to the user.
5.  The Celery worker, polling Redis, picks up the job.
6.  The worker executes the `translate_note_task` function.
7.  The task fetches the `Note` object from PostgreSQL.
8.  It runs the `transformers` model (using `use_safetensors=True`) to get the translation.
9.  It saves the `translated_text` and `translated_language` fields back to the `Note` object in PostgreSQL.
10. **Critically**, the task then calls `cache.delete(f'note_{note_id}')` to invalidate the stale cache in Redis (DB 1).

**Caching Flow (`GET /api/v1/notes/1/`):**
1.  A `GET` request hits the `NoteViewSet`'s `retrieve` method.
2.  The method generates a `cache_key` (e.g., `note_1`).
3.  It asks Redis: `cache.get('note_1')`.
4.  **Cache Hit:** If data is found, it's returned directly to the user.
5.  **Cache Miss:** If no data is found, the app queries PostgreSQL for the note.
6.  The note is serialized to JSON.
7.  The JSON is saved to Redis: `cache.set('note_1', data, timeout=300)`.
8.  The JSON is returned to the user.

---

## 🧐 Design Decisions

* **Why PostgreSQL over DynamoDB?**
    * The data for a "note" is highly structured and relational (even if it's a single table for now).
    * It allows for powerful and familiar SQL queries. The `/stats/` endpoint, for example, uses an efficient `GROUP BY` (via the Django ORM's `.annotate()`) that is trivial in SQL but more complex in NoSQL.

* **Why Celery for Translation?**
    * AI model inference is a slow, I/O-bound, and CPU-intensive task. It can take 5-30+ seconds.
    * Running this synchronously in the API request (`web` worker) would block the server thread, lead to a terrible user experience, and cause most clients to time out.
    * Celery + Redis is the standard, battle-tested Python solution for offloading this work to a separate background process, making the API feel instant and resilient.

* **Caching Strategy (Cache-Aside + Worker Invalidation):**
    * I used the **Cache-Aside** pattern on the `retrieve` (GET /notes/<id>) endpoint, as this is a high-read endpoint.
    * A simple TTL (Time-to-Live) on the cache is not enough. If a translation finishes, the user could see stale data for up to 5 minutes.
    * The solution was **explicit cache invalidation**. The Celery worker, *after* it successfully saves the translation to the database, is responsible for deleting the cache key. This ensures that the next `GET` request will have a cache miss, fetch the fresh data from Postgres, and re-populate the cache. This maintains data consistency between the DB and the cache.

---

## ⚠️ Known Limitations & Next Steps

* **Authentication:** The API is currently open. The highest priority next step would be to add **JWT-based authentication** to secure all endpoints.
* **Model Loading:** The translation model is loaded from Hugging Face every time a task runs. For a production system, this model should be pre-loaded when the Celery worker starts to reduce task overhead.
* **Error Handling:** The Celery task has a basic `try/except` block. This could be improved with more granular error handling and retry policies.
* **Monitoring:** The "good-to-have" **Prometheus/Grafana** integration was not implemented but would be essential for production monitoring.