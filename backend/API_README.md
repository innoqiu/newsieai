# NewsieAI API Server

FastAPI server for connecting the frontend with the backend agents.

## Setup

1. **Install dependencies** (if not already installed):
```bash
pip install fastapi uvicorn[standard] pydantic pydantic[email] python-multipart
```

Or use the requirements file:
```bash
pip install -r requirements_api.txt
```

2. **Start the API server**:
```bash
cd backend
python api_server.py
```

The server will run on `http://localhost:8008`

## API Endpoints

### POST `/api/profile`
Create or update user profile.

**Request Body:**
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "notification_time": "09:00,21:30",
  "interests": "technology, crypto, finance"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Profile created successfully for John Doe",
  "user_id": "john",
  "profile": {
    "user_id": "john",
    "name": "John Doe",
    "email": "john@example.com",
    "timezone": "UTC",
    "preferred_notification_times": ["09:00", "21:30"],
    "content_preferences": ["technology", "crypto", "finance"]
  }
}
```

### POST `/api/news/request`
Request news based on query.

**Request Body:**
```json
{
  "content_query": "latest technology news"
}
```

### POST `/api/personal-assistant/run`
Run Personal Assistant Agent with user profile.

**Request Body:** Same as `/api/profile`

## Frontend Integration

The frontend (React) should be running on `http://localhost:5173` (Vite default port).

Make sure both servers are running:
- Backend API: `http://localhost:8008`
- Frontend: `http://localhost:5173`

## CORS Configuration

The API server is configured to allow requests from:
- `http://localhost:5173` (Vite dev server)
- `http://localhost:3000` (Alternative React port)
- `http://127.0.0.1:5173`

If you need to add more origins, edit `api_server.py` and update the `allow_origins` list.

