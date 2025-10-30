# Nimrag Smart Mirror Backend

This is the backend service for the Nimrag Smart Mirror project. It's built with FastAPI and provides various APIs for the smart mirror functionality.

## Features

- RESTful APIs for all mirror functionalities
- WebSocket support for real-time updates
- Smart home integration via MQTT
- GPIO control for LED strips
- Gesture recognition with MediaPipe
- Voice commands with Vosk

## Requirements

- Python 3.12+
- FastAPI
- MediaPipe
- OpenCV
- Vosk
- MQTT Client
- GPIO (for Raspberry Pi)

## Installation

1. Create a virtual environment:
   ```bash
   python3.12 -m venv venv
   source venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file with your configuration:
   ```
   PROJECT_NAME=Nimrag Smart Mirror
   VERSION=1.0.0
   SECRET_KEY=your-secret-key
   WEATHER_API_KEY=your-api-key
   ```

## Project Structure

```
Backend/
├── src/
│   ├── api/
│   │   └── api_v1/
│   │       ├── endpoints/
│   │       │   ├── weather.py
│   │       │   ├── calendar.py
│   │       │   ├── led.py
│   │       │   └── smart_home.py
│   │       └── api.py
│   ├── core/
│   │   └── config.py
│   ├── models/
│   │   └── ...
│   ├── services/
│   │   ├── weather.py
│   │   ├── led.py
│   │   └── mqtt.py
│   └── utils/
│       └── ...
├── venv/
├── requirements.txt
└── .env
```

## Running the Application

1. Activate the virtual environment:
   ```bash
   source venv/bin/activate
   ```

2. Start the server:
   ```bash
   cd src
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

The API will be available at `http://localhost:8000` with documentation at `/docs`.

## Development

- API endpoints are in `src/api/api_v1/endpoints/`
- Core services are in `src/services/`
- Configuration is managed in `src/core/config.py`
- Environment variables are stored in `.env`

## Testing

Run tests using pytest:
```bash
pytest
```

## License

This project is licensed under the MIT License.