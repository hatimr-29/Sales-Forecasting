import warnings
warnings.filterwarnings('ignore')

import mysql.connector
import sqlite3
import os
import joblib
import pandas as pd
import numpy as np
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "sales_forecasting_secret_key"

DB_TYPE = None

def init_sqlite_db(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("SELECT * FROM users WHERE username = ?", ('admin',))
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
            ('admin', 'admin@gmail.com', 'admin123')
        )
    conn.commit()

# Database Connection Helper
def get_db_connection():
    global DB_TYPE
    if DB_TYPE == 'mysql':
        try:
            conn = mysql.connector.connect( 
                host=os.environ.get("DB_HOST", "localhost"),
                user=os.environ.get("DB_USER", "root"),
                password=os.environ.get("DB_PASSWORD", "h@tim66"),
                database=os.environ.get("DB_NAME", "sales_dashboard"),
                use_pure=True,
                connect_timeout=2
            )
            return conn, 'mysql'
        except Exception:
            DB_TYPE = None

    if DB_TYPE is None:
        try:
            conn = mysql.connector.connect( 
                host=os.environ.get("DB_HOST", "localhost"),
                user=os.environ.get("DB_USER", "root"),
                password=os.environ.get("DB_PASSWORD", "h@tim66"),
                database=os.environ.get("DB_NAME", "sales_dashboard"),
                use_pure=True,
                connect_timeout=2
            )
            DB_TYPE = 'mysql'
            return conn, 'mysql'
        except Exception:
            DB_TYPE = 'sqlite'

    # SQLite Fallback
    db_dir = os.path.join(BASE_DIR, 'database')
    os.makedirs(db_dir, exist_ok=True)
    db_path = os.path.join(db_dir, 'sales_dashboard.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    init_sqlite_db(conn)
    return conn, 'sqlite'


# Matplotlib Static Chart Generator
def generate_matplotlib_charts(df_data):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import seaborn as sns
    
    if df_data is None:
        return
        
    try:
        sns.set_theme(style="whitegrid")
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        
        df_copy = df_data.copy()
        df_copy['Order Date'] = pd.to_datetime(df_copy['Order Date'])
        
        # 1. Monthly Sales Trend (Line chart)
        df_monthly = df_copy.groupby(df_copy['Order Date'].dt.to_period('M'))['Total Sales'].sum()
        df_monthly.index = df_monthly.index.to_timestamp()
        sns.lineplot(x=df_monthly.index, y=df_monthly.values, ax=axes[0, 0], marker='o', color='#2563eb', linewidth=2.5)
        axes[0, 0].set_title('Monthly Sales Trend', fontsize=12, fontweight='bold')
        axes[0, 0].set_xlabel('Order Date', fontsize=10)
        axes[0, 0].set_ylabel('Total Sales (₹)', fontsize=10)
        
        # 2. Sales by Category (Vertical bar chart)
        df_cat = df_copy.groupby('Category')['Total Sales'].sum().reset_index()
        sns.barplot(x='Category', y='Total Sales', data=df_cat, ax=axes[0, 1], hue='Category', legend=False, palette='Set2')
        axes[0, 1].set_title('Sales by Category', fontsize=12, fontweight='bold')
        axes[0, 1].set_xlabel('Category', fontsize=10)
        axes[0, 1].set_ylabel('Total Sales (₹)', fontsize=10)
        
        # 3. Sales by Region (Horizontal bar chart)
        df_reg = df_copy.groupby('Region')['Total Sales'].sum().reset_index()
        sns.barplot(y='Region', x='Total Sales', data=df_reg, ax=axes[1, 0], hue='Region', legend=False, palette='viridis')
        axes[1, 0].set_title('Sales by Region', fontsize=12, fontweight='bold')
        axes[1, 0].set_ylabel('Region', fontsize=10)
        axes[1, 0].set_xlabel('Total Sales (₹)', fontsize=10)
        
        # 4. Top 5 Products by Sales (Vertical bar chart)
        df_prod = df_copy.groupby('Product')['Total Sales'].sum().reset_index().sort_values(by='Total Sales', ascending=False).head(5)
        sns.barplot(x='Product', y='Total Sales', data=df_prod, ax=axes[1, 1], hue='Product', legend=False, palette='coolwarm')
        axes[1, 1].set_title('Top 5 Products by Sales', fontsize=12, fontweight='bold')
        axes[1, 1].set_xlabel('Product', fontsize=10)
        axes[1, 1].set_ylabel('Total Sales (₹)', fontsize=10)
        axes[1, 1].tick_params(axis='x', rotation=15)
        
        plt.tight_layout()
        img_dir = os.path.join('static', 'img')
        os.makedirs(img_dir, exist_ok=True)
        plt.savefig(os.path.join(img_dir, 'matplotlib_charts.png'), dpi=300)
        plt.close()
        print("Generated Matplotlib analytical charts at static/img/matplotlib_charts.png")
    except Exception as e:
        print(f"Error generating Matplotlib charts: {e}")

# Determine base directory safely
try:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    BASE_DIR = os.path.abspath(os.getcwd())

# Load Sales Data and ML Model at Startup
df = None
try:
    data_path = os.path.join(BASE_DIR, 'cleaning', 'sales_data_cleaned.csv')
    if not os.path.exists(data_path):
        data_path = os.path.join('cleaning', 'sales_data_cleaned.csv')
    if os.path.exists(data_path):
        df = pd.read_csv(data_path)
        df['Order Date'] = pd.to_datetime(df['Order Date'])
        print(f"Loaded dataset: {df.shape[0]} rows.")
        generate_matplotlib_charts(df)
except Exception as e:
    print(f"Error loading sales dataset: {e}")

model = None
def load_forecasting_model():
    global model
    if model is None:
        try:
            model_path = os.path.join(BASE_DIR, 'cleaning', 'sales_forecasting_model.pkl')
            if not os.path.exists(model_path):
                model_path = os.path.join('cleaning', 'sales_forecasting_model.pkl')
            if os.path.exists(model_path):
                model = joblib.load(model_path)
                print("Loaded Random Forest model successfully.")
        except Exception as e:
            print(f"Error loading forecasting model: {e}")

load_forecasting_model()

# Page Routes
@app.route('/')
def login():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/register')
def register():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    global df
    if 'username' not in session:
        return redirect(url_for('login'))
        
    if df is not None:
        total_sales = df['Total Sales'].sum()
        total_orders = len(df)
        total_qty = df['Quantity'].sum()
        avg_price = df['Unit Price'].mean()
        total_profit = total_sales * 0.15 # 15% profit margin
        
        # 10 recent transactions from the dataset
        recent_df = df.sort_values(by='Order Date', ascending=False).head(10)
        names = ['Amit Patel', 'Rahul Sharma', 'Priya Nair', 'Neha Gupta', 'Vikram Singh', 
                 'Anjali Desai', 'John Doe', 'David Smith', 'Sarah Connor', 'Michael Scott']
        
        recent_orders = []
        for idx, row in recent_df.iterrows():
            order_id = int(row['Order ID'])
            cust_name = names[order_id % len(names)]
            status = 'Completed' if order_id % 4 == 0 else ('Pending' if order_id % 4 == 1 else ('Shipped' if order_id % 4 == 2 else 'Cancelled'))
            recent_orders.append({
                'order_id': order_id,
                'customer': cust_name,
                'product': row['Product'],
                'amount': row['Total Sales'],
                'status': status
            })
    else:
        total_sales = 0
        total_orders = 0
        total_qty = 0
        avg_price = 0
        total_profit = 0
        recent_orders = []
        
    return render_template(
        'dashboard.html', 
        username=session['username'],
        total_sales=total_sales,
        total_orders=total_orders,
        total_qty=total_qty,
        avg_price=avg_price,
        total_profit=total_profit,
        recent_orders=recent_orders
    )

@app.route('/predict', methods=['GET', 'POST'])
def predict():
    if 'username' not in session:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        if model is None:
            load_forecasting_model()
        if model is None:
            flash("Machine learning model not available.", "danger")
            return redirect(url_for('predict'))
            
        try:
            quantity = int(request.form.get('quantity', 10))
            unit_price = float(request.form.get('unit_price', 2500))
            year = int(request.form.get('year', 2024))
            month = int(request.form.get('month', 5))
            quarter = int(request.form.get('quarter', 2))
            day_of_week = request.form.get('day_of_week', 'Wednesday')
            is_weekend = int(request.form.get('is_weekend', 0))
            avg_price = float(request.form.get('avg_price', 2500))
            
            # Predict using the 8 features expected by the updated model
            day_map = {
                'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3, 
                'Friday': 4, 'Saturday': 5, 'Sunday': 6
            }
            day_num = day_map.get(day_of_week, 2)
            
            input_df = pd.DataFrame(
                [[quantity, unit_price, year, month, quarter, day_num, is_weekend, avg_price]], 
                columns=['Quantity', 'Unit Price', 'Year', 'Month', 'Quarter', 'day_of_week', 'Is Weekend', 'Avg Price']
            )
            
            prediction = model.predict(input_df)[0]
            
            # Map month index to name for display
            months_names = {
                1: 'January', 2: 'February', 3: 'March', 4: 'April', 5: 'May', 6: 'June',
                7: 'July', 8: 'August', 9: 'September', 10: 'October', 11: 'November', 12: 'December'
            }
            month_name = months_names.get(month, 'May')
            
            return render_template(
                'result.html', 
                prediction=prediction, 
                quantity=quantity,
                unit_price=unit_price,
                year=year,
                month_name=month_name,
                quarter=quarter,
                day_of_week=day_of_week,
                is_weekend='Yes' if is_weekend == 1 else 'No',
                avg_price=avg_price
            )
        except Exception as e:
            flash(f"Forecasting calculation failed: {str(e)}", "danger")
            return redirect(url_for('predict'))
            
    return render_template('predict.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    global df
    if 'username' not in session:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        if 'file' not in request.files:
            flash("No file part selected.", "danger")
            return redirect(url_for('upload'))
            
        file = request.files['file']
        if file.filename == '':
            flash("No file selected.", "danger")
            return redirect(url_for('upload'))
            
        if not file.filename.endswith('.csv'):
            flash("Only CSV files are supported.", "danger")
            return redirect(url_for('upload'))
            
        try:
            # Validate columns
            temp_df = pd.read_csv(file)
            required_cols = ['Order ID', 'Order Date', 'Product', 'Category', 'Quantity', 'Unit Price', 'Total Sales', 'Region']
            missing = [c for c in required_cols if c not in temp_df.columns]
            
            if missing:
                flash(f"Invalid file structure. Missing columns: {', '.join(missing)}", "danger")
                return redirect(url_for('upload'))
                
            # Overwrite active dataset file
            dest_path = os.path.join('cleaning', 'sales_data_cleaned.csv')
            temp_df.to_csv(dest_path, index=False)
            
            # Reload dataset in memory
            df = pd.read_csv(dest_path)
            df['Order Date'] = pd.to_datetime(df['Order Date'])
            
            # Regenerate analytics visuals
            generate_matplotlib_charts(df)
            
            flash("Dataset uploaded and processed successfully! Analytics updated.", "success")
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            flash(f"Error processing dataset: {str(e)}", "danger")
            return redirect(url_for('upload'))
            
    return render_template('upload.html')

@app.route('/report')
def report():
    if 'username' not in session:
        return redirect(url_for('login'))
        
    if df is None:
        return "Dataset not found", 404
        
    total_sales = df['Total Sales'].sum()
    total_orders = len(df)
    total_qty = df['Quantity'].sum()
    avg_price = df['Unit Price'].mean()
    total_profit = total_sales * 0.15
    
    # 1. Category stats
    cat_df = df.groupby('Category').agg(
        sales=('Total Sales', 'sum'),
        orders=('Order ID', 'count')
    )
    cat_df['pct'] = (cat_df['sales'] / total_sales) * 100
    category_summary = []
    for cat, row in cat_df.iterrows():
        category_summary.append({
            'name': cat,
            'sales': row['sales'],
            'pct': row['pct'],
            'orders': int(row['orders'])
        })
        
    # 2. Region stats
    reg_df = df.groupby('Region').agg(
        sales=('Total Sales', 'sum')
    )
    reg_df['pct'] = (reg_df['sales'] / total_sales) * 100
    region_summary = []
    for reg, row in reg_df.iterrows():
        region_summary.append({
            'name': reg,
            'sales': row['sales'],
            'pct': row['pct']
        })
        
    # 3. Top products stats
    prod_df = df.groupby('Product').agg(
        sales=('Total Sales', 'sum'),
        qty=('Quantity', 'sum'),
        avg_unit_price=('Unit Price', 'mean')
    ).sort_values(by='sales', ascending=False).head(5)
    
    top_products = []
    for prod, row in prod_df.iterrows():
        top_products.append({
            'name': prod,
            'sales': row['sales'],
            'qty': int(row['qty']),
            'avg_unit_price': row['avg_unit_price']
        })
        
    return render_template(
        'report.html',
        total_sales=total_sales,
        total_orders=total_orders,
        total_qty=total_qty,
        avg_price=avg_price,
        total_profit=total_profit,
        category_summary=category_summary,
        region_summary=region_summary,
        top_products=top_products
    )

# Auth Endpoints
@app.route('/login', methods=['POST'])
def login_post():
    username = request.form.get('username')
    password = request.form.get('password')
    
    if not username or not password:
        flash("Please enter both username and password.", "danger")
        return redirect(url_for('login'))
        
    try:
        conn, db_type = get_db_connection()
        if db_type == 'mysql':
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        else:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user:
            user_pwd = user['password']
            user_id = user['id']
            user_name = user['username']
            if user_pwd == password or check_password_hash(user_pwd, password):
                session['user_id'] = user_id
                session['username'] = user_name
                return redirect(url_for('dashboard'))
                
        flash("Invalid username or password.", "danger")
    except Exception as e:
        flash(f"Database error: {str(e)}", "danger")
        
    return redirect(url_for('login'))

@app.route('/register', methods=['POST'])
def register_post():
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')
    
    if not username or not email or not password or not confirm_password:
        flash("All fields are required.", "danger")
        return redirect(url_for('register'))
        
    if password != confirm_password:
        flash("Passwords do not match.", "danger")
        return redirect(url_for('register'))
        
    try:
        conn, db_type = get_db_connection()
        if db_type == 'mysql':
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE username = %s OR email = %s", (username, email))
        else:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username = ? OR email = ?", (username, email))
            
        existing_user = cursor.fetchone()
        
        if existing_user:
            flash("Username or Email already registered.", "danger")
            cursor.close()
            conn.close()
            return redirect(url_for('register'))
            
        hashed_password = generate_password_hash(password)
        if db_type == 'mysql':
            cursor.execute(
                "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
                (username, email, hashed_password)
            )
        else:
            cursor.execute(
                "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                (username, email, hashed_password)
            )
        conn.commit()
        cursor.close()
        conn.close()
        
        flash("Registration successful! Please login.", "success")
        return redirect(url_for('login'))
    except Exception as e:
        flash(f"Registration failed: {str(e)}", "danger")
        return redirect(url_for('register'))

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
