# Testing Infrastructure Specification (`voice-agent/`)

## Overview

This document outlines the testing infrastructure, isolation strategy, and test tier hierarchy for the `voice-agent/` sales assistant module. The test suite verifies database interaction tools (`search_catalog`, `place_order`), environment DB path resolution, Google ADK Agent initialization (`voice_catalog_concierge`), tool registration, system instruction adherence, and end-to-end shopping workflows.

---

## 1. Test Architecture & Directory Structure

```
ecommerce/
├── voice-agent/
│   ├── app/
│   │   └── agent.py              # ADK Agent definition & tool registration
│   ├── tools.py                  # Catalog search & order placement SQLite tools
│   ├── verify_voice_agent.py     # Standalone verification runner (R4 compliance)
│   └── tests/
│       ├── __init__.py
│       └── test_e2e_suite.py     # 4-Tier Pytest E2E test suite
├── backend/
│   ├── database.py               # Backend DB module
│   ├── seed.py                   # Catalog seed data script
│   └── products.db               # SQLite database (seed target)
├── TEST_INFRA.md                 # Infrastructure specification (this file)
└── TEST_READY.md                 # Test execution guide & tier summary
```

---

## 2. Testing Framework & Execution Tools

- **Primary Test Runner**: `pytest` (`pytest voice-agent/tests/test_e2e_suite.py -v`)
- **Standalone Verification Script**: `python voice-agent/verify_voice_agent.py`
- **Standard Library Support**: `unittest`, `sqlite3`, `pathlib`, `tempfile`, `os`, `sys`

---

## 3. Database Strategy & Isolation

- **Seed Database Context**: Tests can execute against `backend/products.db` (seeded with 25 products) or isolated temporary databases created via `tempfile.NamedTemporaryFile`.
- **Environment Resolution**: Tests override `PRODUCTS_DB_PATH` environment variable to test custom DB path resolution and missing file fallbacks without polluting production/development state.
- **Transaction & Table Safety**: `place_order` ensures automatic creation of the `orders` table (`id`, `customer_name`, `product_id`, `quantity`, `unit_price`, `total_price`, `created_at`).

---

## 4. 4-Tier Testing Methodology

| Tier | Category | Description | Key Focus Areas |
|------|----------|-------------|-----------------|
| **Tier 1** | Feature Coverage | Primary happy-path behaviors & schema contracts | Catalog query by text, category query, default empty query, order placement success, return schema verification, ADK agent metadata |
| **Tier 2** | Boundary & Corner Cases | Error paths, edge conditions & resource stress | Invalid product IDs, zero/negative quantities, missing DB file fallback, empty search results |
| **Tier 3** | Cross-Feature Combinations | Inter-module workflow interactions | Search catalog followed by order placement using matched product ID, multi-category searches with subsequent orders |
| **Tier 4** | Real-World Scenarios | End-to-end customer shopping sessions | Multi-item shopping sequence, direct database order verification, ADK tool invocation verification |

---

## 5. Google ADK Agent Inspection & Mocking Strategy

- **Agent Loading**: Verification that `voice-agent/app/agent.py` exports `voice_catalog_concierge`.
- **Model Verification**: Validates model configuration matches `gemini-live-2.5-flash-native-audio`.
- **System Prompt Inspection**: Asserts system instruction contains expected role and behavior text.
- **Tool Registration**: Verifies `search_catalog` and `place_order` are registered in the agent's tool set.
- **Network Decoupling**: E2E tests inspect agent structure and tool functions locally without requiring live API network connections or credentials.

---

## 6. Authoritative Sources of Expected Output

1. `PROJECT.md` & `ORIGINAL_REQUEST.md`: Interface contracts and return schema definitions.
2. `backend/seed.py`: Seed catalog dataset (25 items across Electronics, Apparel, Home & Kitchen, Fitness & Outdoors, Books & Stationery, Footwear).
3. SQLite Schema Spec: `orders` table structure and price calculations (`total_price = unit_price * quantity`).
