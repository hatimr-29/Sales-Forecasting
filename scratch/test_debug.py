import urllib.request, urllib.parse, http.cookiejar

cookie_jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))

# 1. Login POST
login_data = urllib.parse.urlencode({'username': 'admin', 'password': 'admin123'}).encode()
res_login = opener.open('http://127.0.0.1:5000/login', data=login_data)
print('1. Login POST response URL:', res_login.geturl())

# 2. Predict POST (Sales Prediction)
post_data = urllib.parse.urlencode({
    'quantity': '10',
    'unit_price': '2500',
    'year': '2024',
    'month': '5',
    'quarter': '2',
    'day_of_week': 'Wednesday',
    'is_weekend': '0',
    'avg_price': '2500'
}).encode()
res_post = opener.open('http://127.0.0.1:5000/predict', data=post_data)
html_out = res_post.read().decode('utf-8')
print('Prediction result page HTML excerpt:')
for line in html_out.splitlines():
    if any(k in line for k in ['Predicted', 'Total Sales', '₹', '24,', '25,', 'prediction-value', 'prediction']):
        print('  ', line.strip().encode('ascii', 'replace').decode())
