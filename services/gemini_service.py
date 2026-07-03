# Service module for Google AI Gemini API integration
import os
import json
import google.generativeai as genai
from config import Config

# Initialize API Key and Mock Settings
api_key = Config.GOOGLE_API_KEY
use_mock = os.environ.get('USE_MOCK_MODE', 'False').lower() in ('true', '1', 'yes')

if use_mock:
    print("INFO: Mock Mode is explicitly enabled via USE_MOCK_MODE environment variable.")
else:
    if not api_key or api_key in ("your_gemini_api_key_here", ""):
        print("WARNING: GOOGLE_API_KEY is not configured. Running in MOCK Mode.")
        use_mock = True
    else:
        try:
            genai.configure(api_key=api_key)
        except Exception as e:
            print(f"ERROR: Failed to configure Gemini API: {e}. Running in MOCK Mode.")
            use_mock = True

def get_gemini_model():
    if use_mock:
        return None
    try:
        # Use dynamic model configured in Config.GEMINI_MODEL
        model = genai.GenerativeModel(
            model_name=Config.GEMINI_MODEL,
            system_instruction=Config.AGENT_INSTRUCTIONS
        )
        return model
    except Exception as e:
        print(f"ERROR: Failed to initialize GenerativeModel: {e}")
        return None

# --- CHAT SERVICE ---

def generate_nutrition_chat_response(prompt, history, profile_data=None):
    """
    Sends chat history and new prompt to Gemini, including profile details.
    """
    if use_mock or not get_gemini_model():
        return get_mock_chat_response(prompt, profile_data)

    model = get_gemini_model()
    
    # Format history for Gemini API
    # Gemini expectation: list of dicts with role and parts.
    # roles: 'user' and 'model'
    formatted_history = []
    for chat in history:
        role = 'user' if chat['role'] == 'user' else 'model'
        formatted_history.append({
            'role': role,
            'parts': [chat['message']]
        })
    
    # Prepend profile context to the conversation if available
    context_prefix = ""
    if profile_data:
        context_prefix = (
            f"[User Profile Context: Name: {profile_data['name']}, Age: {profile_data['age']}, "
            f"Gender: {profile_data['gender']}, Height: {profile_data['height_cm']}cm, "
            f"Weight: {profile_data['weight_kg']}kg, Activity: {profile_data['activity_level']}, "
            f"Diet: {profile_data['diet_type']}, Allergies: {profile_data['allergies'] or 'None'}]\n"
        )
    
    try:
        chat_session = model.start_chat(history=formatted_history)
        response = chat_session.send_message(context_prefix + prompt)
        return response.text
    except Exception as e:
        print(f"Gemini API Chat Error: {e}")
        err_str = str(e)
        if "429" in err_str or "resourceexhausted" in err_str.lower() or "quota" in err_str.lower() or "limit" in err_str.lower():
            return (
                "⚠️ **Rate Limit Exceeded (Quota Exhausted)**:\n\n"
                "Your Gemini API Key has hit its rate limit or daily quota. Please wait a minute before sending another message, or check your request limits in Google AI Studio.\n\n"
                "*💡 Tip: If you want to continue testing the application immediately without running into rate limits, you can temporarily change the API Key in your `.env` file back to `your_gemini_api_key_here` to enable the offline Mock Mode!*"
            )
        return (
            f"Sorry, I encountered an issue reaching the Gemini AI Service.\n\n"
            f"**Details**: {err_str}\n\n"
            f"Please verify your GOOGLE_API_KEY in the `.env` file."
        )

# --- MEAL PLANNER SERVICE ---

def generate_meal_plan(profile_data, goal, duration):
    """
    Generates structured meal plan in JSON format.
    """
    if use_mock or not get_gemini_model():
        return get_mock_meal_plan(profile_data, goal, duration)

    model = get_gemini_model()
    
    # Define JSON schema instruction
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
        f"Return ONLY a JSON object that strictly adheres to the following JSON schema:\n"
        f"{{\n"
        f"  \"title\": \"String (A descriptive title for the plan)\",\n"
        f"  \"target_calories\": Integer (Daily target calories),\n"
        f"  \"target_protein\": Integer (Daily target protein in grams),\n"
        f"  \"target_carbs\": Integer (Daily target carbs in grams),\n"
        f"  \"target_fat\": Integer (Daily target fat in grams),\n"
        f"  \"days\": [\n"
        f"    {{\n"
        f"      \"day\": \"String (e.g., 'Day 1' or 'Monday')\",\n"
        f"      \"meals\": {{\n"
        f"        \"breakfast\": {{\n"
        f"          \"name\": \"String (Name of dish)\",\n"
        f"          \"calories\": Integer,\n"
        f"          \"protein\": Integer,\n"
        f"          \"carbs\": Integer,\n"
        f"          \"fat\": Integer,\n"
        f"          \"description\": \"String (Ingredients, preparation summary, and regional tweaks)\"\n"
        f"        }},\n"
        f"        \"lunch\": {{\n"
        f"          \"name\": \"String\",\n"
        f"          \"calories\": Integer,\n"
        f"          \"protein\": Integer,\n"
        f"          \"carbs\": Integer,\n"
        f"          \"fat\": Integer,\n"
        f"          \"description\": \"String\"\n"
        f"        }},\n"
        f"        \"snack\": {{\n"
        f"          \"name\": \"String\",\n"
        f"          \"calories\": Integer,\n"
        f"          \"protein\": Integer,\n"
        f"          \"carbs\": Integer,\n"
        f"          \"fat\": Integer,\n"
        f"          \"description\": \"String\"\n"
        f"        }},\n"
        f"        \"dinner\": {{\n"
        f"          \"name\": \"String\",\n"
        f"          \"calories\": Integer,\n"
        f"          \"protein\": Integer,\n"
        f"          \"carbs\": Integer,\n"
        f"          \"fat\": Integer,\n"
        f"          \"description\": \"String\"\n"
        f"        }}\n"
        f"      }}\n"
        f"    }}\n"
        f"  ]\n"
        f"}}\n"
    )

    try:
        # Request JSON output
        response = model.generate_content(
            schema_prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"Gemini Meal Plan Error: {e}")
        # fallback to mock
        return get_mock_meal_plan(profile_data, goal, duration)

# --- NUTRITION ANALYSIS SERVICE ---

def analyze_food_input(food_description, diet_type="Vegetarian"):
    """
    Analyzes a description of food consumed and extracts calories and macronutrients.
    """
    if use_mock or not get_gemini_model():
        return get_mock_food_analysis(food_description)

    model = get_gemini_model()
    
    prompt = (
        f"Analyze the following food consumption description: \"{food_description}\"\n"
        f"Estimate the total Calories, Protein (g), Carbs (g), and Fat (g) content.\n"
        f"Additionally, provide a short, helpful, and friendly healthy tip/suggestion "
        f"considering a standard {diet_type} diet.\n\n"
        f"Return ONLY a JSON object with the following fields:\n"
        f"{{\n"
        f"  \"calories\": Integer,\n"
        f"  \"protein\": Float,\n"
        f"  \"carbs\": Float,\n"
        f"  \"fat\": Float,\n"
        f"  \"suggestions\": \"String (Short actionable healthy eating tip)\"\n"
        f"}}"
    )

    try:
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"Gemini Food Analysis Error: {e}")
        return get_mock_food_analysis(food_description)

# --- MOCK FALLBACK DATA ---

def get_mock_chat_response(prompt, profile_data):
    name = profile_data['name'] if profile_data else "User"
    return (
        f"👋 Hello {name}! (Running in MOCK Mode - No Gemini API Key configured in `.env`)\n\n"
        f"I received your message: \"{prompt}\"\n\n"
        f"To enable real Gemini AI conversations, please edit the `.env` file in the project root and add your `GOOGLE_API_KEY`.\n\n"
        f"**Here is a generic nutrition tip:**\n"
        f"Indian vegetarian diets can sometimes be carbohydrate-heavy. Try adding protein-rich options like paneer, Greek yogurt (or hung curd), boiled chana, sprouts, or mixed dals to your regular meals to balance your macros. Always prioritize fiber-rich foods like whole-wheat rotis, millets, and raw salads.\n\n"
        f"--- \n"
        f"*Disclaimer: I am an AI Nutrition Agent. These suggestions are for general wellness and educational purposes. Please consult your physician or a registered dietitian before making significant dietary changes, especially if you have pre-existing medical conditions.*"
    )

def get_mock_meal_plan(profile_data, goal, duration):
    name = profile_data['name']
    diet_type = profile_data['diet_type']
    target_cals = 1800 if "loss" in goal.lower() else (2400 if "gain" in goal.lower() else 2000)
    
    # Simple static mock meal plan based on vegetarian/non-vegetarian
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
    
    # If weekly, duplicate for showing structured data
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
    # simple text matching mock
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
        "suggestions": f"Estimated values for: '{food_description}'. (Running in MOCK Mode - Configure GOOGLE_API_KEY in `.env` for accurate AI analysis). Tip: Combine carbs with a quality protein source for steady energy levels."
    }
