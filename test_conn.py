import mysql.connector

conn = mysql.connector.connect(
    host="interchange.proxy.rlwy.net",
    port=39247,
    user="root",
    password="bMRPKJnHNxBllzbZCYzdqjXuaRJyhlsj",
    database="railway"
)
print('Connected!')
conn.close()