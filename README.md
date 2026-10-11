# E-Commerce AI Voice Sales Assistant

An intelligent full-stack e-commerce application equipped with a real-time, low-latency AI Voice Sales Assistant powered by **Google ADK (Agent Development Kit)** and the **Gemini Live 2.5 Native Audio** model (`gemini-live-2.5-flash-native-audio`).

Shoppers can browse products, search the catalog using speech, ask questions about specifications and stock, and place orders directly through natural, continuous voice conversation.

---

## Architecture Overview

```
                                      +---------------------------------------------+
                                      |            Google Vertex AI Live API        |
                                      |   (gemini-live-2.5-flash-native-audio)      |
                                      +----------------------+----------------------+
                                                             ^
                                            Bi-directional   |   Bi-directional
                                            Audio & Tools    |   Audio & Tools
                                                             v
+--------------------------+  WebSocket  +---------------------------------------------+
|   React Web Frontend     |<===========>|             FastAPI Backend Bridge          |
|  (Web Audio 16kHz/24kHz) |  (/ws/voice)|          (Google ADK Live Runner)           |
+--------------------------+             +----------------------+----------------------+
             |                                                  |
             | HTTP REST (/api/products)                        | SQLite WAL
             v                                                  v
+--------------------------+                     +-------------------------------------+
|    Product Catalog UI    |                     |      Local SQLite Database          |
|  (Live Search & Orders)  |                     |        (products.db)                |
+--------------------------+                     +-------------------------------------+
```

### Core Components

1. **Frontend (`frontend/`)**:
   - Modern React application built with Vite.
   - Interactive product grid with category filtering, search, and pagination.
   - Floating interactive voice concierge (`VoiceWidget.jsx`) featuring Web Audio API microphone capture (16kHz 16-bit PCM), low-latency 24kHz native audio playback, and real-time state visualization (Listening, Speaking, Processing).
   - Real-time catalog and order status synchronization driven by incoming WebSocket events.

2. **Backend (`backend/`)**:
   - FastAPI REST API providing product listing, filtering, search, and order retrieval endpoints.
   - Full-duplex WebSocket endpoint (`/ws/voice`) that bridges the browser's audio stream directly to the Google ADK Live Agent runner.
   - Robust error handling, disconnect cleanup, and SQLite WAL mode configuration for concurrent read/write transactions.

3. **Voice Agent (`voice-agent/`)**:
   - Built on Google ADK (`google-adk`).
   - Agent Definition (`voice-agent/app/agent.py`): `voice_catalog_concierge` with system instructions tailored for an upbeat, concise sales concierge.
   - Tool Integration (`voice-agent/tools.py`):
     - `search_catalog(query, category)`: Scans the product database for matching items, stock availability, and prices.
     - `place_order(customer_name, product_id, quantity)`: Records verified order transactions into SQLite and returns structured order receipts.

---

## Prerequisites

- **Python**: 3.10, 3.11, or 3.12
- **Node.js**: v18+ (tested on Node 20 / 24) and npm
- **Google Cloud Platform**:
  - A GCP Project with the **Vertex AI API** enabled.
  - Google Cloud CLI (`gcloud`) authenticated via Application Default Credentials:
    ```bash
    gcloud auth application-default login
    ```

---

## Installation & Setup

### 1. Clone the Repository
```bash
git clone git@github.com:kailashvyas/ecommerce-ai-voice-agent.git
cd ecommerce-ai-voice-agent
```

### 2. Configure Environment Variables
Copy the environment template and set your Google Cloud Project details:
```bash
cp env.dist .env
```
Edit `.env` (or `voice-agent/.env`) with your configuration:
```ini
GOOGLE_GENAI_USE_VERTEXAI=1
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=us-central1
PRODUCTS_DB_PATH=backend/products.db
```

### 3. Setup Python Virtual Environment & Dependencies
```bash
python3 -m venv .venv
source .venv/bin/activate

# Install Backend and Voice Agent packages
pip install --upgrade pip
pip install -r backend/requirements.txt
pip install -r voice-agent/requirements.txt
```

### 4. Seed the Database
Initialize and populate the SQLite catalog (`backend/products.db`) with 25 sample products across Electronics, Apparel, Home & Kitchen, Sports, and Books:
```bash
python backend/seed.py
```

### 5. Setup Frontend
```bash
cd frontend
npm install
cd ..
```

---

## Running the Application

### 1. Start the FastAPI Backend
From the root repository directory with `.venv` activated:
```bash
source .venv/bin/activate
set -a && source .env && set +a
uvicorn backend.main:app --reload --port 8000
```
- API Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
- REST Endpoints: `GET /api/products`, `GET /api/orders`
- WebSocket Bridge: `ws://localhost:8000/ws/voice`

### 2. Start the React Frontend
In a separate terminal:
```bash
cd frontend
npm run dev
```
Open your browser at [http://localhost:3000](http://localhost:3000).

---

## Using the Voice Assistant

1. Click the purple microphone widget located in the bottom-right corner of the web interface.
2. Grant microphone permissions when prompted by your browser.
3. Once connected, talk to the assistant naturally:
   - *"What wireless headphones do you have?"*
   - *"Show me your running shoes under $150."*
   - *"Can you order 1 Ergonomic Wireless Mouse for Kailash?"*
4. Notice how:
   - The assistant replies immediately with synthesized speech.
   - The on-screen product catalog filters in real time according to what you asked.
   - Placed orders are confirmed with order ID, unit price, and total price.

---

## Running Verification & Tests

To execute the automated end-to-end verification suite across the backend, SQLite database, voice agent tools, WebSocket endpoint, and frontend build:

```bash
python verify_fullstack_voice.py
```

To run the voice agent standalone test suite:
```bash
pytest voice-agent/tests
```

To test the agent with the Google ADK Web inspection tool:
```bash
set -a && source .env && set +a
adk web voice-agent/app
```

---

## License

MIT License. See [LICENSE](LICENSE) for details.
