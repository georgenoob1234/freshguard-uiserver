# Smart Scale UI Service

A FastAPI-based microservice that provides the web UI for the Smart Scale computer vision system. It displays scan results, fruit detection, defect information, and pricing.

## Features

- Real-time scan result updates via WebSocket
- Responsive web UI for displaying fruit detection results
- Image proxy for camera service images
- Pricing display based on detected fruit types

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main UI page |
| `/health` | GET | Health check endpoint |
| `/update` | POST | Receive scan results from main server |
| `/api/current` | GET | Get current scan data as JSON |
| `/image/{image_id}` | GET | Proxy images from camera service |
| `/ws` | WebSocket | Real-time scan result updates |

## Configuration

Configuration is managed via environment variables with the `UI_` prefix:

| Variable | Default | Description |
|----------|---------|-------------|
| `UI_CAMERA_SERVICE_BASE_URL` | `http://localhost:8200` | Base URL of the Camera service |
| `UI_PRICE_CONFIG_PATH` | `prices.json` | Path to the pricing configuration file |

## Local Development

### Prerequisites

- Python 3.10+
- Dependencies from `requirements.txt`

### Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run with uvicorn (development mode with reload)
./uvicorn.sh

# Or manually:
uvicorn app.main:app --host 0.0.0.0 --port 8500 --reload
```

## Docker

### Building the Image

```bash
docker build -t ui-service:latest .
```

### Running the Container

```bash
docker run --rm -p 8500:8500 \
  -e UI_CAMERA_SERVICE_BASE_URL=http://camera-service:8200 \
  ui-service:latest
```

### Environment Variables for Docker

| Variable | Default | Description |
|----------|---------|-------------|
| `SERVICE_PORT` | `8500` | Port the service listens on |
| `UI_CAMERA_SERVICE_BASE_URL` | `http://localhost:8200` | Camera service URL |
| `UI_PRICE_CONFIG_PATH` | `prices.json` | Price config path (bundled in image) |

### Using Docker Compose

```bash
# Start the service
docker compose up -d

# View logs
docker compose logs -f ui-service

# Stop the service
docker compose down
```

### Health Check

Verify the service is running:

```bash
curl http://localhost:8500/health
# Response: {"status": "ok"}
```

## Integration

This service is part of the Smart Scale system and expects to communicate with:

- **Camera Service** (`UI_CAMERA_SERVICE_BASE_URL`): For fetching fruit images
- **Main Server**: Sends scan results to `/update` endpoint

The service exposes a WebSocket at `/ws` for real-time updates to connected UI clients.

