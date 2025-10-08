import sqlite3
import hashlib


class Database:
    def __init__(self, db_name="users.db"):
        self.db_name = db_name
        self.init_database()

    def init_database(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                login_attempts INTEGER DEFAULT 0,
                last_attempt TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
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
        return hashlib.sha256(password.encode()).hexdigest()

    def user_exists(self, email):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        result = cursor.fetchone()
        conn.close()
        return result is not None

    def get_login_attempts(self, email):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        q = "SELECT login_attempts FROM users WHERE email=?"
        cursor.execute(q, (email,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else 0

    def check_user(self, email, password):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        q = "SELECT id,name,email,password_hash FROM users WHERE email=?"
        cursor.execute(q, (email,))
        result = cursor.fetchone()

        if result and result[3] == self._hash_password(password):
            user_data = (result[0], result[1], result[2])
            self._log_login_attempt(result[0], email, True)
            self.update_login_attempts(email, True)
            conn.close()
            return user_data

        self._log_login_attempt(result[0] if result else None, email, False)
        self.update_login_attempts(email, False)
        conn.close()
        return None

    def update_login_attempts(self, email, success):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        attempts = 0 if success else self.get_login_attempts(email) + 1
        cursor.execute('''
            UPDATE users
            SET login_attempts = ?, last_attempt = CURRENT_TIMESTAMP
            WHERE email = ?
        ''', (attempts, email))
        conn.commit()
        conn.close()

    def register_user(self, name, email, password):
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
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO login_logs (user_id, email, success)
            VALUES (?, ?, ?)
        ''', (user_id, email, success))
        conn.commit()
        conn.close()

    def get_user_stats(self, email):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT u.name, u.email, u.login_attempts, u.created_at,
                   (SELECT COUNT(*) FROM login_logs
                    WHERE user_id = u.id AND success = 1),
                    (SELECT COUNT(*) FROM login_logs
                    WHERE user_id = u.id AND success = 0)
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
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE email = ?", (email,))
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        return affected > 0


if __name__ == "__main__":

    db = Database()
    print("База данных инициализирована")
