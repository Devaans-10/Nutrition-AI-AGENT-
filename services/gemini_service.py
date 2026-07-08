# Service module for IBM watsonx.ai API integration
import os
import json
from config import Config

# Initialize Mock Settings
use_mock = os.environ.get('USE_MOCK_MODE', 'False').lower() in ('true', '1', 'yes')

# Validate watsonx credentials
_api_key = Config.WATSONX_API_KEY
_project_id = Config.WATSONX_PROJECT_ID
_url = Config.WATSONX_URL

if use_mock:
    print("INFO: Mock Mode is explicitly enabled via USE_MOCK_MODE environment variable.")
else:
    if not _api_key or _api_key in ("your_ibm_cloud_api_key_here", ""):
        print("WARNING: WATSONX_API_KEY is not configured. Running in MOCK Mode.")
        use_mock = True
    elif not _project_id or _project_id in ("your_watsonx_project_id_here", ""):
        print("WARNING: WATSONX_PROJECT_ID is not configured. Running in MOCK Mode.")
        use_mock = True

def get_watsonx_model():
    """Initialize and return IBM watsonx.ai ModelInference client."""
    if use_mock:
        return None
    try:
        from ibm_watsonx_ai import Credentials
        from ibm_watsonx_ai.foundation_models import ModelInference
        from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams

        credentials = Credentials(
            api_key=_api_key,
            url=_url
        )

        params = {
            GenParams.MAX_NEW_TOKENS: 2048,
            GenParams.TEMPERATURE: 0.7,
            GenParams.REPETITION_PENALTY: 1.1,
        }

        model = ModelInference(
            model_id=Config.WATSONX_MODEL,
            credentials=credentials,
            project_id=_project_id,
            params=params
        )
        return model
    except Exception as e:
        print(f"ERROR: Failed to initialize watsonx ModelInference: {e}")
        return None


def _build_chat_prompt(system_instruction, history, user_message):
    """Build a plain-text prompt in chat format for Granite/Llama models."""
    lines = [f"<|system|>\n{system_instruction.strip()}\n"]
    for chat in history:
        role = "user" if chat['role'] == 'user' else "assistant"
        lines.append(f"<|{role}|>\n{chat['message'].strip()}\n")
    lines.append(f"<|user|>\n{user_message.strip()}\n<|assistant|>")
    return "\n".join(lines)


# --- CHAT SERVICE ---

def generate_nutrition_chat_response(prompt, history, profile_data=None):
    """
    Sends chat history and new prompt to watsonx.ai, including profile details.
    """
    if use_mock:
        return get_mock_chat_response(prompt, profile_data)

    model = get_watsonx_model()
    if not model:
        return get_mock_chat_response(prompt, profile_data)

    # Prepend profile context to the user message if available
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

    try:
        response = model.generate_text(prompt=full_prompt)
        return response
    except Exception as e:
        print(f"watsonx Chat Error: {e}")
        err_str = str(e)
        if "429" in err_str or "quota" in err_str.lower() or "limit" in err_str.lower():
            return (
                "⚠️ **Rate Limit Exceeded**:\n\n"
                "Your watsonx.ai API has hit its rate limit. Please wait a moment before retrying.\n\n"
                "*💡 Tip: Set `USE_MOCK_MODE=True` in your `.env` to test the UI offline.*"
            )
        return (
            f"Sorry, I encountered an issue reaching the IBM watsonx.ai service.\n\n"
            f"**Details**: {err_str}\n\n"
            f"Please verify your `WATSONX_API_KEY` and `WATSONX_PROJECT_ID` in the `.env` file."
        )


# --- MEAL PLANNER SERVICE ---

def generate_meal_plan(profile_data, goal, duration):
    """
    Generates structured meal plan in JSON format using watsonx.ai.
    """
    if use_mock:
        return get_mock_meal_plan(profile_data, goal, duration)

    model = get_watsonx_model()
    if not model:
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
        f"using local ingredients (e.g. millets, dals, local spices, paneer/tofu, regional staples). "
        f"Provide suitable alternatives if regional differences exist (North vs South Indian styles).\n\n"
        f"Return ONLY a valid JSON object — no extra text before or after — that strictly follows this schema:\n"
        f"{{\n"
        f"  \"title\": \"String (A descriptive title for the plan)\",\n"
        f"  \"target_calories\": Integer,\n"
        f"  \"target_protein\": Integer,\n"
        f"  \"target_carbs\": Integer,\n"
        f"  \"target_fat\": Integer,\n"
        f"  \"days\": [\n"
        f"    {{\n"
        f"      \"day\": \"String (e.g., 'Day 1' or 'Monday')\",\n"
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

    try:
        raw = model.generate_text(prompt=schema_prompt)
        # Strip markdown code fences if model wraps response
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except Exception as e:
        print(f"watsonx Meal Plan Error: {e}")
        return get_mock_meal_plan(profile_data, goal, duration)


# --- NUTRITION ANALYSIS SERVICE ---

def analyze_food_input(food_description, diet_type="Vegetarian"):
    """
    Analyzes a description of food consumed and extracts calories and macronutrients.
    """
    if use_mock:
        return get_mock_food_analysis(food_description)

    model = get_watsonx_model()
    if not model:
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
        f"  \"suggestions\": \"String (Short actionable healthy eating tip)\"\n"
        f"}}"
    )

    try:
        raw = model.generate_text(prompt=prompt)
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except Exception as e:
        print(f"watsonx Food Analysis Error: {e}")
        return get_mock_food_analysis(food_description)


# --- MOCK FALLBACK DATA ---

def get_mock_chat_response(prompt, profile_data):
    name = profile_data['name'] if profile_data else "User"
    return (
        f"👋 Hello {name}! (Running in MOCK Mode - No watsonx.ai credentials configured in `.env`)\n\n"
        f"I received your message: \"{prompt}\"\n\n"
        f"To enable real AI conversations, please edit the `.env` file and add your `WATSONX_API_KEY` and `WATSONX_PROJECT_ID`.\n\n"
        f"**Here is a generic nutrition tip:**\n"
        f"Indian vegetarian diets can sometimes be carbohydrate-heavy. Try adding protein-rich options like paneer, Greek yogurt (or hung curd), boiled chana, sprouts, or mixed dals to your regular meals to balance your macros. Always prioritize fiber-rich foods like whole-wheat rotis, millets, and raw salads.\n\n"
        f"--- \n"
        f"*Disclaimer: I am an AI Nutrition Agent. These suggestions are for general wellness and educational purposes. Please consult your physician or a registered dietitian before making significant dietary changes, especially if you have pre-existing medical conditions.*"
    )

def get_mock_meal_plan(profile_data, goal, duration):
    name = profile_data['name']
    diet_type = profile_data['diet_type']
    target_cals = 1800 if "loss" in goal.lower() else (2400 if "gain" in goal.lower() else 2000)

    breakfast = {"name": "Poha with Roasted Peanuts & Sprouts", "calories": 320, "protein": 12, "carbs": 50, "fat": 8, "description": "High fiber carbohydrate source paired with plant-based protein."}
    lunch = {"name": "Whole Wheat Roti (2) + Paneer Bhurji + Dal", "calories": 550, "protein": 28, "carbs": 65, "fat": 18, "description": "Balanced North Indian style lunch with high protein."}
    snack = {"name": "Roasted Makhana (1 bowl) + Green Tea", "calories": 140, "protein": 3, "carbs": 25, "fat": 3, "description": "Light, crunchy, low-calorie local Indian snack."}
    dinner = {"name": "Vegetable Khichdi + Curd", "calories": 390, "protein": 14, "carbs": 60, "fat": 10, "description": "Comforting, easily digestible rice-lentil blend."}

    if "non-veg" in diet_type.lower():
        breakfast = {"name": "Egg Bhurji (3 eggs) + Whole Wheat Toast (2)", "calories": 380, "protein": 24, "carbs": 35, "fat": 15, "description": "Classic high protein egg breakfast."}
        lunch = {"name": "Brown Rice + Grilled Chicken Breast / Fish Curry + Dal", "calories": 600, "protein": 40, "carbs": 60, "fat": 12, "description": "Lean protein lunch with complex carbs."}

    plan = {
        "title": f"Mock {goal} Plan for {name} ({duration.capitalize()})",
        "target_calories": target_cals,
        "target_protein": 75 if "loss" in goal.lower() else 95,
        "target_carbs": 200,
        "target_fat": 50,
        "days": [
            {
                "day": "Day 1 (Mock Data)",
                "meals": {
                    "breakfast": breakfast,
                    "lunch": lunch,
                    "snack": snack,
                    "dinner": dinner
                }
            }
        ]
    }

    if duration == "weekly":
        for i in range(2, 8):
            plan["days"].append({
                "day": f"Day {i} (Mock Data)",
                "meals": {
                    "breakfast": breakfast,
                    "lunch": lunch,
                    "snack": snack,
                    "dinner": dinner
                }
            })

    return plan

def get_mock_food_analysis(food_description):
    desc = food_description.lower()
    calories = 350
    protein = 10.0
    carbs = 50.0
    fat = 8.0

    if "roti" in desc or "chapati" in desc:
        calories = 250
        protein = 8.0
        carbs = 45.0
        fat = 4.0
    if "paneer" in desc or "chicken" in desc or "egg" in desc:
        calories = 450
        protein = 28.0
        carbs = 20.0
        fat = 15.0

    return {
        "calories": calories,
        "protein": protein,
        "carbs": carbs,
        "fat": fat,
        "suggestions": f"Estimated values for: '{food_description}'. (Running in MOCK Mode - Configure WATSONX_API_KEY in `.env` for accurate AI analysis). Tip: Combine carbs with a quality protein source for steady energy levels."
    }
