"""LLM layer for MedRAG — loads .env on import so GEMINI_MODEL is always applied."""

import json
import os
import re
import time

from dotenv import load_dotenv

load_dotenv()

from langchain_google_genai import ChatGoogleGenerativeAI

try:
    from langchain_google_genai.chat_models import ChatGoogleGenerativeAIError
except ImportError:
    ChatGoogleGenerativeAIError = Exception

try:
    from google import genai as google_genai
    from google.genai.errors import ClientError as GenaiClientError
    _GENAI_SDK = True
except ImportError:
    google_genai = None
    GenaiClientError = Exception
    _GENAI_SDK = False

APP_LLM_VERSION = "2.0.0"

PROBE_PROMPT = "Reply with exactly one word: OK"

# Common typo → real model id
MODEL_ALIASES = {
    "gemini-1.5-flash-lite": "gemini-2.0-flash-lite",
}

DEFAULT_MODEL_FALLBACKS = (
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
)

MEDICAL_DISCLAIMER = (
    "This is general wellness information only—not medical diagnosis or treatment. "
    "Always consult a licensed healthcare professional for personal medical decisions."
)

EMERGENCY_NOTICE = (
    "URGENT: Chest pain or suspected heart symptoms can be life-threatening. "
    "Call emergency services (911 / local emergency number) now—do not wait for app advice."
)

PROMPTS = {
    "general": """You are a medical health education assistant. Answer using ONLY the retrieved medical context below.

Guidelines:
- Give clear, practical general health guidance grounded in the context
- Mention relevant values, ranges, or guidelines when present in the context
- If the user reports chest pain, acute symptoms, or emergency signs, tell them to seek emergency care immediately
- If the context does not support an answer, say what is missing—do not invent clinical facts
- End with this disclaimer on its own line: {disclaimer}

Question: {query}
Context: {context}
Answer:""",
    "diet": """You are a clinical nutrition assistant. Provide diet and meal guidance using ONLY the retrieved context.

Guidelines:
- Suggest foods, portions, and patterns supported by the context
- Note contraindications, allergies, or conditions if mentioned in the question or context
- Structure advice as: summary, daily pattern, foods to emphasize/limit, and hydration
- If context is insufficient, state limitations clearly
- End with this disclaimer on its own line: {disclaimer}

Request: {query}
Context: {context}
Diet guidance:""",
    "lab_tests": """You are a health literacy assistant helping interpret medical test reports using ONLY the retrieved lab/test context.

Guidelines:
- Explain what each relevant test measures in plain language
- Compare reported values to reference ranges when available in the context
- Flag results that appear high, low, or abnormal based on the context only
- Do NOT diagnose diseases; suggest follow-up with a clinician when appropriate
- If a value or test is not in the context, say so
- End with this disclaimer on its own line: {disclaimer}

Question: {query}
Context: {context}
Interpretation:""",
}

EMERGENCY_KEYWORDS = (
    "chest pain",
    "heart attack",
    "can't breathe",
    "cannot breathe",
    "shortness of breath",
    "stroke",
    "unconscious",
    "severe bleeding",
)

MODE_TITLES = {
    "general": "Guidance from your documents",
    "diet": "Diet guidance from your documents",
    "lab_tests": "Lab-related notes from your documents",
}


def _clean_api_key() -> str:
    return (os.getenv("GOOGLE_API_KEY") or "").strip().strip("'\"")


def _llm_enabled() -> bool:
    return os.getenv("USE_LLM", "true").strip().lower() not in ("0", "false", "no", "off")


def _is_quota_error(err: Exception) -> bool:
    text = str(err).lower()
    return "429" in text or "resource_exhausted" in text or "quota" in text


def _is_model_not_found(err: Exception) -> bool:
    text = str(err).lower()
    return (
        "404" in text
        or "not found" in text
        or "not supported for generatecontent" in text
    )


def _normalize_model(name: str) -> str:
    name = name.strip()
    return MODEL_ALIASES.get(name, name)


def _model_chain() -> list[str]:
    primary = _normalize_model(os.getenv("GEMINI_MODEL", "gemini-2.0-flash-lite"))
    extra = os.getenv("GEMINI_MODEL_FALLBACKS", ",".join(DEFAULT_MODEL_FALLBACKS))
    chain = [primary] + [_normalize_model(m) for m in extra.split(",") if m.strip()]
    seen: set[str] = set()
    ordered: list[str] = []
    for m in chain:
        if m not in seen:
            seen.add(m)
            ordered.append(m)
    return ordered


def _classify_api_error(err: Exception, model: str) -> tuple[bool, str]:
    """Return (should_try_next_model, short_message)."""
    if _is_model_not_found(err):
        return True, f"Model not found (skip): {model}"
    if _is_quota_error(err):
        return True, f"Quota/rate limit on {model}"
    return False, str(err).split("\n")[0][:200]


def _query_terms(query: str) -> set[str]:
    stop = {
        "a", "an", "the", "i", "my", "have", "has", "had", "is", "are", "was", "in", "on",
        "for", "to", "and", "or", "with", "what", "how", "do", "does", "can", "should",
    }
    words = re.findall(r"[a-z0-9]+", query.lower())
    return {w for w in words if len(w) > 2 and w not in stop}


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    cleaned = []
    for p in parts:
        s = re.sub(r"\s+", " ", p).strip()
        if len(s) >= 25:
            cleaned.append(s)
    return cleaned


class LLMProcessor:
    def __init__(self):
        self.model_name = _model_chain()[0]
        self._llm_cache: dict[str, ChatGoogleGenerativeAI] = {}
        self._genai_client = None
        self._rate_status: dict | None = None

    def _get_genai_client(self):
        if self._genai_client is None and _GENAI_SDK and google_genai:
            self._genai_client = google_genai.Client(api_key=_clean_api_key())
        return self._genai_client

    def _get_llm(self, model: str) -> ChatGoogleGenerativeAI:
        if model not in self._llm_cache:
            self._llm_cache[model] = ChatGoogleGenerativeAI(
                model=model,
                google_api_key=_clean_api_key(),
                temperature=0.1,
                max_output_tokens=1024,
            )
        return self._llm_cache[model]

    def is_available(self) -> bool:
        return _llm_enabled() and bool(_clean_api_key())

    def check_api_rate(self, force_refresh: bool = False) -> dict:
        """Send a tiny probe to Gemini before the user's real question."""
        if not force_refresh and self._rate_status is not None:
            return self._rate_status

        started = time.perf_counter()
        models_tried: list[str] = []

        if not _llm_enabled():
            self._rate_status = {
                "ok": False,
                "model": None,
                "probe_reply": None,
                "reason": "LLM disabled (USE_LLM=false). Excerpt-only mode.",
                "latency_ms": 0,
                "models_tried": models_tried,
            }
            return self._rate_status

        if not _clean_api_key():
            self._rate_status = {
                "ok": False,
                "model": None,
                "probe_reply": None,
                "reason": "GOOGLE_API_KEY is not set in .env",
                "latency_ms": 0,
                "models_tried": models_tried,
            }
            return self._rate_status

        last_error = "Unknown error"
        for model in _model_chain():
            models_tried.append(model)
            try:
                if _GENAI_SDK:
                    reply = self._invoke_genai_sdk(model, PROBE_PROMPT)
                else:
                    reply = self._invoke_langchain(model, PROBE_PROMPT)
                latency_ms = int((time.perf_counter() - started) * 1000)
                self.model_name = model
                self._rate_status = {
                    "ok": True,
                    "model": model,
                    "probe_reply": reply or "(empty)",
                    "reason": "API reachable — AI summaries enabled",
                    "latency_ms": latency_ms,
                    "models_tried": models_tried,
                }
                return self._rate_status
            except Exception as e:
                try_next, last_error = _classify_api_error(e, model)
                if try_next:
                    print(f"  {last_error}")
                    continue
                break

        latency_ms = int((time.perf_counter() - started) * 1000)
        self._rate_status = {
            "ok": False,
            "model": None,
            "probe_reply": None,
            "reason": (
                f"{last_error}. Valid examples: gemini-2.0-flash-lite, gemini-2.0-flash, gemini-1.5-flash"
                if models_tried
                else "No models configured"
            ),
            "latency_ms": latency_ms,
            "models_tried": models_tried,
        }
        return self._rate_status

    @staticmethod
    def print_rate_status(status: dict) -> None:
        print("-" * 60)
        print("Gemini API pre-check")
        if status.get("ok"):
            print(f"  Status:   OK")
            print(f"  Model:    {status.get('model')}")
            print(f"  Probe:    {status.get('probe_reply')}")
            print(f"  Latency:  {status.get('latency_ms')} ms")
            print(f"  Message:  {status.get('reason')}")
        else:
            print(f"  Status:   UNAVAILABLE")
            print(f"  Message:  {status.get('reason')}")
            tried = status.get("models_tried") or []
            if tried:
                print(f"  Tried:    {', '.join(tried)}")
            print(f"  Latency:  {status.get('latency_ms')} ms")
            print("  Next:     Answers will use document excerpts only.")
        print("-" * 60)

    def _needs_emergency_notice(self, query: str) -> bool:
        q = query.lower()
        return any(kw in q for kw in EMERGENCY_KEYWORDS)

    def _build_context(self, search_results: list) -> str:
        if not search_results:
            return "No relevant medical content found in the knowledge base."
        parts = []
        for i, result in enumerate(search_results, 1):
            doc_type = result.get("type", "unknown")
            content = result.get("content", "").strip()
            if content:
                parts.append(f"[Source {i} | type: {doc_type}]\n{content}")
        return "\n\n".join(parts)

    def _smart_excerpt_answer(self, query: str, search_results: list, mode: str) -> str:
        """Structured answer from RAG chunks when Gemini is unavailable."""
        terms = _query_terms(query)
        scored: list[tuple[float, str]] = []

        for result in search_results:
            content = result.get("content", "")
            for sentence in _split_sentences(content):
                lower = sentence.lower()
                score = sum(1 for t in terms if t in lower)
                if "•" in sentence or sentence.strip().startswith("-"):
                    score += 1
                if any(k in lower for k in ("heart", "diet", "sodium", "vegetable", "protein", "portion")):
                    score += 0.5
                if score > 0 or not terms:
                    scored.append((score, sentence))

        scored.sort(key=lambda x: (-x[0], -len(x[1])))
        top = []
        seen = set()
        for _, sent in scored:
            key = sent[:80]
            if key in seen:
                continue
            seen.add(key)
            top.append(sent)
            if len(top) >= 10:
                break

        if not top:
            for result in search_results:
                chunk = result.get("content", "").strip()
                if chunk:
                    top.append(chunk[:600] + ("..." if len(chunk) > 600 else ""))
                    break

        title = MODE_TITLES.get(mode, MODE_TITLES["general"])
        lines = [f"{title} (from your uploaded files — not AI-generated)", ""]

        if self._needs_emergency_notice(query):
            lines.extend([EMERGENCY_NOTICE, ""])

        lines.append(f"Your question: {query}")
        lines.append("")
        lines.append("Key points matched in your documents:")
        for sent in top:
            bullet = sent if sent.startswith("•") else f"• {sent}"
            lines.append(bullet)

        lines.extend([
            "",
            "For a full AI-written summary, add a new Gemini API key at https://aistudio.google.com/apikey",
            "(free tier limits vary by model; try GEMINI_MODEL=gemini-2.0-flash-lite in .env).",
            "",
            MEDICAL_DISCLAIMER,
        ])
        return "\n".join(lines)

    def _fallback_response(
        self, query: str, search_results: list, error_msg: str, mode: str = "general"
    ) -> str:
        body = self._smart_excerpt_answer(query, search_results, mode)
        return f"Note: {error_msg}\n\n{body}"

    def _parse_retry_seconds(self, err: Exception) -> float | None:
        match = re.search(r"retry in ([\d.]+)s", str(err), re.IGNORECASE)
        return float(match.group(1)) if match else None

    def _invoke_genai_sdk(self, model: str, prompt: str) -> str:
        client = self._get_genai_client()
        if not client:
            raise RuntimeError("google-genai SDK not available")
        response = client.models.generate_content(model=model, contents=prompt)
        text = getattr(response, "text", None) or ""
        if not text and hasattr(response, "candidates") and response.candidates:
            parts = response.candidates[0].content.parts
            text = "".join(getattr(p, "text", "") or "" for p in parts)
        return text.strip()

    def _invoke_langchain(self, model: str, prompt: str) -> str:
        response = self._get_llm(model).invoke(prompt)
        return (response.content or "").strip()

    def _invoke_with_model_fallbacks(self, prompt: str, preferred_model: str | None = None) -> str:
        last_error: Exception | None = None
        chain = _model_chain()
        if preferred_model:
            models = [preferred_model] + [m for m in chain if m != preferred_model]
        else:
            models = chain

        for model in models:
            for attempt in range(2):
                try:
                    if _GENAI_SDK:
                        text = self._invoke_genai_sdk(model, prompt)
                    else:
                        text = self._invoke_langchain(model, prompt)
                    if text:
                        self.model_name = model
                        return text
                except (ChatGoogleGenerativeAIError, GenaiClientError, Exception) as e:
                    last_error = e
                    try_next, msg = _classify_api_error(e, model)
                    if try_next:
                        print(f"  {msg}")
                        break
                    if attempt == 0:
                        wait = self._parse_retry_seconds(e) or 5.0
                        time.sleep(min(wait, 15))
                        continue
                    break

        if last_error:
            raise last_error
        raise RuntimeError("All Gemini models failed")

    def process_query(self, query: str, search_results: list, mode: str = "general") -> str:
        mode = mode if mode in PROMPTS else "general"

        if not _llm_enabled():
            return self._smart_excerpt_answer(query, search_results, mode)

        if not _clean_api_key():
            return self._fallback_response(
                query, search_results, "GOOGLE_API_KEY is not set.", mode
            )

        status = self._rate_status or self.check_api_rate()
        if not status.get("ok"):
            return self._fallback_response(
                query, search_results, status.get("reason", "API check failed"), mode
            )

        context = self._build_context(search_results)
        prompt = PROMPTS[mode].format(
            query=query,
            context=context,
            disclaimer=MEDICAL_DISCLAIMER,
        )

        try:
            answer = self._invoke_with_model_fallbacks(
                prompt, preferred_model=status.get("model")
            )
            if self._needs_emergency_notice(query):
                answer = f"{EMERGENCY_NOTICE}\n\n{answer}"
            return answer
        except Exception as e:
            err_short = "Gemini API unavailable (quota or invalid key)."
            if _is_quota_error(e):
                err_short = (
                    "All configured Gemini models hit quota limits. "
                    "Create a new key at https://aistudio.google.com/apikey"
                )
            self._rate_status = None
            return self._fallback_response(query, search_results, err_short, mode)

    def _ensure_llm_ready(self) -> bool:
        status = self._rate_status or self.check_api_rate()
        return bool(status.get("ok"))

    def _gemini_text(self, prompt: str) -> str:
        status = self._rate_status or self.check_api_rate()
        if not status.get("ok"):
            raise RuntimeError(status.get("reason", "Gemini API unavailable"))
        return self._invoke_with_model_fallbacks(prompt, preferred_model=status.get("model"))

    def extract_report_findings(self, report_text: str, patient_notes: str = "") -> list[str]:
        prompt = f"""You are a medical report analyst. Read this patient report and list findings.

Return ONLY a JSON array of strings (5-12 items). Each item: one finding, abnormal value, or potential issue.
Use cautious language ("may suggest", "consistent with") — do not state definitive diagnoses.
Include relevant lab values with numbers when present.

Patient notes: {patient_notes or "None"}

Report:
{report_text}

JSON array:"""
        try:
            raw = self._gemini_text(prompt)
            items = _parse_json_array_helper(raw)
            if items:
                return items
        except Exception as e:
            print(f"  Gemini findings extraction failed: {e}")
        return self._heuristic_findings(report_text)

    def evaluate_and_ask(self, report_text: str, findings: list[str], patient_notes: str, knowledge_hits: list[dict] = None) -> str:
        findings_block = "\n".join(f"- {f}" for f in findings)
        context = self._build_context(knowledge_hits) if knowledge_hits else "None"
        prompt = f"""You are a medical, dietary, and fitness analyst. You need to diagnose the patient and create the most comprehensive, personalized diet and fitness plan possible.
Review the patient's report, initial findings, the conversation history, and the medical Knowledge Base context.

Use the Knowledge Base to inform your diagnostic logic. Ensure your questions are grounded in confirming or ruling out conditions or symptoms based on this medical data.
Review the patient's report, initial findings, and the conversation history.

To produce a high-quality fitness and dietary report, you MUST know:
1. The patient's current daily diet and typical meals.
2. Any food allergies, intolerances, or dietary preferences.
3. Their current fitness level, exercise routine, and physical limitations.
4. Their specific health and fitness goals (e.g., weight loss, muscle gain, stamina, managing their condition).
5. Their daily lifestyle (e.g., sedentary job, active job, sleep habits).

Determine if you have ALL of this information. 
If you DO have comprehensive information across all these areas, reply EXACTLY with: [READY]
If you NEED more information, reply with EXACTLY 1 simple, clear question. 

Each question MUST be multiple choice with exactly 4 simple options. Format each question EXACTLY like this:
1. [Your simple question text here?] [Make sure that question is for doctor perspective eg. "Does patient...."]
   A) [Option 1]
   B) [Option 2]
   C) [Option 3]
   D) [Option 4]

Do not include any other conversational text. Output ONLY the questions formatted as above.

Patient context / Q&A history: {patient_notes or "None"}

Report (excerpt):
{report_text[:8000]}

Initial Findings:
{findings_block}

Knowledge Base Context (Diagnosis):
{context}

Your response (either [READY] or your questions):"""
        try:
            return self._gemini_text(prompt)
        except Exception as e:
            print(f"  Gemini evaluation failed: {e}")
            return "[READY]"

    def generate_summary(self, report_text: str, findings: list[str], patient_notes: str, previous_summary: str = "") -> str:
        findings_block = "\n".join(f"- {f}" for f in findings)
        prompt = f"""You are a clinical assistant. Create a highly concise Markdown summary of the patient's current diagnosis and findings based on their medical report and the Q&A history.

Do not include a diet or fitness plan.
At the very end of your summary, add a "General Advice" section with any other information or lifestyle advice you recommend based on the findings.

IMPORTANT: You are updating an existing summary based on new Q&A. Retain the original formatting and general structure as much as possible. Only append or gently modify the diagnosis and advice based on new Q&A if absolutely necessary. Do not rewrite everything from scratch heavily.

Previous Summary:
{previous_summary or "None"}

Report (excerpt):
{report_text[:12000]}

Findings:
{findings_block}

Q&A History:
{patient_notes or "None"}

Updated Summary:"""
        try:
            return self._gemini_text(prompt)
        except Exception as e:
            print(f"  Gemini summary generation failed: {e}")
            return "Could not generate summary."

    def plan_rag_queries(self, findings: list[str], patient_notes: str = "") -> list[str]:
        findings_block = "\n".join(f"- {f}" for f in findings) or "- general heart-healthy nutrition"
        prompt = f"""You plan searches in a nutrition and medical education knowledge base.

Given these report findings and patient notes, return ONLY a JSON array of 5-10 short search queries
to find diet guidelines, lifestyle advice, and condition-specific nutrition (not diagnosis).

Patient notes: {patient_notes or "None"}
Findings:
{findings_block}

JSON array of search strings:"""
        try:
            raw = self._gemini_text(prompt)
            items = _parse_json_array_helper(raw)
            if items:
                return items
        except Exception as e:
            print(f"  Gemini RAG planning failed: {e}")
        return self._heuristic_rag_queries(findings)

    def synthesize_care_plan(
        self,
        report_text: str,
        findings: list[str],
        knowledge_hits: list[dict],
        patient_notes: str = "",
    ) -> str:
        findings_block = "\n".join(f"- {f}" for f in findings)
        context = self._build_context(knowledge_hits)
        prompt = f"""You are a clinical nutrition and health education assistant.

Use the PATIENT REPORT for clinical context and the KNOWLEDGE BASE for diet/lifestyle recommendations only.
Do not invent facts not supported by the inputs.

Produce ONLY a highly standardized JSON object. Do not wrap in markdown code blocks. The JSON must exactly match this format:
{{
  "patient_info": {{
    "name": "Patient Name or Anonymous",
    "age": "Age or Unknown",
    "gender": "Gender or Unknown",
    "blood_type": "Blood Type or Unknown",
    "conditions": ["List of main conditions"],
    "medications": ["List of main medications"]
  }},
  "summary": "Clear, concise diagnosis and summary of the patient's condition based on the report findings...",
  "general_advice": "Practical lifestyle and monitoring guidance...",
  "diet": "Structured 7-day weekly meal plan. FOR EACH DAY (Day 1-7), you MUST create three distinct sections: **Breakfast**, **Lunch**, and **Dinner**. You MUST use DOUBLE NEWLINES (\\n\\n) between these sections so they appear on new lines. For each meal, provide 2 healthy options grounded in the KNOWLEDGE BASE. USE RICH MARKDOWN: ### Day X headers and bullet points.",
  "fitness": "Structured 7-day weekly exercise routine. YOU MUST USE RICH MARKDOWN FORMATTING: Use Markdown Headers (### Day 1), bold text, and bullet points for exercises, sets, reps, and durations.",
  "important": "What requires clinician follow-up. End with exactly this disclaimer: {MEDICAL_DISCLAIMER}"
}}

Patient notes / Q&A history: {patient_notes or "None"}

Report (excerpt):
{report_text[:12000]}

Findings already identified:
{findings_block}

Knowledge base (RAG):
{context}

Standardized Markdown Care Plan:"""
        try:
            return self._gemini_text(prompt)
        except Exception as e:
            return self._care_plan_fallback(findings, knowledge_hits, str(e))

    @staticmethod
    def _heuristic_findings(report_text: str) -> list[str]:
        findings = []
        patterns = [
            (r"(?i)hemoglobin[:\s]+([\d.]+)", "Hemoglobin: {}"),
            (r"(?i)glucose[:\s]+([\d.]+)", "Blood glucose: {}"),
            (r"(?i)cholesterol[:\s]+([\d.]+)", "Cholesterol: {}"),
            (r"(?i)LDL[:\s]+([\d.]+)", "LDL: {}"),
            (r"(?i)HDL[:\s]+([\d.]+)", "HDL: {}"),
            (r"(?i)triglycerides?[:\s]+([\d.]+)", "Triglycerides: {}"),
            (r"(?i)(high|low|elevated|abnormal)", "Flagged term in report: {}"),
        ]
        for pat, tmpl in patterns:
            for m in re.finditer(pat, report_text):
                findings.append(tmpl.format(m.group(0)[:80]))
                if len(findings) >= 8:
                    break
        if not findings:
            snippet = re.sub(r"\s+", " ", report_text[:400]).strip()
            findings = [f"Report summary excerpt: {snippet}..."]
        return findings[:10]

    @staticmethod
    def _heuristic_rag_queries(findings: list[str]) -> list[str]:
        base = [
            "heart healthy diet guidelines",
            "low sodium nutrition",
            "diabetes diet recommendations",
            "cholesterol lowering foods",
        ]
        for f in findings[:4]:
            base.append(f"{f} diet nutrition")
        return list(dict.fromkeys(base))[:8]

    def _care_plan_fallback(self, findings: list[str], knowledge_hits: list[dict], err: str) -> str:
        body = self._smart_excerpt_answer(
            "diet and lifestyle for report findings",
            knowledge_hits,
            "diet",
        )
        findings_txt = "\n".join(f"- {f}" for f in findings)
        return (
            f"Note: Full AI plan unavailable ({err}).\n\n"
            f"## Potential issues (from report)\n{findings_txt}\n\n"
            f"## Guidance from knowledge base\n{body}"
        )


def _parse_json_array_helper(text: str) -> list[str]:
    text = (text or "").strip()
    match = re.search(r"\[[\s\S]*\]", text)
    if match:
        try:
            data = json.loads(match.group())
            if isinstance(data, list):
                return [str(x).strip() for x in data if str(x).strip()]
        except json.JSONDecodeError:
            pass
    lines = []
    for line in text.splitlines():
        line = re.sub(r"^[\s\-\*\d.)]+", "", line).strip()
        if len(line) > 3:
            lines.append(line)
    return lines[:12]
