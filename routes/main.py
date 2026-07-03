from flask import Blueprint, render_template, redirect, url_for, request, flash
import database as db

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    profiles = db.get_profiles()
    if not profiles:
        flash("Welcome! Please create a family profile first to start using the Nutrition Agent.", "info")
        return redirect(url_for('main.profiles_page'))
    
    # Get active profile from query param or default to the most recent one
    active_profile_id = request.args.get('profile_id', type=int)
    active_profile = None
    
    if active_profile_id:
        active_profile = db.get_profile(active_profile_id)
        
    if not active_profile:
        active_profile = profiles[0]
        
    # Get last 7 days of logs for the active profile
    logs = db.get_nutrition_logs(active_profile['id'], limit=7)
    
    # Get latest meal plans for active profile
    meal_plans = db.get_meal_plans(active_profile['id'])
    latest_meal_plan = meal_plans[0] if meal_plans else None
    
    return render_template(
        'dashboard.html',
        profiles=profiles,
        active_profile=active_profile,
        logs=logs,
        latest_meal_plan=latest_meal_plan
    )

@main_bp.route('/chat')
def chat_page():
    profiles = db.get_profiles()
    if not profiles:
        flash("Please create a family profile first to start chatting.", "warning")
        return redirect(url_for('main.profiles_page'))
        
    active_profile_id = request.args.get('profile_id', type=int)
    active_profile = None
    if active_profile_id:
        active_profile = db.get_profile(active_profile_id)
    if not active_profile:
        active_profile = profiles[0]
        
    history = db.get_chat_history(active_profile['id'])
    
    return render_template(
        'chat.html',
        profiles=profiles,
        active_profile=active_profile,
        chat_history=history
    )

@main_bp.route('/meal-planner')
def meal_planner_page():
    profiles = db.get_profiles()
    if not profiles:
        flash("Please create a family profile first to use the Meal Planner.", "warning")
        return redirect(url_for('main.profiles_page'))
        
    active_profile_id = request.args.get('profile_id', type=int)
    active_profile = None
    if active_profile_id:
        active_profile = db.get_profile(active_profile_id)
    if not active_profile:
        active_profile = profiles[0]
        
    # Get meal plans generated for this profile
    plans = db.get_meal_plans(active_profile['id'])
    
    return render_template(
        'meal_planner.html',
        profiles=profiles,
        active_profile=active_profile,
        meal_plans=plans
    )

@main_bp.route('/bmi')
def bmi_page():
    # Standalone page - load profiles if any to auto-fill height/weight
    profiles = db.get_profiles()
    return render_template('bmi.html', profiles=profiles)

@main_bp.route('/profiles')
def profiles_page():
    profiles = db.get_profiles()
    return render_template('profiles.html', profiles=profiles)
