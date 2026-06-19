# Library Borrow API

A simple REST API for managing a library's book inventory, members, and borrow/return records — built with **FastAPI** and **SQLAlchemy ORM**.

## Features

- Add, list, and delete books with copy tracking (total vs. available copies)
- Register library members with unique email validation
- Borrow and return books, with automatic copy-count updates
- View a member's full borrowing history
- Input validation via Pydantic (blank-field checks, positive copy counts, email format)

## Tech Stack

- **FastAPI** — web framework
- **SQLAlchemy (ORM)** — database models and queries
- **SQLite** — database (file: `library.db`)
- **Pydantic** — request validation

## Project Structure

```
.
├── main.py          # App entrypoint: models, schemas, and all API routes
├── library.db        # SQLite database (auto-created on first run)
└── README.md
```

## Setup

```bash
# Clone the repo
git clone https://github.com/<your-username>/library-borrow-api.git
cd library-borrow-api

# Install dependencies
pip install fastapi uvicorn sqlalchemy pydantic[email]

# Run the server
uvicorn main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.
Interactive docs (Swagger UI) at `http://127.0.0.1:8000/docs`.

## API Endpoints

### Books
| Method | Endpoint | Description |
|--------|----------|--------------|
| GET | `/api/books` | List all books (optional `?available_only=true`) |
| POST | `/api/books` | Add a new book |
| DELETE | `/api/books/{book_id}` | Delete a book |

### Members
| Method | Endpoint | Description |
|--------|----------|--------------|
| GET | `/api/members` | List all members |
| POST | `/api/members` | Register a new member |
| GET | `/api/members/{member_id}/history` | Get a member's borrow history |

### Borrow / Return
| Method | Endpoint | Description |
|--------|----------|--------------|
| POST | `/api/borrow` | Borrow a book (`book_id`, `member_id`) |
| POST | `/api/return/{record_id}` | Return a borrowed book |

## Example Request

**Add a book**
```bash
curl -X POST http://127.0.0.1:8000/api/books \
  -H "Content-Type: application/json" \
  -d '{"title": "Clean Code", "author": "Robert C. Martin", "total_copies": 3}'
```
