import traceback
try:
    with open('app.py', 'r', encoding='utf-8') as f:
        code = f.read()
    exec(code, {'__name__': 'not_main'})
    print("app.py executed successfully!")
except Exception as e:
    traceback.print_exc()
