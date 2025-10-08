import sys
import random
import re
import os
import sqlite3
from PyQt5.QtWidgets import (
    QApplication, QWidget, QTabWidget, QVBoxLayout, QLabel,
    QLineEdit, QPushButton, QFormLayout, QMessageBox, QGridLayout, QHBoxLayout
)
from PyQt5.QtCore import Qt, QMimeData, QTimer
from PyQt5.QtGui import QPixmap, QDrag, QPainter, QColor, QFont
from database import Database


class PuzzlePiece(QLabel):
    def __init__(self, pixmap, correct_position, parent=None):
        super().__init__(parent)
        self.setPixmap(pixmap.scaled(100, 100, Qt.KeepAspectRatio))
        self.correct_position = correct_position
        self.setStyleSheet("border:2px solid #333;background:#fff;margin:2px")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setScaledContents(True)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            drag = QDrag(self)
            mime_data = QMimeData()
            mime_data.setText(str(self.correct_position))
            drag.setMimeData(mime_data)
            drag.setPixmap(self.pixmap())
            drag.setHotSpot(event.pos())
            drag.exec(Qt.DropAction.MoveAction)


class TargetLabel(QLabel):
    def __init__(self, index, captcha_widget):
        super().__init__()
        self.index = index
        self.captcha_widget = captcha_widget
        self.setFixedSize(110, 110)
        self.setStyleSheet("border:2px dashed #666;background:#f8f8f8")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        if event.mimeData().hasText():
            correct_position = int(event.mimeData().text())
            source = event.source()
            if isinstance(source, PuzzlePiece):
                if self.pixmap() and not self.pixmap().isNull():
                    self.captcha_widget.return_piece_to_source(self)
                self.setPixmap(source.pixmap())
                source.hide()
                self.correct_position = correct_position
                event.acceptProposedAction()
                self.captcha_widget.auto_check_completion()


class CaptchaWidget(QWidget):
    def __init__(self, image_paths):
        super().__init__()
        self.image_paths = image_paths
        self.num_pieces = len(image_paths)
        self.target_labels = []
        self.correct_positions = list(range(self.num_pieces))
        self.is_completed = False
        self.on_success = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Проверка безопасности")
        self.setFixedSize(700, 500)
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.setSpacing(10)
        title_label = QLabel("Соберите пазл")
        title_label.setStyleSheet("font:bold 16px; margin:10px;")
        main_layout.addWidget(title_label, alignment=Qt.AlignCenter)
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        self.source_widget = QWidget()
        self.source_layout = QGridLayout(self.source_widget)
        self.source_layout.setSpacing(5)
        self.source_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(self.source_widget)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        self.target_widget = QWidget()
        self.target_layout = QGridLayout(self.target_widget)
        self.target_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(self.target_widget)
        content_layout.addWidget(left_widget)
        content_layout.addWidget(right_widget)
        main_layout.addLayout(content_layout)
        self.reset_button = QPushButton("Начать заново")
        self.reset_button.setFixedSize(120, 35)
        self.reset_button.setStyleSheet("font-size:12px")
        self.reset_button.clicked.connect(self.reset_puzzle)
        main_layout.addWidget(self.reset_button, alignment=Qt.AlignCenter)
        self.load_pieces()

    def load_pieces(self):
        images = []
        for path in self.image_paths:
            pixmap = QPixmap(os.path.join(os.path.dirname(__file__), path))
            if pixmap.isNull():
                pixmap = QPixmap(100, 100)
                color = QColor(
                    random.randint(50, 200),
                    random.randint(50, 200),
                    random.randint(50, 200)
                )
                pixmap.fill(color)
            images.append(pixmap)
        self.pieces = [PuzzlePiece(p, i, self) for i, p in enumerate(images)]
        random.shuffle(self.pieces)
        positions = [(0, 0), (0, 1), (1, 0), (1, 1)]
        for i, piece in enumerate(self.pieces):
            if i < len(positions):
                row, col = positions[i]
                self.source_layout.addWidget(piece, row, col, Qt.AlignCenter)
        self.target_labels = [TargetLabel(i, self) for i in range(4)]
        for i, label in enumerate(self.target_labels):
            row, col = i // 2, i % 2
            self.target_layout.addWidget(label, row, col, Qt.AlignCenter)

    def return_piece_to_source(self, target_label):
        if hasattr(target_label, 'correct_position'):
            for piece in self.pieces:
                if piece.correct_position == target_label.correct_position:
                    piece.show()
                    for i in range(self.source_layout.count()):
                        item = self.source_layout.itemAt(i)
                        if not item or not item.widget():
                            row, col = i // 2, i % 2
                            self.source_layout.addWidget(piece, row, col)
                            break
                    break
        target_label.clear()
        target_label.setStyleSheet("border:2px dashed #666;background:#f8f8f8")

    def all_cells_filled(self):
        return all(
            label.pixmap() and not label.pixmap().isNull()
            for label in self.target_labels
        )

    def auto_check_completion(self):
        if not self.all_cells_filled():
            return
        self.is_completed = all(
            label.correct_position == i
            for i, label in enumerate(self.target_labels)
        )
        if self.is_completed:
            QTimer.singleShot(300, self.on_captcha_success)

    def on_captcha_success(self):
        QMessageBox.information(self, "Успех", "Проверка пройдена!")
        if self.on_success:
            self.on_success()
        self.close()

    def reset_puzzle(self):
        for label in self.target_labels:
            if label.pixmap() and not label.pixmap().isNull():
                self.return_piece_to_source(label)
        for piece in self.pieces:
            piece.show()
        for i in reversed(range(self.source_layout.count())):
            item = self.source_layout.itemAt(i)
            if item and item.widget():
                item.widget().setParent(None)
        random.shuffle(self.pieces)
        positions = [(0, 0), (0, 1), (1, 0), (1, 1)]
        for i, piece in enumerate(self.pieces):
            if i < len(positions):
                row, col = positions[i]
                self.source_layout.addWidget(piece, row, col, Qt.AlignCenter)
        self.is_completed = False


class AuthWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.max_attempts = 3
        self.pong_game = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Вход и регистрация")
        self.resize(400, 350)
        self.layout = QVBoxLayout()
        self.tabs = QTabWidget()
        self.setup_login_tab()
        self.setup_register_tab()
        self.tabs.addTab(self.login_tab, "Вход")
        self.tabs.addTab(self.register_tab, "Регистрация")
        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)

    def setup_login_tab(self):
        self.login_tab = QWidget()
        self.login_layout = QFormLayout()
        self.login_email = QLineEdit()
        self.login_email.setPlaceholderText("test@test.com")
        self.login_password = QLineEdit()
        self.login_password.setPlaceholderText("123456")
        self.login_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.login_button = QPushButton("Войти")
        self.login_button.clicked.connect(self.handle_login)
        self.login_layout.addRow("Электронная почта:", self.login_email)
        self.login_layout.addRow("Пароль:", self.login_password)
        self.login_layout.addRow(self.login_button)
        self.login_tab.setLayout(self.login_layout)

    def setup_register_tab(self):
        self.register_tab = QWidget()
        self.register_layout = QFormLayout()
        self.reg_name = QLineEdit()
        self.reg_name.setPlaceholderText("Введите ваше имя")
        self.reg_email = QLineEdit()
        self.reg_email.setPlaceholderText("Введите ваш email")
        self.reg_password = QLineEdit()
        self.reg_password.setPlaceholderText("Придумайте пароль")
        self.reg_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.register_button = QPushButton("Зарегистрироваться")
        self.register_button.clicked.connect(self.handle_register)
        self.register_layout.addRow("Имя:", self.reg_name)
        self.register_layout.addRow("Электронная почта:", self.reg_email)
        self.register_layout.addRow("Пароль:", self.reg_password)
        self.register_layout.addRow(self.register_button)
        self.register_tab.setLayout(self.register_layout)

    def handle_login(self):
        email = self.login_email.text().strip()
        password = self.login_password.text().strip()

        if not email or not password:
            QMessageBox.warning(self, "Ошибка", "Заполните все поля!")
            return

        # Создаем временную запись для подсчета попыток, если пользователя нет
        if not self.db.user_exists(email):
            self.create_login_attempt_record(email)

        login_attempts = self.db.get_login_attempts(email)

        if login_attempts >= self.max_attempts:
            QMessageBox.warning(
                self,
                "Слишком много попыток",
                "Превышено количество попыток входа."
            )
            self.show_captcha(email)
            return

        user_exists = self.db.user_exists(email)
        user = self.db.check_user(email, password) if user_exists else None

        if user_exists and user:
            # Успешный вход - сбрасываем попытки
            self.db.update_login_attempts(email, True)
            QMessageBox.information(self, "Успех", f"Вход выполнен, {user[1]}")
            self.open_pong_game(user[1])
            return

        # Неудачная попытка - увеличиваем счетчик
        self.db.update_login_attempts(email, False)

        updated_attempts = self.db.get_login_attempts(email)
        remaining_attempts = self.max_attempts - updated_attempts

        if remaining_attempts > 0:
            if not user_exists:
                error_msg = "Пользователь не найден"
            else:
                error_msg = "Неверный пароль"

            QMessageBox.warning(
                self,
                "Ошибка входа",
                f"{error_msg}. Осталось попыток: {remaining_attempts}"
            )
        else:
            QMessageBox.warning(
                self,
                "Слишком много попыток",
                "Требуется проверка безопасности."
            )
            self.show_captcha(email)

    def create_login_attempt_record(self, email):
        """Создает временную запись для подсчета попыток входа"""
        conn = sqlite3.connect(self.db.db_name)
        cursor = conn.cursor()
        try:
            sql = 'INSERT OR IGNORE INTO users (email,password_hash,name,login_attempts)VALUES (?,?,?,?)'
            cursor.execute(sql, (email, 'temp_hash', 'temp_user', 1))
            conn.commit()
        except Exception as e:
            print(f"Error creating login attempt record: {e}")
        finally:
            conn.close()

    def show_captcha(self, email):
        image_paths = [
            os.path.join(os.path.dirname(__file__), f'{i}.png')
            for i in range(1, 5)
        ]
        self.captcha_window = CaptchaWidget(image_paths)
        self.captcha_window.on_success = lambda: self.on_captcha_success(email)
        self.captcha_window.show()

    def on_captcha_success(self, email):
        self.db.update_login_attempts(email, True)
        QMessageBox.information(
            self,
            "Доступ восстановлен",
            "Проверка пройдена! Можно продолжить вход."
        )

    def handle_register(self):
        name = self.reg_name.text().strip()
        email = self.reg_email.text().strip()
        password = self.reg_password.text().strip()
        if not name or not email or not password:
            QMessageBox.warning(self, "Ошибка", "Заполните все поля!")
            return
        if len(password) < 6:
            QMessageBox.warning(self, "Ошибка", "Пароль 6 символов!")
            return
        if not self.is_valid_email(email):
            QMessageBox.warning(self, "Ошибка", "Введите корректный email!")
            return
        if self.db.register_user(name, email, password):
            QMessageBox.information(self, "Успех", "Регистрация выполнена!")
            self.reg_name.clear()
            self.reg_email.clear()
            self.reg_password.clear()
            self.tabs.setCurrentIndex(0)
        else:
            QMessageBox.warning(self, "Ошибка", "Email занят!")

    def is_valid_email(self, email):
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return re.match(email_pattern, email) is not None

    def open_pong_game(self, username):
        if self.pong_game is None:
            self.pong_game = PongGame(username)
        self.pong_game.show()
        self.close()


class PongGame(QWidget):
    def __init__(self, username):
        super().__init__()
        self.username = username
        self.paddle_width = 10
        self.paddle_height = 100
        self.ball_size = 20
        self.paddle_speed = 5
        self.ball_speed_x = 5.0
        self.ball_speed_y = 5.0
        self.ball_acceleration = 0.001
        self.max_ball_speed = 10.0
        self.plr1_y = 250
        self.player2_y = 250
        self.ball_x = 390.0
        self.ball_y = 290.0
        self.score1 = 0
        self.score2 = 0
        self.keys_pressed = {}
        self.font = QFont('Arial', 20)
        self.font_user = QFont('Arial', 12)
        self.setFixedSize(800, 600)
        self.setWindowTitle("Понг - Мультиплеер")
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_game)
        self.timer.start(16)

    def keyPressEvent(self, event):
        self.keys_pressed[event.key()] = True
        if event.key() == Qt.Key_R:
            self.restart_game()

    def keyReleaseEvent(self, event):
        self.keys_pressed[event.key()] = False

    def update_game(self):
        if self.keys_pressed.get(Qt.Key_W, False):
            self.plr1_y = max(0, self.plr1_y - self.paddle_speed)
        if self.keys_pressed.get(Qt.Key_S, False):
            self.plr1_y = min(
                self.height() - self.paddle_height,
                self.plr1_y + self.paddle_speed
            )
        if self.keys_pressed.get(Qt.Key_Up, False):
            self.player2_y = max(0, self.player2_y - self.paddle_speed)
        if self.keys_pressed.get(Qt.Key_Down, False):
            self.player2_y = min(
                self.height() - self.paddle_height,
                self.player2_y + self.paddle_speed
            )
        accel = self.ball_acceleration
        sign_x = 1 if self.ball_speed_x > 0 else -1
        sign_y = 1 if self.ball_speed_y > 0 else -1
        self.ball_speed_x += accel * sign_x
        self.ball_speed_y += accel * sign_y
        self.ball_speed_x = min(
            max(self.ball_speed_x, -self.max_ball_speed), self.max_ball_speed
        )
        self.ball_speed_y = min(
            max(self.ball_speed_y, -self.max_ball_speed), self.max_ball_speed
        )
        self.ball_x += self.ball_speed_x
        self.ball_y += self.ball_speed_y
        if self.ball_y <= 0 or self.ball_y + self.ball_size >= self.height():
            self.ball_speed_y *= -1
        if (self.ball_x <= self.paddle_width and
                self.plr1_y <= self.ball_y + self.ball_size and
                self.ball_y <= self.plr1_y + self.paddle_height):
            self.ball_speed_x *= -1
        if (self.ball_x + self.ball_size >= self.width()-self.paddle_width and
                self.player2_y <= self.ball_y + self.ball_size and
                self.ball_y <= self.player2_y + self.paddle_height):
            self.ball_speed_x *= -1
        if self.ball_x < 0:
            self.score2 += 1
            self.reset_ball()
        if self.ball_x > self.width():
            self.score1 += 1
            self.reset_ball()
        if self.score1 >= 5 or self.score2 >= 5:
            self.timer.stop()
            winner = self.username if self.score1 > self.score2 else "Игрок 2"
            QMessageBox.information(
                self,
                "Игра окончена",
                f"Победитель: {winner}\nНажмите R для рестарта."
            )
        self.update()

    def reset_ball(self):
        self.ball_x = self.width() // 2 - self.ball_size // 2
        self.ball_y = self.height() // 2 - self.ball_size // 2
        self.ball_speed_x = 5.0 if random.choice([True, False]) else -5.0
        self.ball_speed_y = 5.0 if random.choice([True, False]) else -5.0

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0))
        painter.setBrush(QColor(255, 255, 255))
        painter.drawRect(0, self.plr1_y, self.paddle_width, self.paddle_height)
        painter.drawRect(
            self.width() - self.paddle_width,
            self.player2_y,
            self.paddle_width,
            self.paddle_height
        )
        painter.drawEllipse(
            int(self.ball_x), int(self.ball_y), self.ball_size, self.ball_size
        )
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(self.font)
        painter.drawText(self.width() // 4, 30, str(self.score1))
        painter.drawText(self.width() * 3 // 4, 30, str(self.score2))
        painter.setFont(self.font_user)
        painter.drawText(10, self.height() - 10, self.username)
        painter.drawText(self.width() - 100, self.height() - 10, "Игрок 2")

    def restart_game(self):
        self.score1 = 0
        self.score2 = 0
        self.plr1_y = self.height() // 2 - self.paddle_height // 2
        self.player2_y = self.height() // 2 - self.paddle_height // 2
        self.ball_speed_x = 5.0
        self.ball_speed_y = 5.0
        self.reset_ball()
        self.timer.start()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AuthWindow()
    window.show()
    sys.exit(app.exec())
