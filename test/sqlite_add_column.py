import sqlite3

# 连接当前目录下的sqlite数据库文件
conn = sqlite3.connect("tokens.db")  # test.db 在当前工作目录
cur = conn.cursor()

# 新增一列，允许为空，默认值NULL
table_name = "Tokens"
new_col = "password"
# TEXT 类型，可以改成 INTEGER / REAL / BLOB
sql = f'ALTER TABLE {table_name} ADD COLUMN {new_col} TEXT NULL;'

try:
    cur.execute(sql)
    conn.commit()
    print(f"成功新增列 {new_col}")
except sqlite3.OperationalError as e:
    print("出错：", e)
finally:
    conn.close()
