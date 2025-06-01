# Anomaly Detector Documentation

## Overview

The **Anomaly Detector** is a fully offline, self-hosted AI solution for ingesting system and event logs, detecting data irregularities, and producing human-readable, conversational summaries. By leveraging lightweight local models, high-speed vector search, and orchestration frameworks, the tool delivers near-real-time insights while ensuring data privacy, cost-effectiveness, and minimal operational overhead.



### Setup:
- Requirements:
    - Docker
    - Internet access (To pull needed images, and AI model - 4.0 GB)
- Start the program:
    - `make e` - create the .env file
    - `make b` - build the container

### Key Benefits

* **Privacy & Security:** All processing and storage occur on-premise via Ollama and Typesense.
* **Speed & Scalability:** Millisecond-level indexing and retrieval with Typesense; sub-second inference using Llama 3.2 via Ollama.
* **Clarity:** Technical anomalies are transformed into clear narratives, reducing operator cognitive load.

---

## System Architecture & Workflow

The system is divided into two coordinated phases—**anomaly extraction** and **summary generation**—connected by **Typesense** as the central data store.

### Phase 1: Log Ingestion & Anomaly Extraction

1. **Endpoint Ingestion (`POST /system_events`)**

   * Receives JSON-formatted logs from sensors or applications.
   * Validates data schema (e.g., timestamps, sensor IDs, metrics).

2. **Detection Engine**

   * Applies configurable rules (e.g., spikes, dropouts, pattern deviations).
   * Supports dynamic configuration for parameters and anomaly types.
   * Labels each event with `is_anomaly` and related metadata.

3. **Indexing in Typesense (Anomaly Store)**

   * Stores raw events and anomaly metadata.
   * Uses vector and field indexing for fast similarity and attribute-based searches.

   **Benefits:**

   * **Real-Time Indexing:** New anomalies are queryable immediately.
   * **Low Latency:** Sub-5ms query times under load.
   * **Schema Agility:** Modify fields without downtime.

---

### Phase 2: Scheduled Summarization

1. **Scheduler Setup**

   * Triggers every **30 seconds**.
   * Balances timely reporting and computational efficiency.

2. **Batch Retrieval**

   * Pulls anomalies from the last interval using Typesense queries.
   * Groups related anomalies via vector similarity.

3. **LangChain Orchestration**

   * Pipeline: Retrieval → Prompt Construction → Model Inference → Post-Processing.
   * Handles prompt templates, errors, and context truncation.

4. **Text Generation (Llama 3.2–3B via Ollama)**

   * Generates coherent, conversational summaries.
   * Includes timestamps, sensor IDs, and anomaly details.

5. **Summary Indexing (Summary Store)**

   * Stores summaries with `window_start`, `window_end`, and summary text.
   * Enables fast querying via `/summary`.

---

## API Endpoints

### `POST /system_events`

**Description:** Ingests and analyzes a single log entry.

**Request Body (JSON):**

```json
{
  "timestamp": "2025-05-28T12:57:51.622563Z",
  "sensor_id": "wtf-pipe-3",
  "temperature": 34.7,
  "pressure": 4.8,
  "flow": 73.6
}
```

**Response (JSON):**

```json
{
  "id": "2989",
  "timestamp": 1748437071622,
  "sensor_id": "wtf-pipe-3",
  "temperature": 34.7,
  "pressure": 4.8,
  "flow": 73.6,
  "is_anomaly": true,
  "anomalies": [
    {
      "type": "spike",
      "parameter": "pressure",
      "value": 4.8,
      "threshold": 4.0,
      "message": "Pressure spike: 4.80 bar (threshold 4.0 bar)",
      "timestamp": "2025-05-28T12:57:51.622563Z"
    }
  ]
}
```

**Internal Reference:** `container/system_events/runner.py`

---

### `GET /anomalies`

**Description:** Retrieve anomalies within a user-defined timeframe.

**Query Parameters:**

* `duration` (seconds, optional; default: 3600)

**Response (JSON array):**

```json
[
  {
    "anomalies": [
      {
        "duration_seconds": 22,
        "message": "No data for 22.0s (threshold 10s) on wtf-pipe-7",
        "sensor_id": "wtf-pipe-7",
        "timestamp": "2025-05-28T14:15:38.063827Z",
        "type": "dropout"
      },
      {
        "message": "Flow spike: 125.4 L/min (threshold 120 L/min)",
        "parameter": "flow",
        "sensor_id": "wtf-pipe-7",
        "timestamp": "2025-05-28T14:15:38.063827Z",
        "type": "spike",
        "value": 125.4
      }
    ],
    "flow": 125.4,
    "id": "3562",
    "is_anomaly": true,
    "pressure": 2.8,
    "sensor_id": "wtf-pipe-7",
    "temperature": 28.1,
    "timestamp": "2025-05-28T14:15:38.063000Z"
  }
]
```

---

### `GET /summary`

**Description:** Fetch the latest human-readable summaries.

**Query Parameters:**

* `limit` (integer, optional; default: 10)

**Response (JSON array):**

```json
[
  {
    "window_start": "2025-05-28T14:15:38.063000Z",
    "window_end": "2025-05-28T14:15:38.063000Z",
    "summary": "Here is the summary of the anomaly data:\n\nEarlier today around 2:15 PM, we detected a dropout on `wtf-pipe-7`. The sensor stopped reporting data for about 22 seconds. Additionally, at the same time, flow spiked to 125.4 L/min, which is unusually high compared to the normal threshold of 120 L/min. All other sensors reported normally during this period."
  }
]
```

---

### `GET /status`

**Description:** Check the health of core components.

**Response (JSON):**

```json
{
  "anomaly_store": "active",
  "summary_store": "active",
  "llm": "active"
}
```

---

## Technology Stack & Justification

| Component                 | Role                        | Rationale                                                              |
| ------------------------- | --------------------------- | ---------------------------------------------------------------------- |
| **Ollama**                | Local model execution       | On-prem inference, fast startup, optimized for low-memory environments |
| **Typesense**             | Vector & structured storage | Real-time indexing, flexible schema, and fast vector-based retrieval   |
| **Llama 3.2–3B-instruct** | Text generation             | Good balance of quality, speed, and resource efficiency                |
| **LangChain**             | Orchestration & prompt mgmt | Modular chains, retry logic, and template management                   |

---

## Configuration & Best Practices

* **Scheduler Interval:** 30 seconds ensures efficient, non-overlapping processing.
* **Model Temperature (0.1):** Promotes deterministic summaries with reduced hallucination.
* **Typesense Schema:** Must include `sensor_id`, `timestamp`, `anomaly_type`, and embeddings.
* **Resource Management:** Monitor CPU/GPU usage and scale batch sizes as needed.

---

## Model Temperature Rationale

Setting the temperature to **0.1** is optimal for factual summarization:

1. **Precision Over Creativity:** Focuses on relevant high-likelihood tokens.
2. **Retrieval Fidelity:** Ensures embeddings drive accurate summaries.
3. **Coherent Flow:** Structured, logical summaries.
4. **Hallucination Mitigation:** Reduces false information.

> **Note:** Lower values (<0.05) may cause repetitiveness.

---

## Deployment & Scaling

* **Containerization:** Use Docker Compose to run Ollama, Typesense, and the API.
* **Horizontal Scaling:** API can scale independently; connect to a shared Typesense instance.
* **Monitoring:** Integrate with Prometheus and Grafana for observability of ingest and inference metrics.

---

## Additional Sections

1. **Detection Thresholds**

   * **Static:** Fixed limits (e.g., pressure > 4.0).
   * **Dynamic:** Statistical baselines (e.g., percentiles, rolling averages).
   * **Hybrid Rules:** Compositional logic (e.g., "dropout after spike").

2. **LangChain Integration**

   * Retrieval → Prompt → LLM → Post-processing
   * Extendable via custom logic (e.g., severity ranking, multilingual output)

3. **API Reference**

   * Parameters, status codes, error schema
   * Pagination: `page`, `per_page`, filtering by `sensor_id`, `anomaly_type`

4. **Local Deployment Guide**:
    - Run  `make e` to generate all environment variables
    - Run  `make b`

5. **Observability & Security**

   * All diagnostics via structured logs
   * No external alerts; rely on logs and exception traces
   * Isolate services using Docker networks
   * Store data indefinitely for audits

---

## Final Remarks

The Anomaly Detector emphasizes secure, scalable, and intelligible log monitoring. Its offline-first architecture and efficient orchestration make it suitable for real-time operations in privacy-conscious environments.

