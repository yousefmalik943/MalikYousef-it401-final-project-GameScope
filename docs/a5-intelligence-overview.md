# A5 Intelligence Generation Overview

GameScope now includes an intelligence generation workflow that uses retrieved database records as context before generating a recommendation. The feature keeps the application grounded in its own data rather than relying on arbitrary external knowledge.

## Retrieval-Augmented Workflow

User Request -> Retrieve Relevant Records -> Build Context -> Generate Intelligence -> Display Results

## Selected Capability

Recommendation generation using retrieved search results.

## Why this feature

It adds value beyond simple retrieval by identifying the strongest candidate from the matched records, summarizing common themes, and exposing a confidence level and evidence list.

## Prompt Design

- System instructions: instruct the model to use only the retrieved records and return JSON.
- User prompt: includes the user's request and the specific records returned by the app.
- Retrieved context: only the selected records and confidence-related metadata.

## Validation and Reliability

- Required fields are validated before output is shown or saved.
- Invalid JSON, missing fields, and empty output are rejected.
- Fallback logic generates a deterministic recommendation when no API key or model response is available.
- Database write failures and retrieval errors are handled gracefully.

## Persistence

The application stores generated recommendations with prompt version, model used, timestamp, user request, source IDs, and output JSON.
