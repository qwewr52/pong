import sqlite3
import hashlib
import os
from datetime import datetime

class Database:
    def __init__(self, db_name="users.db"):
        self.db_name = db_name
        self.init_database()

    def init_database(self):
        """Инициализация базы данных и создание таблиц"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Создание таблицы пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                login_attempts INTEGER DEFAULT 0,
                last_attempt TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Создание таблицы для логирования попыток входа
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS login_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                email TEXT NOT NULL,
                success BOOLEAN NOT NULL,
                attempt_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        conn.commit()
        conn.close()

    def _hash_password(self, password):
        """Хеширование пароля"""
        return hashlib.sha256(password.encode()).hexdigest()

    def user_exists(self, email):
        """Проверка существования пользователя по email"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        result = cursor.fetchone()
        
        conn.close()
        return result is not None

    def get_login_attempts(self, email):
        """Получение количества неудачных попыток входа"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute("SELECT login_attempts FROM users WHERE email = ?", (email,))
        result = cursor.fetchone()
        
        conn.close()
        return result[0] if result else 0

    def check_user(self, email, password):
        """Проверка учетных данных пользователя"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, name, email, password_hash FROM users WHERE email = ?", (email,))
        result = cursor.fetchone()
        
        if result and result[3] == self._hash_password(password):
            user_data = (result[0], result[1], result[2])
            # Логируем успешную попытку
            self._log_login_attempt(result[0], email, True)
            conn.close()
            return user_data
        
        # Логируем неудачную попытку
        if result:
            self._log_login_attempt(result[0], email, False)
        else:
            self._log_login_attempt(None, email, False)
            
        conn.close()
        return None

    def update_login_attempts(self, email, success):
        """Обновление счетчика попыток входа"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        if success:
            # Сброс счетчика при успешном входе
            cursor.execute('''
                UPDATE users 
                SET login_attempts = 0, last_attempt = CURRENT_TIMESTAMP 
                WHERE email = ?
            ''', (email,))
        else:
            # Увеличение счетчика при неудачной попытке
            cursor.execute('''
                UPDATE users 
                SET login_attempts = login_attempts + 1, last_attempt = CURRENT_TIMESTAMP 
                WHERE email = ?
            ''', (email,))
        
        conn.commit()
        conn.close()

    def register_user(self, name, email, password):
        """Регистрация нового пользователя"""
        if self.user_exists(email):
            return False
            
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            password_hash = self._hash_password(password)
            cursor.execute('''
                INSERT INTO users (name, email, password_hash) 
                VALUES (?, ?, ?)
            ''', (name, email, password_hash))
            
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            conn.close()
            return False

    def _log_login_attempt(self, user_id, email, success):
        """Логирование попытки входа"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO login_logs (user_id, email, success) 
            VALUES (?, ?, ?)
        ''', (user_id, email, success))
        
        conn.commit()
        conn.close()

    def get_user_stats(self, email):
        """Получение статистики пользователя"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT u.name, u.email, u.login_attempts, u.created_at,
                   (SELECT COUNT(*) FROM login_logs WHERE user_id = u.id AND success = 1) as successful_logins,
                   (SELECT COUNT(*) FROM login_logs WHERE user_id = u.id AND success = 0) as failed_logins
            FROM users u
            WHERE u.email = ?
        ''', (email,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'name': result[0],
                'email': result[1],
                'login_attempts': result[2],
                'created_at': result[3],
                'successful_logins': result[4],
                'failed_logins': result[5]
            }
        return None

    def get_all_users(self):
        """Получение списка всех пользователей (для администрирования)"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, name, email, login_attempts, created_at 
            FROM users 
            ORDER BY created_at DESC
        ''')
        
        users = cursor.fetchall()
        conn.close()
        return users

    def delete_user(self, email):
        """Удаление пользователя"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM users WHERE email = ?", (email,))
            conn.commit()
            conn.close()
            return True
        except:
            conn.close()
            return False

# Создание тестового пользователя при первом запуске
def create_test_user():
    db = Database()
    if not db.user_exists("test@test.com"):
        db.register_user("Тестовый пользователь", "test@test.com", "123456")
        print("Создан тестовый пользователь: test@test.com / 123456")

if __name__ == "__main__":
    create_test_user()
