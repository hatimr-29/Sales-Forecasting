import traceback, sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import app

with app.app.test_request_context('/login', method='POST', data={'username': 'admin', 'password': 'admin123'}):
    try:
        res = app.login_post()
        print("login_post returned:", res)
    except Exception as e:
        traceback.print_exc()
