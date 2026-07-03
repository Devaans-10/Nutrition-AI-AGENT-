from flask import Blueprint, jsonify, request
import json
import database as db
import services.gemini_service as gemini
from datetime import datetime

api_bp = Blueprint('api', __name__)

# Helper to calculate scientific TDEE and macro distribution
def calculate_nutritional_targets(weight, height, age, gender, activity_level):
    # BMR (Mifflin-St Jeor Equation)
    if gender.lower() == 'male':
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    else:
        bmr = 10 * weight + 6.25 * height - 5 * age - 161
        
    # Activity multipliers
    multipliers = {
        'Sedentary': 1.2,
        'Lightly Active': 1.375,
        'Moderately Active': 1.55,
        'Very Active': 1.725,
        'Extra Active': 1.9
    }
    
    multiplier = multipliers.get(activity_level, 1.2)
    tdee = bmr * multiplier
    
    # Standard healthy macro split: 50% carbs, 20% protein, 30% fat
    calories = round(tdee)
    carbs_g = round((calories * 0.50) / 4)
    protein_g = round((calories * 0.20) / 4)
    fat_g = round((calories * 0.30) / 9)
    
    return calories, protein_g, carbs_g, fat_g

# --- PROFILE API ---

@api_bp.route('/profiles', methods=['POST'])
def add_profile():
    try:
        data = request.json or request.form
        name = data.get('name')
        age = int(data.get('age'))
        gender = data.get('gender')
        height_cm = float(data.get('height_cm'))
        weight_kg = float(data.get('weight_kg'))
        activity_level = data.get('activity_level', 'Sedentary')
        diet_type = data.get('diet_type', 'Vegetarian')
        allergies = data.get('allergies', '')
        
        if not name or not age or not gender or not height_cm or not weight_kg:
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
            
        calories, protein, carbs, fat = calculate_nutritional_targets(
            weight_kg, height_cm, age, gender, activity_level
        )
        
        profile_id = db.create_profile(
            name, age, gender, height_cm, weight_kg, activity_level, diet_type, allergies,
            target_calories=calories, target_protein=protein, target_carbs=carbs, target_fat=fat
        )
        
        return jsonify({
            'success': True,
            'message': 'Profile created successfully!',
            'profile_id': profile_id
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/profiles/update/<int:profile_id>', methods=['POST'])
def update_profile(profile_id):
    try:
        data = request.json or request.form
        name = data.get('name')
        age = int(data.get('age'))
        gender = data.get('gender')
        height_cm = float(data.get('height_cm'))
        weight_kg = float(data.get('weight_kg'))
        activity_level = data.get('activity_level', 'Sedentary')
        diet_type = data.get('diet_type', 'Vegetarian')
        allergies = data.get('allergies', '')
        
        if not name or not age or not gender or not height_cm or not weight_kg:
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
            
        # Re-calculate macros based on updated metrics
        calories, protein, carbs, fat = calculate_nutritional_targets(
            weight_kg, height_cm, age, gender, activity_level
        )
        
        db.update_profile(
            profile_id, name, age, gender, height_cm, weight_kg, activity_level, diet_type, allergies,
            target_calories=calories, target_protein=protein, target_carbs=carbs, target_fat=fat
        )
        
        return jsonify({'success': True, 'message': 'Profile updated successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/profiles/delete/<int:profile_id>', methods=['POST'])
def delete_profile(profile_id):
    try:
        db.delete_profile(profile_id)
        return jsonify({'success': True, 'message': 'Profile deleted successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# --- BMI API ---

@api_bp.route('/bmi/calculate', methods=['POST'])
def calculate_bmi():
    try:
        data = request.json or request.form
        weight = float(data.get('weight'))
        height_cm = float(data.get('height'))
        
        if not weight or not height_cm:
            return jsonify({'success': False, 'message': 'Please provide height and weight'}), 400
            
        height_m = height_cm / 100
        bmi = weight / (height_m * height_m)
        bmi = round(bmi, 1)
        
        # Categorize
        if bmi < 18.5:
            category = "Underweight"
            alert_class = "warning"
            tip = "Consider speaking to a nutritionist to help you gain weight healthily. Ensure you are eating calorie-dense foods."
        elif 18.5 <= bmi < 24.9:
            category = "Normal weight"
            alert_class = "success"
            tip = "Great job! Keep maintaining your balanced diet and regular physical activity."
        elif 25 <= bmi < 29.9:
            category = "Overweight"
            alert_class = "warning"
            tip = "Focus on portion control, adding more protein and vegetables, and increasing physical exercise."
        else:
            category = "Obesity"
            alert_class = "danger"
            tip = "We advise consulting a healthcare professional or clinical dietitian for a personalized therapeutic plan."
            
        return jsonify({
            'success': True,
            'bmi': bmi,
            'category': category,
            'alert_class': alert_class,
            'tip': tip
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# --- CHAT API ---

@api_bp.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json or request.form
        profile_id = int(data.get('profile_id'))
        message = data.get('message')
        
        if not profile_id or not message:
            return jsonify({'success': False, 'message': 'Missing profile_id or message'}), 400
            
        # Get active profile and chat history
        profile_data = db.get_profile(profile_id)
        if not profile_data:
            return jsonify({'success': False, 'message': 'Profile not found'}), 404
            
        history = db.get_chat_history(profile_id)
        
        # Call Gemini service
        ai_response = gemini.generate_nutrition_chat_response(message, history, profile_data)
        
        # Save messages to database
        db.add_chat_message(profile_id, 'user', message)
        db.add_chat_message(profile_id, 'model', ai_response)
        
        return jsonify({
            'success': True,
            'response': ai_response
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/chat/clear', methods=['POST'])
def clear_chat():
    try:
        data = request.json or request.form
        profile_id = int(data.get('profile_id'))
        db.clear_chat_history(profile_id)
        return jsonify({'success': True, 'message': 'Chat history cleared successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# --- MEAL PLANNER API ---

@api_bp.route('/meal-plan/generate', methods=['POST'])
def generate_meal_plan():
    try:
        data = request.json or request.form
        profile_id = int(data.get('profile_id'))
        goal = data.get('goal', 'Maintenance')
        duration = data.get('duration', 'daily') # 'daily' or 'weekly'
        
        profile_data = db.get_profile(profile_id)
        if not profile_data:
            return jsonify({'success': False, 'message': 'Profile not found'}), 404
            
        # Generate meal plan via Gemini
        plan = gemini.generate_meal_plan(profile_data, goal, duration)
        
        # Save meal plan to database as a stringified JSON
        db.add_meal_plan(profile_id, goal, duration, json_data:=json.dumps(plan))
        
        return jsonify({
            'success': True,
            'plan': plan
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# --- FOOD LOGGING AND STATS API ---

@api_bp.route('/nutrition/log', methods=['POST'])
def log_nutrition():
    try:
        data = request.json or request.form
        profile_id = int(data.get('profile_id'))
        food_description = data.get('food_description')
        date_str = data.get('date', datetime.today().strftime('%Y-%m-%d'))
        
        if not profile_id or not food_description:
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
            
        profile_data = db.get_profile(profile_id)
        if not profile_data:
            return jsonify({'success': False, 'message': 'Profile not found'}), 404
            
        # Call Gemini to analyze food input
        analysis = gemini.analyze_food_input(food_description, profile_data['diet_type'])
        
        # Retrieve existing log for today to add to it rather than overwrite
        conn = db.get_db_connection()
        existing_log = conn.execute(
            "SELECT * FROM nutrition_logs WHERE profile_id = ? AND date = ?", 
            (profile_id, date_str)
        ).fetchone()
        conn.close()
        
        if existing_log:
            new_calories = existing_log['calories'] + analysis['calories']
            new_protein = round(existing_log['protein'] + analysis['protein'], 1)
            new_carbs = round(existing_log['carbs'] + analysis['carbs'], 1)
            new_fat = round(existing_log['fat'] + analysis['fat'], 1)
        else:
            new_calories = analysis['calories']
            new_protein = analysis['protein']
            new_carbs = analysis['carbs']
            new_fat = analysis['fat']
            
        success = db.add_nutrition_log(
            profile_id, new_calories, new_protein, new_carbs, new_fat, date_str
        )
        
        if not success:
            return jsonify({'success': False, 'message': 'Database error logging nutrition'}), 500
            
        return jsonify({
            'success': True,
            'analysis': analysis,
            'daily_total': {
                'calories': new_calories,
                'protein': new_protein,
                'carbs': new_carbs,
                'fat': new_fat
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/nutrition-stats/<int:profile_id>')
def get_nutrition_stats(profile_id):
    try:
        logs = db.get_nutrition_logs(profile_id, limit=7)
        profile = db.get_profile(profile_id)
        
        if not profile:
            return jsonify({'success': False, 'message': 'Profile not found'}), 404
            
        # Format logs for Chart.js
        labels = [log['date'] for log in logs]
        calories = [log['calories'] for log in logs]
        protein = [log['protein'] for log in logs]
        carbs = [log['carbs'] for log in logs]
        fat = [log['fat'] for log in logs]
        
        return jsonify({
            'success': True,
            'labels': labels,
            'calories': calories,
            'protein': protein,
            'carbs': carbs,
            'fat': fat,
            'targets': {
                'calories': profile['target_calories'],
                'protein': profile['target_protein'],
                'carbs': profile['target_carbs'],
                'fat': profile['target_fat']
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
