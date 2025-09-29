import sys
import random
import re
from PyQt5.QtWidgets import (
    QApplication, QWidget, QTabWidget, QVBoxLayout, QLabel,
    QLineEdit, QPushButton, QFormLayout, QMessageBox, QGridLayout, QHBoxLayout
)
from PyQt5.QtCore import Qt, QMimeData, QTimer
from PyQt5.QtGui import QPixmap, QDrag, QPainter, QColor, QFont

# Импортируем базу данных из отдельного файла
from database import Database, create_test_user

# Создаем тестового пользователя при импорте
create_test_user()

# Класс для кусочков капчи
class PuzzlePiece(QLabel):
    def __init__(self, pixmap, correct_position, parent=None):
        super().__init__(parent)
        self.setPixmap(pixmap.scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatio))
        self.correct_position = correct_position
        self.setStyleSheet("border: 2px solid #333; background-color: white; margin: 2px;")
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

# Класс для целевых ячеек
class TargetLabel(QLabel):
    def __init__(self, index, captcha_widget):
        super().__init__()
        self.index = index
        self.captcha_widget = captcha_widget
        self.setFixedSize(110, 110)
        self.setStyleSheet("border: 2px dashed #666; background-color: #f8f8f8;")
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

# Класс для капчи
class CaptchaWidget(QWidget):
    def __init__(self, image_paths):
        super().__init__()
        self.image_paths = image_paths
        self.num_pieces = len(image_paths)
        self.target_labels = []
        self.correct_positions = list(range(self.num_pieces))
        self.is_completed = False
        self.on_success = None

        self.initUI()

    def initUI(self):
        self.setWindowTitle("Проверка безопасности")
        self.setFixedSize(700, 500)

        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.setSpacing(10)

        title_label = QLabel("Соберите пазл")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        main_layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignCenter)

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
        self.reset_button.setStyleSheet("font-size: 12px;")
        self.reset_button.clicked.connect(self.reset_puzzle)
        main_layout.addWidget(self.reset_button, alignment=Qt.AlignmentFlag.AlignCenter)

        self.load_pieces()

    def load_pieces(self):
        images = []
        for path in self.image_paths:
            try:
                pixmap = QPixmap(path)
                if pixmap.isNull():
                    pixmap = QPixmap(100, 100)
                    color = QColor(random.randint(50, 200), random.randint(50, 200), random.randint(50, 200))
                    pixmap.fill(color)
                images.append(pixmap)
            except:
                pixmap = QPixmap(100, 100)
                color = QColor(random.randint(50, 200), random.randint(50, 200), random.randint(50, 200))
                images.append(pixmap)

        self.pieces = [PuzzlePiece(img, i, self) for i, img in enumerate(images)]
        random.shuffle(self.pieces)

        positions = [(0, 0), (0, 1), (1, 0), (1, 1)]
        for i, piece in enumerate(self.pieces):
            if i < len(positions):
                row, col = positions[i]
                self.source_layout.addWidget(piece, row, col, alignment=Qt.AlignmentFlag.AlignCenter)

        self.target_labels = []
        for i in range(4):
            label = TargetLabel(i, self)
            self.target_labels.append(label)
            row = i // 2
            col = i % 2
            self.target_layout.addWidget(label, row, col, alignment=Qt.AlignmentFlag.AlignCenter)

    def return_piece_to_source(self, target_label):
        if hasattr(target_label, 'correct_position'):
            for piece in self.pieces:
                if piece.correct_position == target_label.correct_position:
                    piece.show()
                    for i in range(self.source_layout.count()):
                        item = self.source_layout.itemAt(i)
                        if item and item.widget() is None:
                            row = i // 2
                            col = i % 2
                            self.source_layout.addWidget(piece, row, col)
                            break
                    break
        target_label.clear()
        target_label.setStyleSheet("border: 2px dashed #666; background-color: #f8f8f8;")

    def all_cells_filled(self):
        for label in self.target_labels:
            if label.pixmap() is None or label.pixmap().isNull():
                return False
        return True

    def auto_check_completion(self):
        if not self.all_cells_filled():
            return

        correct_count = 0
        for i, label in enumerate(self.target_labels):
            if hasattr(label, 'correct_position') and label.correct_position == i:
                correct_count += 1

        self.is_completed = (correct_count == self.num_pieces)

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
                self.source_layout.addWidget(piece, row, col, alignment=Qt.AlignmentFlag.AlignCenter)

        self.is_completed = False

# Основное окно авторизации
class AuthWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.max_attempts = 3
        self.pong_game = None
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Вход и Регистрация")
        self.resize(400, 350)

        self.layout = QVBoxLayout()
        self.tabs = QTabWidget()

        # Вкладка входа
        self.login_tab = QWidget()
        self.login_layout = QFormLayout()

        self.login_email = QLineEdit()
        self.login_email.setPlaceholderText("test@test.com")
        
        self.login_password = QLineEdit()
        self.login_password.setPlaceholderText("123456")
        self.login_password.setEchoMode(QLineEdit.EchoMode.Password)
        
        self.login_button = QPushButton("Войти")
        self.login_button.clicked.connect(self.handle_login)

        self.login_layout.addRow("Email:", self.login_email)
        self.login_layout.addRow("Пароль:", self.login_password)
        self.login_layout.addRow(self.login_button)

        self.login_tab.setLayout(self.login_layout)

        # Вкладка регистрации
        self.register_tab = QWidget()
        self.register_layout = QFormLayout()

        self.reg_name = QLineEdit()
        self.reg_name.setPlaceholderText("Введите ваше имя")
        
        self.reg_email = QLineEdit()
        self.reg_email.setPlaceholderText("Введите ваш email")
        
        self.reg_password = QLineEdit()
        self.reg_password.setPlaceholderText("Придумайте пароль (минимум 6 символов)")
        self.reg_password.setEchoMode(QLineEdit.EchoMode.Password)
        
        self.register_button = QPushButton("Зарегистрироваться")
        self.register_button.clicked.connect(self.handle_register)

        self.register_layout.addRow("Имя:", self.reg_name)
        self.register_layout.addRow("Email:", self.reg_email)
        self.register_layout.addRow("Пароль:", self.reg_password)
        self.register_layout.addRow(self.register_button)

        self.register_tab.setLayout(self.register_layout)

        self.tabs.addTab(self.login_tab, "Вход")
        self.tabs.addTab(self.register_tab, "Регистрация")

        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)

    def handle_login(self):
        email = self.login_email.text().strip()
        password = self.login_password.text().strip()

        if not email or not password:
            QMessageBox.warning(self, "Ошибка", "Заполните все поля!")
            return

        if not self.db.user_exists(email):
            QMessageBox.warning(self, "Ошибка", "Пользователь с таким email не найден!")
            return

        login_attempts = self.db.get_login_attempts(email)
        
        if login_attempts >= self.max_attempts:
            QMessageBox.warning(self, "Превышено количество попыток", 
                              "Вы превысили количество попыток входа. Требуется проверка безопасности.")
            self.show_captcha(email)
            return

        user = self.db.check_user(email, password)
        
        if user:
            self.db.update_login_attempts(email, True)
            QMessageBox.information(self, "Успех", f"Вход выполнен успешно, {user[1]}!")
            self.open_pong_game(user[1])
        else:
            self.db.update_login_attempts(email, False)
            remaining_attempts = self.max_attempts - (login_attempts + 1)
            
            if remaining_attempts > 0:
                QMessageBox.warning(self, "Ошибка входа", 
                                  f"Неверный пароль. Осталось попыток: {remaining_attempts}")
            else:
                QMessageBox.warning(self, "Превышено количество попыток", 
                                  "Вы превысили количество попыток входа. Требуется проверка безопасности.")
                self.show_captcha(email)

    def show_captcha(self, email):
        image_paths = ['1.png', '2.png', '3.png', '4.png']
        
        self.captcha_window = CaptchaWidget(image_paths)
        self.captcha_window.on_success = lambda: self.on_captcha_success(email)
        self.captcha_window.show()

    def on_captcha_success(self, email):
        self.db.update_login_attempts(email, True)
        QMessageBox.information(self, "Доступ восстановлен", 
                              "Проверка пройдена успешно! Вы можете продолжить попытки входа.")

    def handle_register(self):
        name = self.reg_name.text().strip()
        email = self.reg_email.text().strip()
        password = self.reg_password.text().strip()

        if not name or not email or not password:
            QMessageBox.warning(self, "Ошибка", "Заполните все поля!")
            return

        if len(password) < 6:
            QMessageBox.warning(self, "Ошибка", "Пароль должен содержать минимум 6 символов!")
            return

        if not self.is_valid_email(email):
            QMessageBox.warning(self, "Ошибка", "Введите корректный email адрес!")
            return

        if self.db.register_user(name, email, password):
            QMessageBox.information(self, "Успех", "Регистрация выполнена успешно!")
            self.reg_name.clear()
            self.reg_email.clear()
            self.reg_password.clear()
            self.tabs.setCurrentIndex(0)
        else:
            QMessageBox.warning(self, "Ошибка", "Пользователь с таким email уже существует!")

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
        self.ball_speed_x = 5
        self.ball_speed_y = 5
        self.player1_y = 250
        self.player2_y = 250
        self.ball_x = 390
        self.ball_y = 290
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
        key = event.key()
        self.keys_pressed[key] = True

        if key == Qt.Key_R:
            self.restart_game()

    def keyReleaseEvent(self, event):
        key = event.key()
        self.keys_pressed[key] = False

    def update_game(self):
        if self.keys_pressed.get(Qt.Key_W, False):
            self.player1_y = max(0, self.player1_y - self.paddle_speed)
        if self.keys_pressed.get(Qt.Key_S, False):
            self.player1_y = min(self.height() - self.paddle_height, self.player1_y + self.paddle_speed)
        if self.keys_pressed.get(Qt.Key_Up, False):
            self.player2_y = max(0, self.player2_y - self.paddle_speed)
        if self.keys_pressed.get(Qt.Key_Down, False):
            self.player2_y = min(self.height() - self.paddle_height, self.player2_y + self.paddle_speed)

        self.ball_x += self.ball_speed_x
        self.ball_y += self.ball_speed_y

        if self.ball_y <= 0 or self.ball_y + self.ball_size >= self.height():
            self.ball_speed_y *= -1

        if (self.ball_x <= self.paddle_width and
                self.player1_y <= self.ball_y + self.ball_size and
                self.ball_y <= self.player1_y + self.paddle_height):
            self.ball_speed_x *= -1

        if (self.ball_x + self.ball_size >= self.width() - self.paddle_width and
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
            QMessageBox.information(self, "Игра окончена",
                                      f"Победитель: {winner}\nНажмите R для рестарта.")

        self.update()

    def reset_ball(self):
        self.ball_x = self.width() // 2 - self.ball_size // 2
        self.ball_y = self.height() // 2 - self.ball_size // 2
        self.ball_speed_x = 5 if random.choice([True, False]) else -5
        self.ball_speed_y = 5 if random.choice([True, False]) else -5

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0))

        painter.setBrush(QColor(255, 255, 255))
        painter.drawRect(0, self.player1_y, self.paddle_width, self.paddle_height)
        painter.drawRect(self.width() - self.paddle_width, self.player2_y, self.paddle_width, self.paddle_height)

        painter.drawEllipse(self.ball_x, self.ball_y, self.ball_size, self.ball_size)

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
        self.player1_y = self.height() // 2 - self.paddle_height // 2
        self.player2_y = self.height() // 2 - self.paddle_height // 2
        self.reset_ball()
        self.timer.start()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AuthWindow()
    window.show()
    sys.exit(app.exec())

    
