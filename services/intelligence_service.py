import json
import os
import re
from datetime import datetime, timezone

import requests


class IntelligenceValidationError(ValueError):
    """Raised when a model response is missing required intelligence fields."""


class AiService:
    """Generate structured recommendations from retrieved database records."""

    def __init__(self, api_key=None, model=None, timeout=15):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.model = model or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        self.timeout = timeout
        self.base_url = "https://api.openai.com/v1"
        self.engine_used = "local-deterministic-engine"

    def build_prompt(self, user_request, records):
        context_lines = []
        for index, record in enumerate(records, start=1):
            details = [
                f"{index}. Title: {record.title}",
                f"Source: {record.source}",
                f"Genre: {record.tag or 'Unspecified'}",
                f"Approval: {record.approval if record.approval is not None else 'Not reported'}",
                f"Reviews: {record.review_count if record.review_count is not None else 'Not reported'}",
                f"Description: {record.description}",
            ]
            context_lines.append("\n   ".join(details))

        system_prompt = (
            "You are GameScope's recommendation engine. Use only the supplied records. "
            "Do not invent facts beyond the records. Create a concise recommendation for a user "
            "who is exploring games from the retrieved results. Return valid JSON only and include "
            "summary, recommendation, confidence, and supporting_items keys."
        )
        user_prompt = (
            f"User request: {user_request or 'Recommend the strongest option from these records.'}\n\n"
            "Use the retrieved records below as evidence. Summarize the pattern across the records, "
            "recommend which option best matches the request, and explain why.\n\n"
            "Retrieved context:\n"
            + "\n\n".join(context_lines)
            + "\n\nReturn a JSON object with: {\n"
            "  'summary': '1-2 sentence narrative',\n"
            "  'recommendation': 'single recommendation for the user',\n"
            "  'confidence': 'High|Medium|Low',\n"
            "  'supporting_items': ['item 1', 'item 2', 'item 3']\n"
            "}"
        )
        return {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "context_records": [
                {
                    "id": record.id,
                    "title": record.title,
                    "source": record.source,
                    "tag": record.tag,
                    "approval": record.approval,
                    "review_count": record.review_count,
                    "description": record.description,
                }
                for record in records
            ],
        }

    def validate_generated_output(self, payload):
        if not isinstance(payload, dict):
            raise IntelligenceValidationError("Generated response was not returned as JSON.")

        required_fields = ["summary", "recommendation", "confidence", "supporting_items"]
        missing = [field for field in required_fields if field not in payload]
        if missing:
            raise IntelligenceValidationError(
                "Generated response missing required field(s): " + ", ".join(missing)
            )

        summary = str(payload["summary"]).strip()
        recommendation = str(payload["recommendation"]).strip()
        confidence = str(payload["confidence"]).strip()
        supporting_items = payload["supporting_items"]

        if not summary or not recommendation or not confidence:
            raise IntelligenceValidationError("Generated response contained empty summary, recommendation, or confidence values.")
        if not isinstance(supporting_items, list) or not supporting_items or not all(str(item).strip() for item in supporting_items):
            raise IntelligenceValidationError("Generated response must include at least one supporting item.")
        if confidence not in {"High", "Medium", "Low"}:
            confidence = confidence.capitalize()
        if confidence not in {"High", "Medium", "Low"}:
            raise IntelligenceValidationError("Generated confidence must be High, Medium, or Low.")

        return {
            "summary": summary,
            "recommendation": recommendation,
            "confidence": confidence,
            "supporting_items": [str(item).strip() for item in supporting_items[:5]],
        }

    def _extract_json(self, response_data):
        if isinstance(response_data, dict):
            if "choices" in response_data:
                content = response_data["choices"][0]["message"]["content"]
                return self._extract_json(content)
            if "data" in response_data:
                return response_data["data"]
            return response_data

        if isinstance(response_data, str):
            cleaned = response_data.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.strip("`")
                if cleaned.lower().startswith("json"):
                    cleaned = cleaned[4:].strip()
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                match = re.search(r"\{.*\}", cleaned, re.DOTALL)
                if match:
                    return json.loads(match.group(0))
                raise IntelligenceValidationError("Model output could not be decoded as JSON.")

        raise IntelligenceValidationError("Model returned an unsupported response format.")

    def _fallback_generate(self, user_request, records):
        ranked = list(records)
        if not ranked:
            raise ValueError("No records available for intelligence generation.")

        primary = ranked[0]
        recommendation = (
            f"Focus on {primary.title} first. It ranks highest in the retrieved results and has the strongest match "
            f"for the user's request among the available evidence."
        )
        summary = (
            f"Across {len(ranked)} retrieved records, {primary.title} stands out as the leading match because it appears "
            f"earliest in the current result set and is supported by the other returned records."
        )
        confidence = "Low"
        recommendation += " This is a result-order suggestion; personal fit has not been measured."
        supporting_items = [record.title for record in ranked[:3]]
        return {
            "summary": summary,
            "recommendation": recommendation,
            "confidence": confidence,
            "supporting_items": supporting_items,
        }

    def _generate_with_openai(self, user_request, records):
        self.engine_used = "local-deterministic-engine"
        if not self.api_key:
            return self._fallback_generate(user_request, records)

        prompt = self.build_prompt(user_request, records)
        payload = {
            "model": self.model,
            "temperature": 0.3,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": prompt["system_prompt"]},
                {"role": "user", "content": prompt["user_prompt"]},
            ],
        }

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            model_content = response.json()
            extracted = self.validate_generated_output(self._extract_json(model_content))
            if not set(extracted["supporting_items"]).issubset({record.title for record in records}):
                raise IntelligenceValidationError("Supporting titles must belong to the retrieved records.")
            self.engine_used = self.model
            return extracted
        except requests.Timeout:
            return self._fallback_generate(user_request, records)
        except requests.RequestException:
            return self._fallback_generate(user_request, records)
        except (IntelligenceValidationError, ValueError, KeyError, IndexError, TypeError):
            return self._fallback_generate(user_request, records)

    def generate(self, user_request, records, prompt_version="A5-v1"):
        if not records:
            raise ValueError("No records available for intelligence generation.")

        generated = self._generate_with_openai(user_request, records)
        validated = self.validate_generated_output(generated)
        validated["prompt_version"] = prompt_version
        validated["model_used"] = self.engine_used
        validated["generated_at"] = datetime.now(timezone.utc).isoformat()
        return validated
