# -*- coding: utf-8 -*-
import json, sqlite3, os
from configparser import ConfigParser
from time import sleep

from selenium import webdriver
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager

MAIN_URL = "https://www.facebook.com/"
MARKETPLACE_URL = "https://www.facebook.com/marketplace/create/item"

class App:
    def __init__(self, email="", password="", language="en", path="C:/ImagenesFacebook", time_to_sleep="0.7", browser="Chrome"):
        self.email = email
        self.password = password
        self.path = path  # Ruta principal donde están las carpetas de imágenes
        self.browser = browser
        self.language = language
        self.marketplace_options = None
        self.posts = None
        self.time_to_sleep = float(time_to_sleep)
        self.emojis_available = False
        with open(self.resource_path('marketplace_options.json'), encoding='utf-8') as f:
            self.marketplace_options = json.load(f)
            self.marketplace_options = self.marketplace_options[self.language]
        # To remove the pop up notification window
        if browser == "Firefox":
            self.emojis_available = True
            options = FirefoxOptions()
            options.set_preference("dom.webnotifications.enabled", False)
            self.driver = webdriver.Firefox(service=FirefoxService(GeckoDriverManager().install()), options=options)
        else:
            self.emojis_available = False
            options = ChromeOptions()
            options.add_argument("--disable-notifications")
            self.driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)

        self.driver.maximize_window()
        self.main_url = MAIN_URL
        self.marketplace_url = MARKETPLACE_URL
        self.driver.get(self.main_url)
        self.log_in()
        self.posts = self.fetch_all_posts()
        for post in self.posts:
            self.move_from_home_to_marketplace_create_item()
            self.create_post(post)
        sleep(2)
        self.driver.quit()

    def log_in(self):
        email_input = WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.ID, "email")))
        email_input.send_keys(self.email)
        password_input = WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.ID, "pass")))
        password_input.send_keys(self.password)
        login_button = WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.XPATH, "//*[@type='submit']")))
        login_button.click()

    def move_from_home_to_marketplace_create_item(self):
        WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//a[@href="/"]')))
        self.driver.get(self.marketplace_url)

    # Función modificada para cargar imágenes
    def add_photos_to_post(self, post_folder):
        # Definir la ruta principal donde se almacenan las imágenes
        image_base_path = "C:/ImagenesFacebook"  # Ruta principal de las imágenes
        
        # Combinamos la ruta principal con la carpeta obtenida de la base de datos
        image_folder_path = os.path.join(image_base_path, post_folder.strip("\\"))  # Asegurarse de que no haya un backslash
    
        # Verificar si la carpeta existe
        if not os.path.exists(image_folder_path):
            print(f"La carpeta {image_folder_path} no existe.")
            return

        # Obtenemos todas las imágenes en la carpeta con extensiones .jpg o .png
        image_paths = [os.path.join(image_folder_path, img) for img in os.listdir(image_folder_path) if img.endswith(('.jpg', '.png'))]

        # Si no se encuentran imágenes, detener el proceso
        if not image_paths:
            print(f"No se encontraron imágenes en el directorio: {image_folder_path}")
            return

        # Unir las rutas de las imágenes con un salto de línea para cargarlas todas
        images_to_upload = "\n".join(image_paths)

        # Localizar el input para subir las fotos
        upload_input = WebDriverWait(self.driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//input[@type='file']"))
        )

        # Enviar las rutas de las imágenes al input de tipo 'file'
        upload_input.send_keys(images_to_upload)

        # Esperar un par de segundos para que las imágenes se carguen
        sleep(self.time_to_sleep)

    def resource_path(self, relative_path):
        try:
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)

    def add_text_to_post(self, title, price, description, label):
        title_input = WebDriverWait(self.driver, 5).until(
            EC.presence_of_element_located((By.XPATH, "//input[contains(@class, 'x1i10hfl') and @type='text']"))
        )
        title_input.send_keys(title)
        
        # Localizar el input del precio
        price_input = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//span[contains(text(),'Precio')]/following::input[@type='text'][1]"))
        )
        price_input.send_keys(price)

        # Continuar con la descripción
        description_input = WebDriverWait(self.driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//span[contains(text(),'Descripción')]/following::textarea[1]"))
        )
        description_input.send_keys(description.replace("\r\n", "\n"))
        
        if label:
            label_input = WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.XPATH, "//label[@aria-label='" + self.marketplace_options["labels"]["Product Labels"] + "']/div/div[2]/div/textarea")))
            if not label.endswith(","):
                label += ","
            label_input.send_keys(label)

    def fetch_all_posts(self):
        posts = None
        try:
            sqliteConnection = sqlite3.connect('articles.db')
            cursor = sqliteConnection.cursor()
            sqlite_select_query = """SELECT * from item"""
            cursor.execute(sqlite_select_query)
            posts = cursor.fetchall()
            cursor.close()
        except sqlite3.Error as error:
            print("Failed to read data from sqlite table", error)
        finally:
            if sqliteConnection:
                sqliteConnection.close()
        return posts

    def clean_characters_bmp(self, text):
        return ''.join(c for c in text if ord(c) <= 0xFFFF).strip()

    def create_post(self, post):
        self.add_photos_to_post(post[8])  # Asumiendo que post[8] tiene el nombre de la carpeta de imágenes

        # Esperar que el dropdown de categoría esté disponible y hacer clic en él
        category_dropdown = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Categoría')]/following::div[1]"))
        )
        category_dropdown.click()  # Abre el menú desplegable
        sleep(self.time_to_sleep)  # Espera para que el menú se despliegue

        try:
            # Esperar y seleccionar la opción de categoría desde la base de datos (post[3] contiene la categoría)
            category_option = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, f"//span[contains(text(), '{post[3]}')]"))
            )
            category_option.click()  # Haz clic en la opción de categoría
            sleep(self.time_to_sleep)  # Espera después de seleccionar la categoría
        except Exception as e:
            print(f"Error al seleccionar la categoría: {e}")
            return  # Salir de la función si no se encuentra la categoría

        # Ahora que la categoría está seleccionada, llenar el resto de los campos
        self.add_text_to_post(post[1], post[2], post[5], post[6])  # Ajusta los índices según tu base de datos

        # Continuar con la selección del estado
        state_input = WebDriverWait(self.driver, 5).until(
            EC.presence_of_element_located((By.XPATH, "//label[@aria-label='" + self.marketplace_options["labels"]["State"] + "']"))
        )
        state_input.click()
        sleep(self.time_to_sleep)

        state_option = WebDriverWait(self.driver, 5).until(
            EC.presence_of_element_located((By.XPATH, '//div[@role="listbox"]/div/div/div/div/div[1]/div/div[' + self.get_element_position("states", post[4]) + ']'))
        )
        state_option.click()
        sleep(self.time_to_sleep)

        # Continuar con el flujo
        next_button = WebDriverWait(self.driver, 5).until(
            EC.presence_of_element_located((By.XPATH, "//div[@aria-label='" + self.marketplace_options["labels"]["Next Button"] + "']"))
        )
        next_button.click()
        self.post_in_more_places(post[9])  # post[9] tiene la información de grupos
        sleep(self.time_to_sleep)

        post_button = WebDriverWait(self.driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//div[@aria-label='" + self.marketplace_options["labels"]["Post"] + "']"))
        )
        post_button.click()
        sleep(self.time_to_sleep)




    def get_element_position(self, key, specific):
        if specific in self.marketplace_options[key]:
            return str(self.marketplace_options[key][specific])
        return -1

    def post_in_more_places(self, groups):
        groups_positions = groups.split(",")
        for group_position in groups_positions:
            group_input = WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.XPATH, "//div[@aria-label='" + self.marketplace_options["labels"]["Marketplace"] +  "']/div/div/div/div[4]/div/div/div/div/div/div/div[2]/div[" + group_position + "]")))
            group_input.click()
            sleep(self.time_to_sleep)

if __name__ == '__main__':
    config_object = ConfigParser()
    config_object.read("config.ini")
    facebook = config_object["FACEBOOK"]
    configuration = config_object["CONFIG"]
    app = App(facebook["email"], facebook["password"], configuration["language"], configuration["images_path"], configuration["time_to_sleep"], configuration["browser"])
