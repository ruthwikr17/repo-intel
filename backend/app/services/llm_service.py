import asyncio
import json

import google.generativeai as genai
from groq import AsyncGroq

from app.config import get_settings
from app.services.prompts import (
    prompt_architecture,
    prompt_code_quality_report,
    prompt_code_walkthrough,
    prompt_contribution_suggestions,
    prompt_contributor_guide_narrative,
    prompt_executive_summary,
    prompt_common_patterns,
    prompt_gotchas_and_tips,
    prompt_project_summary,
    prompt_setup_guide,
)

settings = get_settings()


# ─── Gemini Client ────────────────────────────────────────────────────────────


def get_gemini_model(api_key: str):
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(
        model_name="gemini-3.6-flash",
        generation_config=genai.GenerationConfig(
            temperature=0.3,
            max_output_tokens=3000,
        ),
    )


async def call_gemini(prompt: str, api_key: str) -> str:
    """Call Gemini API with given prompt and API key."""
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name="gemini-3.6-flash",
            generation_config=genai.GenerationConfig(
                temperature=0.3,
                max_output_tokens=8192,  # Changed from 2048 to 8192
            ),
        )
        response = await asyncio.to_thread(model.generate_content, prompt)
        return response.text
    except Exception as e:
        # Log but don't crash - return empty string, Groq will fill in
        print(f"Gemini error: {str(e)}")
        return ""


# ─── Groq Client ─────────────────────────────────────────────────────────────


async def call_groq(prompt: str, max_retries: int = 3) -> str:
    """Call Groq API with given prompt and automatic retry on rate limit."""
    client = AsyncGroq(api_key=settings.groq_api_key)
    models_to_try = ["qwen/qwen3.8-27b", "openai/gpt-oss-120b"]
    
    for model_name in models_to_try:
        for attempt in range(max_retries):
            try:
                response = await client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=8192,  # Changed from 2048 to 8192
                )
                return response.choices[0].message.content
            except Exception as e:
                err_str = str(e)
                # If rate limited (429), wait and retry
                if "429" in err_str or "rate_limit_exceeded" in err_str:
                    wait_time = (2 ** attempt) * 2 + 1  # 3s, 5s, 9s
                    print(f"Groq rate limit on {model_name} (attempt {attempt+1}/{max_retries}), waiting {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    print(f"Groq error on {model_name}: {err_str}")
                    break  # Try next model fallback
                    
    return f"[Groq Error: Rate limit or service unavailable after retries]"


# ─── Tier 1: Hybrid (Gemini + Groq) ─────────────────────────────────────────


async def run_tier1_analysis(repo_data: dict, gemini_key: str) -> dict:
    """
    Tier 1: High quality hybrid.
    Gemini handles complex reasoning tasks.
    Groq handles structured generation tasks.
    All 9 run in parallel via asyncio.gather.
    """
    (
        summary,
        architecture,
        walkthrough,
        quality_report,
        setup_guide,
        contributor_narrative,
        executive_summary,
        common_patterns,
        gotchas,
    ) = await asyncio.gather(
        call_groq(prompt_project_summary(repo_data)),
        call_gemini(prompt_architecture(repo_data), gemini_key),
        call_gemini(prompt_code_walkthrough(repo_data), gemini_key),
        call_gemini(prompt_code_quality_report(repo_data), gemini_key),
        call_groq(prompt_setup_guide(repo_data)),
        call_groq(prompt_contributor_guide_narrative(repo_data)),
        call_groq(prompt_executive_summary(repo_data)),
        call_gemini(prompt_common_patterns(repo_data), gemini_key),
        call_groq(prompt_gotchas_and_tips(repo_data)),
    )

    # Fallback: if Gemini failed, use Groq for those calls
    if not architecture:
        architecture = await call_groq(prompt_architecture(repo_data))
    if not walkthrough:
        walkthrough = await call_groq(prompt_code_walkthrough(repo_data))
    if not quality_report:
        quality_report = await call_groq(prompt_code_quality_report(repo_data))
    if not common_patterns:
        common_patterns = await call_groq(prompt_common_patterns(repo_data))

    return {
        "quality_tier": "HIGH",
        "apis_used": ["gemini-3.6-flash", "groq-gpt-oss-120b"],
        "summary": summary,
        "architecture_explanation": architecture,
        "code_walkthrough": walkthrough,
        "code_quality_report": quality_report,
        "setup_guide": setup_guide,
        "contributor_guide_narrative": contributor_narrative,
        "executive_summary": executive_summary,
        "common_patterns": common_patterns,
        "gotchas_and_tips": gotchas,
    }


# ─── Tier 2: Groq Only ───────────────────────────────────────────────────────


async def run_tier2_analysis(repo_data: dict) -> dict:
    """
    Tier 2: All Groq fallback.
    Used when both Gemini projects are exhausted.
    Same prompts, all sent to Groq.
    """
    (
        summary,
        architecture,
        walkthrough,
        quality_report,
        setup_guide,
        contributor_narrative,
        executive_summary,
        common_patterns,
        gotchas,
    ) = await asyncio.gather(
        call_groq(prompt_project_summary(repo_data)),
        call_groq(prompt_architecture(repo_data)),
        call_groq(prompt_code_walkthrough(repo_data)),
        call_groq(prompt_code_quality_report(repo_data)),
        call_groq(prompt_setup_guide(repo_data)),
        call_groq(prompt_contributor_guide_narrative(repo_data)),
        call_groq(prompt_executive_summary(repo_data)),
        call_groq(prompt_common_patterns(repo_data)),
        call_groq(prompt_gotchas_and_tips(repo_data)),
    )

    return {
        "quality_tier": "MEDIUM",
        "apis_used": ["groq-gpt-oss-120b"],
        "summary": summary,
        "architecture_explanation": architecture,
        "code_walkthrough": walkthrough,
        "code_quality_report": quality_report,
        "setup_guide": setup_guide,
        "contributor_guide_narrative": contributor_narrative,
        "executive_summary": executive_summary,
        "common_patterns": common_patterns,
        "gotchas_and_tips": gotchas,
    }



# ─── Master LLM Analysis ─────────────────────────────────────────────────────


async def run_llm_analysis(repo_data: dict, gemini_key: str | None = None) -> dict:
    """
    Master function called by other services.
    If gemini_key is provided: runs Tier 1 (hybrid).
    If gemini_key is None: runs Tier 2 (Groq only).
    """
    if gemini_key:
        return await run_tier1_analysis(repo_data, gemini_key)
    else:
        return await run_tier2_analysis(repo_data)


# ─── AI Contribution Suggestions ─────────────────────────────────────────────


async def generate_ai_opportunities(repo_data: dict, gemini_key: str = None) -> list:
    """
    Use LLM to generate feature/doc/testing contribution suggestions.
    Returns list of opportunity dicts.
    """
    prompt = prompt_contribution_suggestions(repo_data)

    raw = ""
    if gemini_key:
        raw = await call_gemini(prompt, gemini_key)
    if not raw:
        raw = await call_groq(prompt)

    if not raw:
        print("[AI Suggestions] Empty response from both models")
        return []

    try:
        clean = raw.strip()

        # Strip markdown code fences
        if "```json" in clean:
            clean = clean.split("```json")[1].split("```")[0].strip()
        elif "```" in clean:
            parts = clean.split("```")
            if len(parts) >= 2:
                clean = parts[1].strip()

        # Find the JSON array boundaries
        start = clean.find('[')
        end = clean.rfind(']')

        if start == -1:
            print(f"[AI Suggestions] No JSON array found in response")
            return []

        if end == -1 or end <= start:
            # Response was truncated - try to salvage complete objects
            print(f"[AI Suggestions] Response truncated, attempting salvage")
            clean = clean[start:]
            # Count complete objects by counting balanced braces
            salvaged = []
            depth = 0
            current_obj_start = -1
            i = 0
            in_string = False
            escape_next = False

            for i, char in enumerate(clean):
                if escape_next:
                    escape_next = False
                    continue
                if char == '\\' and in_string:
                    escape_next = True
                    continue
                if char == '"' and not escape_next:
                    in_string = not in_string
                    continue
                if in_string:
                    continue
                if char == '{':
                    if depth == 1:
                        current_obj_start = i
                    depth += 1
                elif char == '}':
                    depth -= 1
                    if depth == 1 and current_obj_start != -1:
                        obj_str = clean[current_obj_start:i+1]
                        try:
                            obj = json.loads(obj_str)
                            salvaged.append(obj)
                        except Exception:
                            pass
                        current_obj_start = -1

            if salvaged:
                print(f"[AI Suggestions] Salvaged {len(salvaged)} complete suggestions")
                return salvaged[:12]
            return []

        json_str = clean[start:end+1]
        suggestions = json.loads(json_str)

        if isinstance(suggestions, list):
            print(f"[AI Suggestions] Successfully parsed {len(suggestions)} suggestions")
            return suggestions[:12]

    except Exception as e:
        print(f"[AI Suggestions] Parse failed: {e}")
        print(f"[AI Suggestions] Raw response first 500 chars: {raw[:500]}")
        return []

    return []
