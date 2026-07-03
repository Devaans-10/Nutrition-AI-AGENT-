import os
import unittest
import json
from app import create_app
import database as db
import services.gemini_service as gemini

class NutritionAgentTestCase(unittest.TestCase):
    def setUp(self):
        # Override database to a separate test database
        self.db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_nutrition_agent.db')
        from config import Config
        Config.DATABASE = self.db_path
        
        # Re-initialize the test database schema
        db.init_db()
        
        # Force mock mode for Gemini services during testing
        gemini.use_mock = True
        
        self.app = create_app()
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()
        # Remove testing database
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except OSError:
                pass

    def test_empty_profiles_redirects(self):
        """Verify redirect to /profiles if no family profile exists."""
        response = self.client.get('/', follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertTrue('/profiles' in response.location)

    def test_profile_page_loads(self):
        """Verify profiles manager page loads successfully."""
        response = self.client.get('/profiles')
        self.assertEqual(response.status_code, 200)

    def test_bmi_calculator_math(self):
        """Verify BMI calculation logic and output classifications."""
        payload = {'weight': 70, 'height': 175}
        response = self.client.post('/api/bmi/calculate', 
                                    data=json.dumps(payload), 
                                    content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['bmi'], 22.9)
        self.assertEqual(data['category'], 'Normal weight')

    def test_profile_crud_lifecycle(self):
        """Verify profile creation, targets calculation, updates, and deletion."""
        # 1. Create Profile
        payload = {
            'name': 'Test User',
            'age': 30,
            'gender': 'Male',
            'height_cm': 180,
            'weight_kg': 80,
            'activity_level': 'Sedentary',
            'diet_type': 'Vegetarian',
            'allergies': 'Peanuts'
        }
        response = self.client.post('/api/profiles',
                                    data=json.dumps(payload),
                                    content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        profile_id = data['profile_id']

        # Verify profile is in db and macro calculations occurred (Mifflin BMR = 10*80 + 6.25*180 - 5*30 + 5 = 800+1125-150+5 = 1780. TDEE = 1780*1.2 = 2136)
        profile = db.get_profile(profile_id)
        self.assertIsNotNone(profile)
        self.assertEqual(profile['name'], 'Test User')
        self.assertEqual(profile['target_calories'], 2136)
        self.assertEqual(profile['target_protein'], 107) # (2136 * 0.20) / 4 = 106.8 -> 107
        
        # 2. Update Profile
        payload['weight_kg'] = 75
        response = self.client.post(f'/api/profiles/update/{profile_id}',
                                    data=json.dumps(payload),
                                    content_type='application/json')
        self.assertEqual(response.status_code, 200)
        profile = db.get_profile(profile_id)
        self.assertEqual(profile['weight_kg'], 75)
        self.assertLess(profile['target_calories'], 2136) # Calorie budget should fall as weight decreases

        # 3. Delete Profile
        response = self.client.post(f'/api/profiles/delete/{profile_id}')
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(db.get_profile(profile_id))

    def test_mock_gemini_services(self):
        """Verify mock fallbacks for Gemini services operate properly."""
        profile_data = {
            'name': 'Aarav',
            'age': 25,
            'gender': 'Male',
            'height_cm': 170,
            'weight_kg': 65,
            'activity_level': 'Sedentary',
            'diet_type': 'Vegetarian',
            'allergies': ''
        }
        
        # Chat
        chat_resp = gemini.generate_nutrition_chat_response("What is healthy breakfast?", [], profile_data)
        self.assertIn("Aarav", chat_resp)
        self.assertIn("MOCK Mode", chat_resp)
        
        # Meal Planner
        plan = gemini.generate_meal_plan(profile_data, "Weight Loss", "daily")
        self.assertEqual(plan['target_calories'], 1800)
        self.assertTrue(len(plan['days']) == 1)
        self.assertEqual(plan['days'][0]['meals']['breakfast']['name'], "Poha with Roasted Peanuts & Sprouts")

        # Food analyzer
        analysis = gemini.analyze_food_input("I ate 2 rotis")
        self.assertEqual(analysis['calories'], 250)
        self.assertEqual(analysis['protein'], 8.0)

if __name__ == '__main__':
    unittest.main()
