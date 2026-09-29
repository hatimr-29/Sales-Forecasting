import mysql.connector
import sys, traceback
print("Testing mysql connector with use_pure=True...")
try:
    conn = mysql.connector.connect(
        host="localhost", user="root", password="wrong", database="test", connect_timeout=1, use_pure=True
    )
    print("MySQL connected!")
except Exception as e:
    print("Caught MySQL exception cleanly with use_pure=True:", type(e), e)
