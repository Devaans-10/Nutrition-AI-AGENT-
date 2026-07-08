# Service module for IBM watsonx.ai REST API integration (no SDK — uses requests only)
import os
import json
import requests
from config import Config

# Initialize Mock Settings
use_mock = os.environ.get('USE_MOCK_MODE', 'False').lower() in ('true', '1', 'yes')

# Validate watsonx credentials
_api_key    = Config.WATSONX_API_KEY
_project_id = Config.WATSONX_PROJECT_ID
_url        = Config.WATSONX_URL.rstrip('/')
_model_id   = Config.WATSONX_MODEL

if use_mock:
    print("INFO: Mock Mode is explicitly enabled via USE_MOCK_MODE environment variable.")
else:
    if not _api_key or _api_key in ("your_ibm_cloud_api_key_here", ""):
        print("WARNING: WATSONX_API_KEY is not configured. Running in MOCK Mode.")
        use_mock = True
    elif not _project_id or _project_id in ("your_watsonx_project_id_here", ""):
        print("WARNING: WATSONX_PROJECT_ID is not configured. Running in MOCK Mode.")
        use_mock = True

# Cache the IAM token so we don't re-fetch on every request
_iam_token_cache = {"token": None, "expires_at": 0}

def _get_iam_token():
    """Fetch a short-lived IAM bearer token from IBM Cloud using the API key."""
    import time
    now = time.time()
    if _iam_token_cache["token"] and now < _iam_token_cache["expires_at"] - 60:
        return _iam_token_cache["token"]
    try:
        resp = requests.post(
            "https://iam.cloud.ibm.com/identity/token",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=f"grant_type=urn:ibm:params:oauth:grant-type:apikey&apikey={_api_key}",
            timeout=15
        )
        resp.raise_for_status()
        data = resp.json()
        _iam_token_cache["token"] = data["access_token"]
        _iam_token_cache["expires_at"] = now + int(data.get("expires_in", 3600))
        return _iam_token_cache["token"]
    except Exception as e:
        print(f"ERROR: Failed to fetch IAM token: {e}")
        return None


def _watsonx_generate(prompt, max_new_tokens=1024, temperature=0.7):
    """
    Call watsonx.ai text generation REST endpoint directly.
    Returns the generated text string or None on failure.
    """
    token = _get_iam_token()
    if not token:
        return None

    endpoint = f"{_url}/ml/v1/text/generation?version=2023-05-29"
    payload = {
        "model_id": _model_id,
        "project_id": _project_id,
        "input": prompt,
        "parameters": {
            "max_new_tokens": max_new_tokens,
            "temperature": temperature,
            "repetition_penalty": 1.1
        }
    }
    try:
        resp = requests.post(
            endpoint,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            json=payload,
            timeout=60
        )
        resp.raise_for_status()
        result = resp.json()
        return result["results"][0]["generated_text"].strip()
    except Exception as e:
        print(f"ERROR: watsonx generate call failed: {e}")
        return None


def _build_chat_prompt(system_instruction, history, user_message):
    """Build a plain-text prompt in Granite/Llama chat format."""
    lines = [f"<|system|>\n{system_instruction.strip()}\n"]
    for chat in history:
        role = "user" if chat['role'] == 'user' else "assistant"
        lines.append(f"<|{role}|>\n{chat['message'].strip()}\n")
    lines.append(f"<|user|>\n{user_message.strip()}\n<|assistant|>")
    return "\n".join(lines)


def _strip_code_fences(text):
    """Remove markdown ```json ... ``` wrappers that some models add."""
    text = text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        # parts[1] is the content inside the fences
        text = parts[1]
        if text.startswith("json"):
            text = text[4:]
    return text.strip()


# --- CHAT SERVICE ---

def generate_nutrition_chat_response(prompt, history, profile_data=None):
    """Sends chat history and new prompt to watsonx.ai, including profile details."""
    if use_mock:
        return get_mock_chat_response(prompt, profile_data)

    context_prefix = ""
    if profile_data:
        context_prefix = (
            f"[User Profile Context: Name: {profile_data['name']}, Age: {profile_data['age']}, "
            f"Gender: {profile_data['gender']}, Height: {profile_data['height_cm']}cm, "
            f"Weight: {profile_data['weight_kg']}kg, Activity: {profile_data['activity_level']}, "
            f"Diet: {profile_data['diet_type']}, Allergies: {profile_data['allergies'] or 'None'}]\n"
        )

    full_prompt = _build_chat_prompt(
        system_instruction=Config.AGENT_INSTRUCTIONS,
        history=history,
        user_message=context_prefix + prompt
    )

    result = _watsonx_generate(full_prompt, max_new_tokens=1024, temperature=0.7)
    if result is None:
        return get_mock_chat_response(prompt, profile_data)
    return result


# --- MEAL PLANNER SERVICE ---

def generate_meal_plan(profile_data, goal, duration):
    """Generates structured meal plan in JSON format using watsonx.ai."""
    if use_mock:
        return get_mock_meal_plan(profile_data, goal, duration)

    schema_prompt = (
        f"Generate a customized {duration} meal plan for the following profile:\n"
        f"- Name: {profile_data['name']}\n"
        f"- Age: {profile_data['age']} years old\n"
        f"- Gender: {profile_data['gender']}\n"
        f"- Height: {profile_data['height_cm']} cm\n"
        f"- Weight: {profile_data['weight_kg']} kg\n"
        f"- Activity Level: {profile_data['activity_level']}\n"
        f"- Dietary Type: {profile_data['diet_type']}\n"
        f"- Allergies: {profile_data['allergies'] or 'None'}\n"
        f"- Goal: {goal}\n\n"
        f"IMPORTANT: The food recommendations must heavily align with Indian regional foods, "
        f"using local ingredients (e.g. millets, dals, local spices, paneer/tofu, regional staples).\n\n"
        f"Return ONLY a valid JSON object — no extra text before or after — that strictly follows this schema:\n"
        f"{{\n"
        f"  \"title\": \"String\",\n"
        f"  \"target_calories\": Integer,\n"
        f"  \"target_protein\": Integer,\n"
        f"  \"target_carbs\": Integer,\n"
        f"  \"target_fat\": Integer,\n"
        f"  \"days\": [\n"
        f"    {{\n"
        f"      \"day\": \"String\",\n"
        f"      \"meals\": {{\n"
        f"        \"breakfast\": {{\"name\": \"String\", \"calories\": Integer, \"protein\": Integer, \"carbs\": Integer, \"fat\": Integer, \"description\": \"String\"}},\n"
        f"        \"lunch\":     {{\"name\": \"String\", \"calories\": Integer, \"protein\": Integer, \"carbs\": Integer, \"fat\": Integer, \"description\": \"String\"}},\n"
        f"        \"snack\":     {{\"name\": \"String\", \"calories\": Integer, \"protein\": Integer, \"carbs\": Integer, \"fat\": Integer, \"description\": \"String\"}},\n"
        f"        \"dinner\":    {{\"name\": \"String\", \"calories\": Integer, \"protein\": Integer, \"carbs\": Integer, \"fat\": Integer, \"description\": \"String\"}}\n"
        f"      }}\n"
        f"    }}\n"
        f"  ]\n"
        f"}}"
    )

    raw = _watsonx_generate(schema_prompt, max_new_tokens=2048, temperature=0.3)
    if raw is None:
        return get_mock_meal_plan(profile_data, goal, duration)
    try:
        return json.loads(_strip_code_fences(raw))
    except Exception as e:
        print(f"watsonx Meal Plan JSON parse error: {e}")
        return get_mock_meal_plan(profile_data, goal, duration)


# --- NUTRITION ANALYSIS SERVICE ---

def analyze_food_input(food_description, diet_type="Vegetarian"):
    """Analyzes a food description and extracts calories and macronutrients."""
    if use_mock:
        return get_mock_food_analysis(food_description)

    prompt = (
        f"Analyze the following food consumption description: \"{food_description}\"\n"
        f"Estimate the total Calories, Protein (g), Carbs (g), and Fat (g) content.\n"
        f"Additionally, provide a short, helpful, and friendly healthy tip/suggestion "
        f"considering a standard {diet_type} diet.\n\n"
        f"Return ONLY a valid JSON object — no extra text before or after — with these fields:\n"
        f"{{\n"
        f"  \"calories\": Integer,\n"
        f"  \"protein\": Float,\n"
        f"  \"carbs\": Float,\n"
        f"  \"fat\": Float,\n"
        f"  \"suggestions\": \"String\"\n"
        f"}}"
    )

    raw = _watsonx_generate(prompt, max_new_tokens=512, temperature=0.3)
    if raw is None:
        return get_mock_food_analysis(food_description)
    try:
        return json.loads(_strip_code_fences(raw))
    except Exception as e:
        print(f"watsonx Food Analysis JSON parse error: {e}")
        return get_mock_food_analysis(food_description)


# --- MOCK FALLBACK DATA ---

def get_mock_chat_response(prompt, profile_data):
    name = profile_data['name'] if profile_data else "User"
    return (
        f"👋 Hello {name}! (Running in MOCK Mode — No watsonx.ai credentials configured)\n\n"
        f"I received your message: \"{prompt}\"\n\n"
        f"To enable real AI conversations, add `WATSONX_API_KEY` and `WATSONX_PROJECT_ID` to your Railway environment variables.\n\n"
        f"**Here is a generic nutrition tip:**\n"
        f"Indian vegetarian diets can sometimes be carbohydrate-heavy. Try adding protein-rich options like paneer, "
        f"Greek yogurt (or hung curd), boiled chana, sprouts, or mixed dals to your regular meals to balance your macros. "
        f"Always prioritize fiber-rich foods like whole-wheat rotis, millets, and raw salads.\n\n"
        f"---\n"
        f"*Disclaimer: I am an AI Nutrition Agent. These suggestions are for general wellness and educational purposes. "
        f"Please consult your physician or a registered dietitian before making significant dietary changes.*"
    )


def get_mock_meal_plan(profile_data, goal, duration):
    name      = profile_data['name']
    diet_type = profile_data['diet_type']
    target_cals = 1800 if "loss" in goal.lower() else (2400 if "gain" in goal.lower() else 2000)

    breakfast = {"name": "Poha with Roasted Peanuts & Sprouts", "calories": 320, "protein": 12, "carbs": 50, "fat": 8,  "description": "High fiber carbohydrate source paired with plant-based protein."}
    lunch     = {"name": "Whole Wheat Roti (2) + Paneer Bhurji + Dal", "calories": 550, "protein": 28, "carbs": 65, "fat": 18, "description": "Balanced North Indian style lunch with high protein."}
    snack     = {"name": "Roasted Makhana (1 bowl) + Green Tea", "calories": 140, "protein": 3,  "carbs": 25, "fat": 3,  "description": "Light, crunchy, low-calorie local Indian snack."}
    dinner    = {"name": "Vegetable Khichdi + Curd", "calories": 390, "protein": 14, "carbs": 60, "fat": 10, "description": "Comforting, easily digestible rice-lentil blend."}

    if "non-veg" in diet_type.lower():
        breakfast = {"name": "Egg Bhurji (3 eggs) + Whole Wheat Toast (2)", "calories": 380, "protein": 24, "carbs": 35, "fat": 15, "description": "Classic high protein egg breakfast."}
        lunch     = {"name": "Brown Rice + Grilled Chicken Breast / Fish Curry + Dal", "calories": 600, "protein": 40, "carbs": 60, "fat": 12, "description": "Lean protein lunch with complex carbs."}

    plan = {
        "title": f"Mock {goal} Plan for {name} ({duration.capitalize()})",
        "target_calories": target_cals,
        "target_protein": 75 if "loss" in goal.lower() else 95,
        "target_carbs": 200,
        "target_fat": 50,
        "days": [{"day": "Day 1 (Mock Data)", "meals": {"breakfast": breakfast, "lunch": lunch, "snack": snack, "dinner": dinner}}]
    }

    if duration == "weekly":
        for i in range(2, 8):
            plan["days"].append({
                "day": f"Day {i} (Mock Data)",
                "meals": {"breakfast": breakfast, "lunch": lunch, "snack": snack, "dinner": dinner}
            })
    return plan


def get_mock_food_analysis(food_description):
    desc     = food_description.lower()
    calories = 350
    protein  = 10.0
    carbs    = 50.0
    fat      = 8.0

    if "roti" in desc or "chapati" in desc:
        calories, protein, carbs, fat = 250, 8.0, 45.0, 4.0
    if "paneer" in desc or "chicken" in desc or "egg" in desc:
        calories, protein, carbs, fat = 450, 28.0, 20.0, 15.0

    return {
        "calories": calories,
        "protein":  protein,
        "carbs":    carbs,
        "fat":      fat,
        "suggestions": (
            f"Estimated values for: '{food_description}'. "
            f"(Running in MOCK Mode — configure WATSONX_API_KEY in Railway variables for real AI analysis). "
            f"Tip: Combine carbs with a quality protein source for steady energy levels."
        )
    }
