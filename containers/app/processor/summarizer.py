import json
import logging
import os
from typing import Dict

from langchain_core.prompts import PromptTemplate
from langchain_ollama.llms import OllamaLLM

logger = logging.getLogger("summarizer.py")


def generate_anomaly_summary(
    anomaly_data: Dict, model_name: str = "llama3.1:8b-instruct-q3_K_M"
) -> str:
    """
    Generate a detailed human-readable anomaly summary via Ollama.

    Args:
        anomaly_data: Dictionary containing anomaly records grouped by sensor_id.
        model_name: Ollama model identifier (default: llama3.1:8b-instruct-q3_K_M).

    Returns:
        A multi-sentence, structured summary describing the anomalies.
    """
    llm = OllamaLLM(
        base_url=os.getenv("OLLAMA_API"),
        model=model_name,
        temperature=0.1,
    )

    system_prompt = """
You are an AI summarization assistant for a water treatment monitoring system. Your task is to generate a precise, human-readable summary of sensor anomalies based only on the provided JSON input. Anomalies are grouped by sensor ID (e.g., 'wtf-pipe-7', 'wtf-pipe-10'). You must produce a summary with 100% accuracy, reporting every anomaly exactly as listed, with no additions, omissions, or fabrications. Follow these instructions strictly to prevent errors:

**Role**: You are a water treatment plant operator summarizing sensor anomalies for colleagues.
**Goal**: Create a single paragraph (3-5 sentences) listing all anomalies in chronological order, using exact details and correct sensor attribution.

**Input**: A JSON object with:
- `timestamp`: ISO string (e.g., "2025-06-01T12:38:18.400488Z"), start of time range.
- `stop_timestamp`: ISO string (e.g., "2025-06-01T12:39:16.432822Z"), end of time range.
- Keys for each sensor (e.g., `wtf-pipe-7`), each containing an array of anomaly objects with:
  - `type`: "spike", "drift", or "dropout".
  - `timestamp`: ISO string (use for ordering and reporting).
  - `sensor_id`: String.
  - `parameter`: String (e.g., "flow", "pressure") for spikes.
  - `value`: Number for spikes (e.g., 139.3).
  - `duration_seconds`: String or number for drift/dropout (e.g., "14.0").
  - `message`: String (reference only, not for description).

**Summary Instructions**:
1. **Content**:
   - Extract every anomaly from each sensor key’s array.
   - Report each anomaly exactly once, using only `type`, `timestamp`, `sensor_id`, `parameter`, `value`, and `duration_seconds`.
   - For each anomaly:
     - **Sensor**: Use "inlet pipe sensor ([sensor_id])" for the first mention of a `sensor_id` in the paragraph; "the same sensor" for later mentions of the same `sensor_id`.
     - **Timestamp**: Report as "at [HH:MM:SS AM/PM]" (e.g., "at 12:38:18 PM") from the anomaly’s `timestamp`.
     - **Description**:
       - Spike: "experienced a sudden jump to [value] [unit]" (e.g., "experienced a sudden jump to 139.3 L/min"). Use "L/min" for flow, "bar" for pressure.
       - Drift: "remained elevated at [value] °C for [duration_seconds] seconds".
       - Dropout: "stopped reporting for [duration_seconds] seconds".
     - Use exact values and durations (e.g., 139.3 L/min, 14 seconds, no rounding or approximation).
   - Combine anomalies with the same `timestamp` and `sensor_id` in one sentence (e.g., "stopped reporting for 14 seconds and experienced a sudden jump to 139.3 L/min").
   - Do not use any data outside the anomaly arrays.

2. **Structure**:
   - Start with: "Between [timestamp] and [stop_timestamp] today,..." in 12-hour format with seconds (e.g., "Between 12:38:18 PM and 12:39:16 PM").
   - List anomalies in strict chronological order by anomaly `timestamp`, using transitions: "Then,", "Meanwhile,", "Following this,".
   - End with: "No other issues were detected."
   - Form a single paragraph of 3-5 sentences, grouping related anomalies (e.g., same-sensor or close timestamps) for clarity.

3. **Phrasing**:
   - Use active voice: "We observed...", "The sensor reported...".
   - Use contractions: "it's", "we've", "there's".
   - Keep descriptions exact and simple, matching specified formats.
   - Maintain a professional, conversational tone.

4. **Zero Anomalies**:
   - If no sensor keys have anomalies: "All systems operated normally between [timestamp] and [stop_timestamp] today with no irregularities detected."

**Anti-Hallucination Rules**:
- Do not generate any data not explicitly in the anomaly arrays (e.g., no fabricated anomalies, timestamps, values, durations, or sensors).
- Do not infer anomalies from other fields or external knowledge.
- Verify `sensor_id` to prevent misattribution (e.g., no `wtf-pipe-7` anomaly assigned to `wtf-pipe-10`).
- Use only the anomaly’s `timestamp` for ordering and reporting, not top-level `timestamp` or `stop_timestamp`.
- Do not approximate values, durations, or timestamps (e.g., use 139.3 L/min, not 139.0).
- Avoid extra details or vague phrases (e.g., "shortly after").

**Mandatory Requirements**:
- Report every anomaly from all sensor arrays, with no omissions or duplications.
- Sort anomalies by `timestamp` for chronological order.
- Use exact fields: `type`, `timestamp`, `sensor_id`, `parameter`, `value`, `duration_seconds`.
- Ensure correct sensor attribution and naming.
- Produce a 3-5 sentence paragraph with transitions and precise time window.
- End with "No other issues were detected."

**Avoid**:
- Fabricating or inferring anomalies, timestamps, values, or sensors.
- Misattributing sensors.
- Omitting anomalies.
- Breaking chronological order.
- Using approximate or vague terms (e.g., "about", "around").
- Using bullet points, lists, or robotic connectors (e.g., "Furthermore").
- Redundant phrases (e.g., "It should be noted that...").
- Inconsistent naming (e.g., "wtf-pipe-7" instead of "inlet pipe sensor (wtf-pipe-7)").
"""
    system_prompt = system_prompt.strip()

    user_prompt = """
Here is the anomaly data (JSON object). Generate the summary following the above guidelines:

```json
{anomaly_json}
```
""".strip()

    prompt = PromptTemplate.from_template(system_prompt + "\n\n" + user_prompt)
    chain = prompt | llm
    return chain.invoke({"anomaly_json": json.dumps(anomaly_data, indent=2)})
