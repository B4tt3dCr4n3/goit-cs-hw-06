import http.server
import socketserver
import socket
import json
import os
from datetime import datetime
from pymongo import MongoClient
from concurrent.futures import ProcessPoolExecutor
from bson import json_util
import logging

# Налаштування системи логування
# Формат логу включає часову мітку для кращого відстеження подій
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def create_mongo_client():
    """
    Створює та повертає клієнт MongoDB.
    
    Ця функція інкапсулює створення з'єднання з MongoDB, що дозволяє
    легко змінювати параметри підключення в одному місці.
    Використовується URI для з'єднання, що відповідає налаштуванням у docker-compose.
    
    :return: Об'єкт MongoClient для взаємодії з базою даних
    """
    return MongoClient('mongodb://mongodb:27017/')

def read_file(filename):
    """
    Читає файл з теки front-init.
    
    Ця функція забезпечує безпечне читання файлів, обмежуючи доступ
    тільки до файлів у визначеній директорії (front-init).
    
    :param filename: Ім'я файлу для читання
    :return: Вміст файлу як bytes або None, якщо файл не знайдено
    """
    try:
        # Використання os.path.basename для безпеки, щоб запобігти доступу до файлів поза текою front-init
        safe_filename = os.path.basename(filename)
        with open(os.path.join('front-init', safe_filename), 'rb') as file:
            return file.read()
    except FileNotFoundError:
        logger.error(f"File not found: {filename}")
        return None

def parse_post_data(post_data):
    """
    Парсить дані POST-запиту.
    
    Ця функція розбирає рядок POST-запиту на словник параметрів.
    Вона також декодує URL-кодовані символи, такі як '+' у пробіли.
    
    :param post_data: Рядок з даними POST-запиту
    :return: Словник з розпарсеними даними
    """
    params = {}
    for param in post_data.split('&'):
        if '=' in param:
            key, value = param.split('=', 1)
            params[key] = value.replace('+', ' ')  # Заміна '+' на пробіл для декодування URL
    return params

class MyHandler(http.server.SimpleHTTPRequestHandler):
    """
    Клас для обробки HTTP запитів.
    
    Цей клас розширює SimpleHTTPRequestHandler, додаючи власну логіку
    для обробки GET та POST запитів. Кожен екземпляр має власне
    з'єднання з MongoDB для кращої ізоляції та керування ресурсами.
    """
    def __init__(self, *args, **kwargs):
        # Створення нового з'єднання з MongoDB для кожного екземпляра обробника
        # Це забезпечує ізоляцію з'єднань між різними запитами
        self.mongodb_client = create_mongo_client()
        self.db = self.mongodb_client['message_db']
        self.collection = self.db['messages']
        super().__init__(*args, **kwargs)

    def do_GET(self):
        """
        Обробляє GET-запити.
        
        Ця функція відповідає за надсилання статичних файлів клієнту.
        Вона обробляє спеціальні випадки для кореневого URL та сторінки повідомлень,
        а також визначає правильний Content-Type для різних типів файлів.
        """
        if self.path == '/':
            self.path = '/index.html'  # Перенаправлення кореневого URL на index.html
        elif self.path == '/message':
            self.path = '/message.html'  # Перенаправлення /message на message.html

        file_content = read_file(self.path.lstrip('/'))
        if file_content is None:
            self.send_error(404, "File not found")
            return

        # Відправка відповіді з відповідним Content-Type
        self.send_response(200)
        if self.path.endswith('.html'):
            self.send_header('Content-type', 'text/html')
        elif self.path.endswith('.css'):
            self.send_header('Content-type', 'text/css')
        elif self.path.endswith('.png'):
            self.send_header('Content-type', 'image/png')
        self.end_headers()
        self.wfile.write(file_content)

    def do_POST(self):
        """
        Обробляє POST-запити.
        
        Ця функція обробляє відправку повідомлень. Вона читає дані форми,
        логує отримані дані, відправляє їх на Socket-сервер та перенаправляє
        користувача назад на сторінку повідомлень.
        """
        if self.path == '/message' or self.path == '/message.html':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            params = parse_post_data(post_data)
            
            username = params.get('username', '')
            message = params.get('message', '')

            logger.info(f"Received POST data: username={username}, message={message}")

            # Відправка даних на Socket-сервер через TCP
            # Це дозволяє розділити логіку обробки HTTP та збереження даних
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect(('localhost', 5001))
                sock.sendall(json.dumps({'username': username, 'message': message}).encode())

            # Перенаправлення користувача назад на сторінку повідомлень
            self.send_response(303)
            self.send_header('Location', '/message.html')
            self.end_headers()

def run_http_server():
    """
    Запускає HTTP-сервер на порту 3000.
    
    Ця функція налаштовує та запускає HTTP-сервер, використовуючи
    MyHandler для обробки запитів. Сервер працює безкінечно,
    обробляючи вхідні з'єднання.
    """
    with socketserver.TCPServer(("", 3000), MyHandler) as httpd:
        logger.info("HTTP server running on port 3000")
        httpd.serve_forever()

def run_socket_server():
    """
    Запускає Socket-сервер на порту 5001.
    
    Ця функція створює TCP-сервер, який приймає з'єднання на порту 5001.
    Вона обробляє вхідні повідомлення, зберігає їх у MongoDB та логує події.
    Сервер працює в безкінечному циклі, постійно прослуховуючи нові з'єднання.
    """
    # Створюємо нове з'єднання з MongoDB для цього процесу
    mongodb_client = create_mongo_client()
    db = mongodb_client['message_db']
    collection = db['messages']

    # Створюємо сокет для прийому TCP-з'єднань
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        # Прив'язуємо сокет до всіх інтерфейсів на порту 5001
        sock.bind(('0.0.0.0', 5001))
        # Починаємо прослуховування вхідних з'єднань
        sock.listen()
        logger.info("Socket server running on port 5001")
        
        while True:
            try:
                # Приймаємо нове з'єднання
                conn, addr = sock.accept()
                logger.info(f"New connection from {addr}")
                with conn:
                    # Отримуємо дані від клієнта
                    data = conn.recv(1024)
                    if not data:
                        logger.warning(f"Empty data received from {addr}")
                        continue
                    
                    # Декодуємо отримані дані з JSON формату
                    message_dict = json.loads(data.decode())
                    # Отримуємо поточний час для збереження з повідомленням
                    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
                    
                    # Формуємо словник для вставки в MongoDB
                    insert_dict = {
                        "date": current_time,
                        "username": message_dict.get('username', 'Unknown'),
                        "message": message_dict.get('message', '')
                    }
                    
                    # Зберігаємо повідомлення в MongoDB
                    collection.insert_one(insert_dict)
                    # Логуємо успішне збереження повідомлення
                    logger.info(f"Received and saved message from {addr}: {json_util.dumps(insert_dict)}")
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON received from {addr}")
            except Exception as e:
                logger.error(f"Error processing connection from {addr}: {str(e)}")

if __name__ == "__main__":
    
    # Використовуємо ProcessPoolExecutor для паралельного запуску серверів
    with ProcessPoolExecutor(max_workers=2) as executor:
        # Запускаємо HTTP-сервер в окремому процесі
        executor.submit(run_http_server)
        
        # Запускаємо Socket-сервер в іншому окремому процесі
        executor.submit(run_socket_server)
