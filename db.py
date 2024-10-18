import sqlite3

# Инициализация базы данных
def create_connection():
    return sqlite3.connect('bot_database.db')

# Создание всех необходимых таблиц
def create_table(conn):
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            admin_username TEXT PRIMARY KEY
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS managers (
            manager_username TEXT PRIMARY KEY
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chats (
            chat_id INTEGER PRIMARY KEY,
            developer_username TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vacations (
            chat_id INTEGER,
            start_date TEXT,
            end_date TEXT,
            FOREIGN KEY (chat_id) REFERENCES chats(chat_id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vacation_requests (
            chat_id INTEGER,
            developer_username TEXT,
            start_date TEXT,
            end_date TEXT,
            PRIMARY KEY (chat_id, developer_username)
        )
    ''')

    conn.commit()

# Функции работы с запросами на отпуск
def save_vacation_request(conn, chat_id, developer_username, start_date, end_date):
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO vacation_requests (chat_id, developer_username, start_date, end_date) VALUES (?, ?, ?, ?)", 
                   (chat_id, developer_username, start_date, end_date))
    conn.commit()

def get_vacation_request(conn, chat_id):
    cursor = conn.cursor()
    cursor.execute("SELECT developer_username, start_date, end_date FROM vacation_requests WHERE chat_id = ?", (chat_id,))
    return cursor.fetchone()

def delete_vacation_request(conn, chat_id):
    cursor = conn.cursor()
    cursor.execute("DELETE FROM vacation_requests WHERE chat_id = ?", (chat_id,))
    conn.commit()

# Функции работы с отпуском
def save_vacation(conn, chat_id, start_date, end_date):
    cursor = conn.cursor()
    cursor.execute("INSERT INTO vacations (chat_id, start_date, end_date) VALUES (?, ?, ?)", 
                   (chat_id, start_date, end_date))
    conn.commit()

# Добавление менеджера в таблицу managers
def add_manager(conn, manager_username):
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO managers (manager_username) VALUES (?)", (manager_username,))
    conn.commit()

# Удаление менеджера из таблицы managers
def delete_manager(conn, manager_username):
    cursor = conn.cursor()
    cursor.execute("DELETE FROM managers WHERE manager_username = ?", (manager_username,))
    conn.commit()
