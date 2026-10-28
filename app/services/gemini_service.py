import os
import json
import logging
import requests
from typing import Dict, Any, Optional, Tuple
from app.core.settings import settings
from app.services.khmer_service import KhmerService

logger = logging.getLogger("AIAnimationStudio.GeminiService")

class GeminiService:
    """Service for generating story scripts, scenes, and visual prompts via Gemini / Groq."""

    SYSTEM_PROMPT = """You are a master Cambodian Video Content Creator, Viral Storyteller, and Educational Filmmaker (អ្នកផលិតមាតិកាវីដេអូអាជីព និងអ្នកនិពន្ធ Script វីដេអូ Viral កំពូល).
Your goal is to write captivating, natural spoken video scripts for social media (TikTok, YouTube Shorts, Reels, Facebook Watch).

CRITICAL SCRIPTWRITING DIRECTIVES (ក្បួនតែង Script ដូចអ្នកធ្វើវីដេអូពិតៗ):
1. ភាសានិយាយរស់រវើក (Natural Spoken Creator Voice - NOT textbook or ancient poetry):
   - ហាមដាច់ខាតសរសេរដូចកំណាព្យ, ដូចពាក្យស្លោកអរូបី, ឬដូចសៀវភៅពុម្ព (No stiff bookish proverbs, no poems, no abstract dense sentences like 'ភាពស្ងប់ស្ងាត់ជាកម្លាំងដើម្បីស្ដាប់...').
   - ត្រូវសរសេរជាភាសានិយាយធម្មជាតិ រស់រវើក ដូចអ្នកធ្វើវីដេអូកំពុងនិយាយជជែកផ្ទាល់ជាមួយទស្សនិកជន!

2. ភាសាខ្មែរសុទ្ធសាធ (100% Pure Khmer - Absolutely NO English or Thai words):
   - ហាមដាច់ខាតប្រើពាក្យអង់គ្លេសក្នុង narration_km (ទោះបីក្នុង Topic មានពាក្យ Introvert ក៏ហាមយកពាក្យ Introvert មកសរសេរក្នុង narration ដែរ ត្រូវប្រើពាក្យ 'មនុស្សស្ងប់ស្ងាត់' ឬ 'មនុស្សមិនសូវមាត់ក')។
   - ហាមដាច់ខាតប្រើអក្សរថៃ (No Thai script \\u0E00-\\u0E7F)។ ត្រូវប្រើតែអក្សរខ្មែរ (\\u1780-\\u17FF)។
   - ហាមដាច់ខាតបកប្រែចំៗបែបកំប្លែង។ ត្រូវប្រើពាក្យខ្មែរធម្មជាតិ រលូន និងមានន័យជ្រាលជ្រៅ។
   - ត្រឹមត្រូវតាមវចនានុក្រម សម្ដេចព្រះសង្ឃរាជ ជួន ណាត។

3. ការបញ្ចេញបញ្ចូលពាក្យ និងឃ្លាតភ្ជាប់អារម្មណ៍ (Conversational Hooks & Transitions):
   - Scene 1 ត្រូវតែជា Hook បើកឆាកទាក់ទាញអារម្មណ៍ ដូចជាការចោទសួរ (ឧ. 'តើអ្នកធ្លាប់ឆ្ងល់ទេថា... ហេតុអ្វីបានជាមនុស្សមួយចំនួន ចូលចិត្តនៅស្ងៀមស្ងាត់ មិនសូវចេះមាត់ក?')។
   - ត្រូវប្រើឃ្លាបញ្ចេញបញ្ចូលទាក់ទាញអារម្មណ៍៖
     * បើកឆាក (Hook): 'តើអ្នកធ្លាប់ឆ្ងល់ទេថា...', 'តើអ្នកធ្លាប់កត់សម្គាល់ទេថា...'
     * ជំទាស់គំនិតទូទៅ (Myth): 'មនុស្សភាគច្រើនតែងយល់ច្រឡំថា...', 'ប៉ុន្តែការពិតទៅ...', 'វាមិនមែនបែបនោះទាល់តែសោះ!'
     * បកស្រាយស៊ីជម្រៅ (Insight): 'សាកគិតមើលទៅ...', 'ខណៈពេលដែលអ្នកដទៃ...', 'តាមពិតទៅ...'
     * សរុបគំនិតមាស (Conclusion): 'ដូច្នេះហើយ...', 'ចូរចាំថា...', 'ចូរមានមោទនភាពលើ...'
   - ប្រើសញ្ញា (...) សម្រាប់ផ្អាកអារម្មណ៍ទាក់ទាញ, សញ្ញាក្បៀស (,) សម្រាប់ដង្ហើម, និងសញ្ញាសួរ (?) សម្រាប់សំនៀងចោទសួរ។ ហាមកាត់ឃ្លាដាច់ៗកំបុតៗ។

4. គំរូ Script វីដេអូ Viral (FEW-SHOT EXEMPLAR):
   Scene 1: "តើអ្នកធ្លាប់ឆ្ងល់ទេថា... ហេតុអ្វីបានជាមនុស្សមួយចំនួន ចូលចិត្តនៅស្ងៀមស្ងាត់ មិនសូវចេះមាត់ក? តើពួកគេអៀន ឬគ្មានអ្វីត្រូវនិយាយ?"
   Scene 2: "មនុស្សភាគច្រើនតែងគិតថា ការនៅស្ងៀមមានន័យថាទន់ខ្សោយ... ប៉ុន្តែការពិតទៅ វាមិនមែនបែបនោះទាល់តែសោះ!"
   Scene 3: "សាកគិតមើលទៅ... ក្នុងចិត្តរបស់ពួកគេពោរពេញដោយការគិតស៊ីជម្រៅ និងការសង្កេតពិភពលោកយ៉ាងច្បាស់លាស់។"
   Scene 4: "ដូច្នេះហើយ... បើអ្នកជាមនុស្សស្ងប់ស្ងាត់ ចូរមានមោទនភាពលើខ្លួនឯង! ព្រោះភាពស្ងប់ស្ងាត់ គឺជាកម្លាំងដ៏អស្ចារ្យបំផុត។"

5. រចនាសម្ព័ន្ធ Story Arc (Engaging Video Narrative):
   - Scene 1: Hook បើកឆាក (ចោទសួរឱ្យចង់ដឹងភ្លាមៗ)
   - Scene 2: The Myth / Common Belief (អ្វីដែលគេតែងយល់ច្រឡំ)
   - Scene 3/4: The Insight / Psychological Truth (ការបកស្រាយចំណុចខ្លាំងស៊ីជម្រៅ)
   - Final Scene: The Golden Takeaway (សារបំផុសចិត្ត និងលើកទឹកចិត្តយ៉ាងកក់ក្តៅ)

6. ប្រវែងល្មមសមរម្យ និងខ្លីខ្លឹម (Concise & Punchy):
   - ក្នុងមួយ Scene ត្រូវមាន ១ ទៅ ២ ល្បះពេញលេញ (ប្រហែល ២០ ទៅ ៣០ ពាក្យ / ៦ ទៅ ៩ វិនាទី) ដើម្បីឱ្យសម្លេងអានរលូន ពីរោះ និងងាយស្រួលមើល subtitle លើអេក្រង់។
   - `image_prompt_en` ត្រូវសរសេរខ្លីខ្លឹមត្រឹម ១ ប្រយោគ (around 15-20 English words describing subject, action, lighting, and style).

IMPORTANT: Output MUST be valid JSON only.
Format:
{
  "title": "Story Title",
  "character_description": "Core character visual details",
  "scenes": [
    {
      "scene_number": 1,
      "narration_km": "តើអ្នកធ្លាប់ឆ្ងល់ទេថា... ហេតុអ្វីបានជាមនុស្សមួយចំនួន ចូលចិត្តនៅស្ងៀមស្ងាត់ មិនសូវចេះមាត់ក? តើពួកគេអៀន ឬគ្មានអ្វីត្រូវនិយាយ?",
      "image_prompt_en": "A thoughtful young Cambodian adult standing in a cozy room, soft cinematic lighting, 3D Pixar style",
      "camera_motion": "talking"
    }
  ]
}"""

    @classmethod
    def test_api_key(cls, api_key: str) -> Tuple[bool, str]:
        """Verify if a Gemini API key is valid using Google's models endpoint."""
        if not api_key or not api_key.strip():
            return False, "API Key is empty."

        clean_key = api_key.strip()
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={clean_key}"
        try:
            logger.info("Verifying Gemini API Key via models endpoint...")
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                models = data.get("models", [])
                supported = []
                for m in models:
                    m_name = m.get("name", "").replace("models/", "")
                    methods = m.get("supportedGenerationMethods", [])
                    if "generateContent" in methods and "flash" in m_name:
                        supported.append(m_name)

                chosen_model = "gemini-3.8-flash"
                for candidate in ["gemini-3.8-flash", "gemini-flash-latest", "gemini-2.5-flash", "gemini-1.5-flash"]:
                    if candidate in supported:
                        chosen_model = candidate
                        break
                else:
                    if supported:
                        chosen_model = supported[0]

                settings.set("gemini_active_model", chosen_model)
                logger.info(f"Gemini Key verified successfully! Active model: {chosen_model}")
                return True, f"Key ត្រឹមត្រូវ និងដំណើរការជោគជ័យ! (Model: {chosen_model})"
            else:
                err_data = resp.json().get("error", {})
                err_msg = err_data.get("message", resp.text)
                return False, f"API Key មិនត្រឹមត្រូវ ({resp.status_code}): {err_msg}"
        except Exception as e:
            return False, f"Connection error: {e}"

    @classmethod
    def test_groq_key(cls, api_key: str) -> Tuple[bool, str]:
        """Verify if a Groq API key is valid using Groq's models endpoint."""
        if not api_key or not api_key.strip():
            return False, "Groq Key is empty."

        clean_key = api_key.strip()
        url = "https://api.groq.com/openai/v1/models"
        headers = {"Authorization": f"Bearer {clean_key}", "Content-Type": "application/json"}
        try:
            logger.info("Verifying Groq API Key via models endpoint...")
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                available_models = [m.get("id") for m in data.get("data", [])]

                # Select best available model from modern Groq lineup
                chosen_model = "openai/gpt-oss-120b"
                for candidate in ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b"]:
                    if candidate in available_models:
                        chosen_model = candidate
                        break

                settings.set("groq_active_model", chosen_model)
                logger.info(f"Groq Key verified successfully! Active model: {chosen_model}")
                return True, f"Groq Key ត្រឹមត្រូវ និងដំណើរការជោគជ័យ! (Model: {chosen_model})"
            else:
                err_msg = resp.json().get("error", {}).get("message", resp.text)
                return False, f"Groq Key មិនត្រឹមត្រូវ: {err_msg}"
        except Exception as e:
            return False, f"Groq Connection error: {e}"

    @classmethod
    def generate_storyboard(cls, topic: str, num_scenes: int = 5, style: str = "3d_pixar", genre: str = "general") -> Dict[str, Any]:
        """
        Generate storyboard with scenes, Khmer narration, and English visual prompts.
        Supports automatic seamless fallback: Gemini -> Groq.
        """
        api_key = settings.get("gemini_api_key", "").strip()
        groq_key = settings.get("groq_api_key", "").strip()

        target_sec = num_scenes * 7
        mins = target_sec // 60
        secs = target_sec % 60
        dur_label = f"{mins} នាទី {secs} វិនាទី" if mins > 0 else f"{secs} វិនាទី"

        is_psychology = (genre in ("psychology", "philosophy", "education")) or any(
            k in topic.lower() for k in [
                "ចិត្តវិទ្យា", "អារម្មណ៍", "មនុស្សស្ងៀមស្ងាត់", "ស្ងៀមស្ងាត់", 
                "ចិត្ត", "ផ្លូវចិត្ត", "ឯកោ", "គិតច្រើន", "អប់រំ", "ទស្សនវិជ្ជា",
                "psychology", "emotion", "mindset", "introvert", "education", "philosophy"
            ]
        )

        if is_psychology:
            genre_context = """CONTENT GENRE: EDUCATIONAL PSYCHOLOGY, EMOTIONS & MINDSET (គំនិតអប់រំ និងចិត្តវិទ្យា)
You are an inspiring Educational Video Content Creator & Life Mindset Mentor.
Your narration must be natural, spoken conversational Khmer, deeply insightful, and relatable:
- Hook the audience immediately with an intriguing rhetorical question (Scene 1).
- Dispel common misunderstandings and myths with empathy and warmth (Scene 2).
- Reveal the hidden inner strength and psychology of the person (Scene 3+).
- Conclude with an empowering, heartwarming golden takeaway (Final Scene).
- Absolutely NO poems, NO textbook proverbs, NO English/Thai loanwords."""
        else:
            genre_context = """CONTENT GENRE: Engaging Narrative Video Storytelling with Conversational Flow and Strong Visuals.
Write like a modern video creator telling an engaging story directly to the viewer."""

        if style in ("aitest_style", "talkmoney_2d", "2d_comic", "stickman", "default") or not style:
            style_instruction = """VISUAL ART STYLE: aitest.mp4 Video Style (TalkMoney inspired storytelling illustration).
- Character: A cute minimalist character with a smooth round white head, expressive black line facial emotions (worried, confident, thoughtful, observing), wearing casual modern clothing.
- Background: Detailed colorful cartoon background of realistic everyday Cambodian scenes (coffee shop counter, espresso machine, street with tuk-tuks, warehouse, local market, rain outside, cozy room).
- Composition: Clean crisp inked outlines, vibrant flat colors, graphic novel storytelling framing, 16:9 widescreen composition."""
        elif style in ("cinematic_zoom", "cinematic_realistic"):
            style_instruction = """VISUAL ART STYLE: Cinematic Movie Scene Still with 35mm lens, atmospheric lighting, depth of field, sharp focus, 4k resolution."""
        else:
            style_instruction = f"VISUAL ART STYLE: {style}"

        user_prompt = f"""Topic: {topic}
Number of Scenes: {num_scenes}
Target Duration: ~{dur_label} (~{target_sec} seconds total)
{genre_context}
{style_instruction}

CRITICAL NARRATION & SCRIPT REQUIREMENTS:
1. Natural Spoken Creator Language: Write in natural conversational Khmer like a real video creator on YouTube / TikTok talking to their audience.
2. Expressive Punctuation: Use natural pauses (... and ,), question marks (?), and exclamation marks (!) so the AI voice (Edge-TTS) speaks with breathing, vocal inflection, and genuine emotion.
3. Subtitle-Friendly Length: Each scene's `narration_km` MUST be 1 to 2 complete, well-formed conversational sentences (around 20 to 30 Khmer words / 6 to 9 seconds of speech).
4. Concise Visual Prompts: Each scene's `image_prompt_en` must be concise (1 short sentence, 15 to 20 English words describing character, action, lighting, and style).
Return only the valid JSON object."""

        errors = []

        # 1. Try Gemini first (if configured)
        if api_key:
            try:
                logger.info("Attempting storyboard generation with Google Gemini...")
                return cls._generate_with_gemini(api_key, user_prompt)
            except Exception as e:
                err_str = str(e)
                logger.warning(f"Gemini generation failed: {err_str}")
                errors.append(f"Gemini: {err_str}")

        # 2. Seamless Fallback to Groq (if Gemini fails/out of quota or if Groq is primary)
        if groq_key:
            try:
                logger.info("Falling back to Groq for storyboard generation...")
                return cls._generate_with_groq(groq_key, user_prompt)
            except Exception as e:
                err_str = str(e)
                logger.warning(f"Groq generation failed: {err_str}")
                errors.append(f"Groq: {err_str}")

        if errors:
            raise RuntimeError("\n".join(errors))
        else:
            raise ValueError("មិនទាន់មាន Gemini API Key ឬ Groq API Key នៅឡើយទេ។ សូមចូលទៅកាន់ Settings ដើម្បីបញ្ចូល Key។")

    @classmethod
    def _generate_with_gemini(cls, api_key: str, prompt: str) -> Dict[str, Any]:
        payload = {
            "contents": [
                {"role": "user", "parts": [{"text": cls.SYSTEM_PROMPT + "\n\n" + prompt}]}
            ],
            "generationConfig": {
                "temperature": 0.7,
                "responseMimeType": "application/json"
            }
        }
        headers = {"Content-Type": "application/json"}

        candidates = ["gemini-3.8-flash", "gemini-flash-latest", "gemini-2.5-flash", "gemini-1.5-flash"]
        active_model = settings.get("gemini_active_model")
        if active_model and active_model in candidates:
            candidates.remove(active_model)
            candidates.insert(0, active_model)

        last_error = ""
        for model in candidates:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=45)
                if resp.status_code == 200:
                    data = resp.json()
                    raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                    settings.set("gemini_active_model", model)
                    parsed = json.loads(raw_text)
                    return cls._sanitize_storyboard(parsed)
                else:
                    err_obj = resp.json().get("error", {})
                    last_error = err_obj.get("message", resp.text)
                    logger.warning(f"Gemini {model} error: {last_error}")
                    if "RESOURCE_EXHAUSTED" in resp.text or "quota" in last_error.lower():
                        raise RuntimeError(f"Gemini quota exceeded: {last_error}")
            except Exception as e:
                last_error = str(e)
                if "quota" in str(e).lower() or "RESOURCE_EXHAUSTED" in str(e):
                    raise

        raise RuntimeError(f"Gemini API error: {last_error}")

    @classmethod
    def _sanitize_storyboard(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize storyboard text, correcting Unicode order and spelling."""
        if not isinstance(data, dict):
            return data
        if "title" in data and isinstance(data["title"], str):
            data["title"] = KhmerService.clean_text(data["title"])
        for s in data.get("scenes", []):
            if "narration_km" in s and isinstance(s["narration_km"], str):
                s["narration_km"] = KhmerService.clean_text(s["narration_km"])
        return data

    @classmethod
    def _generate_with_groq(cls, groq_key: str, prompt: str) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"}
        
        # Modern active models on Groq
        candidates = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b"]
        active_model = settings.get("groq_active_model")
        if active_model and active_model in candidates:
            candidates.remove(active_model)
            candidates.insert(0, active_model)

        last_error = ""
        for model in candidates:
            url = "https://api.groq.com/openai/v1/chat/completions"
            max_toks = 950 if "qwen" in model else 2500
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": cls.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.7,
                "max_tokens": max_toks
            }
            try:
                logger.info(f"Generating story using Groq model: {model}...")
                resp = requests.post(url, headers=headers, json=payload, timeout=45)
                if resp.status_code == 200:
                    data = resp.json()
                    raw_text = data["choices"][0]["message"]["content"]
                    settings.set("groq_active_model", model)
                    logger.info(f"Groq story generated successfully with model: {model}")
                    parsed = json.loads(raw_text)
                    return cls._sanitize_storyboard(parsed)
                else:
                    last_error = resp.json().get("error", {}).get("message", resp.text)
                    logger.warning(f"Groq model {model} failed: {last_error}")
            except Exception as e:
                last_error = str(e)

        raise RuntimeError(f"Groq API error: {last_error}")
