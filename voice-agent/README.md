# Voice Sales Assistant (`voice-agent/`)

An AI-powered voice shopping assistant for the e-commerce store built using **Google ADK** (Agent Development Kit) and Gemini native live audio. The assistant enables natural voice interactions for browsing product catalogs, querying item details, and placing orders backed by a SQLite database.

---

## 📁 Directory Layout

```
voice-agent/
├── .env                  # ADK & Vertex AI configuration
├── app/
│   ├── __init__.py
│   └── agent.py          # ADK Agent definition (voice_catalog_concierge)
├── tests/
│   ├── __init__.py
│   └── test_e2e_suite.py # Multi-tiered E2E test suite
├── requirements.txt      # Python dependencies (google-adk, certifi, python-dotenv)
├── tools.py              # SQLite database tools (search_catalog, place_order)
├── verify_voice_agent.py # End-to-end automated verification script
└── README.md             # Setup and usage documentation
```

---

## 🚀 Quick Start

### 1. Virtual Environment & Dependencies

The repository has a shared virtual environment in `.venv/` at the project root. Packages are installed directly into this environment:

```bash
# Option A: Activate .venv first
source .venv/bin/activate
pip install -r voice-agent/requirements.txt

# Option B: Install directly using the .venv pip binary
.venv/bin/pip install -r voice-agent/requirements.txt
```

> **Note:** `google-adk`, `certifi`, and `python-dotenv` are already installed in `.venv`.

---

### 2. Environment Configuration (`.env`)

The `.env` file is located at `voice-agent/.env` (and replicated at the project root `.env` for convenience):

```env
# Google Cloud Vertex AI & ADK Settings
GOOGLE_GENAI_USE_VERTEXAI=1
GOOGLE_CLOUD_PROJECT=light-footing-208411
GOOGLE_CLOUD_LOCATION=us-central1

# Database Location
PRODUCTS_DB_PATH=../backend/products.db
```

#### How `.env` is Loaded:

1. **Automatic (Python runtime):**  
   Both `voice-agent/app/agent.py` and `voice-agent/tools.py` use `python-dotenv` to automatically discover and load `voice-agent/.env` (and repo root `.env`) on startup. No manual export is needed when running Python scripts.

2. **In your Shell (for CLI tools like `adk web`):**  
   To load the environment variables into your current terminal session:
   ```bash
   # Method 1 (Zsh / Bash):
   set -a && source voice-agent/.env && set +a

   # Method 2 (Export all non-comment lines):
   export $(grep -v '^#' voice-agent/.env | xargs)
   ```

3. **SSL Certificate Configuration:**  
   Export the `certifi` CA certificate bundle to ensure secure TLS connections to Google APIs:
   ```bash
   export SSL_CERT_FILE=$(.venv/bin/python3 -m certifi)
   ```

---

### 3. Running the ADK Web Server

With `.venv` activated and `.env` loaded:

```bash
# 1. Activate environment and load settings
source .venv/bin/activate
set -a && source voice-agent/.env && set +a
export SSL_CERT_FILE=$(python3 -m certifi)

# 2. Launch ADK Web Testing Interface
adk web voice-agent/app
```

Alternatively, run without activating using `.venv` directly:
```bash
set -a && source voice-agent/.env && set +a
export SSL_CERT_FILE=$(.venv/bin/python3 -m certifi)
.venv/bin/adk web voice-agent/app
```

Open the web server URL printed in the terminal (typically `http://localhost:8000` or `http://localhost:8080`) in a web browser to test voice audio interactions.

---

## 🛠️ Tools & Capabilities

The agent (`voice_catalog_concierge`) utilizes model `gemini-live-2.5-flash-native-audio` with Vertex AI and executes the following tools:

- **`search_catalog(query: str = None, category: str = None)`**  
  Queries `backend/products.db` for matching items by title, description, or category. Returns item details including ID, title, price, description, and stock status.

- **`place_order(customer_name: str, product_id: int, quantity: int)`**  
  Ensures the `orders` table exists in SQLite, inserts the customer order, and returns a structured confirmation payload with order ID, unit price, total price, and timestamp.

---

## 🧪 Verification & Testing

### Automated E2E Verification Script

Run the verification script to test database connectivity, tool execution, `.env` loading, and ADK agent exports:

```bash
.venv/bin/python voice-agent/verify_voice_agent.py
```

Expected output:
```
============================================================
Starting Voice Agent End-to-End Verification
============================================================
[✓] Database located at: /path/to/ecommerce/backend/products.db
[✓] search_catalog verified (found 1 items for 'headphones')
[✓] place_order verified (order ID inserted into orders table)
[✓] ADK Agent voice_catalog_concierge verified with tools: ['search_catalog', 'place_order']
============================================================
ALL VOICE AGENT VERIFICATION CHECKS PASSED SUCCESSFULLY!
============================================================
```

### Full Test Suite

Run the pytest suite covering schema contracts, edge cases, and multi-step shopping workflows:

```bash
.venv/bin/pytest voice-agent/tests/test_e2e_suite.py
```
