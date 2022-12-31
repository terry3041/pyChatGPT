from selenium.webdriver.support import expected_conditions as EC
from selenium.common import exceptions as SeleniumExceptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By

import undetected_chromedriver as uc
from markdownify import markdownify
import platform
import logging
import json
import re
import os


class ChatGPT:
    __cf_challenge = (By.ID, 'challenge-form')
    __textbox = (By.TAG_NAME, 'textarea')
    __streaming = (By.CLASS_NAME, 'result-streaming')
    __big_response = (By.XPATH, '//div[@class="flex-1 overflow-hidden"]//div[p]')
    __small_response = (
        By.XPATH,
        '//div[starts-with(@class, "markdown prose w-full break-words")]',
    )
    __alert = (By.XPATH, '//div[@role="alert"]')
    __intro = (By.ID, 'headlessui-portal-root')
    __login_btn = (By.XPATH, '//button[text()="Log in"]')

    def __init__(
        self,
        session_token: str = None,
        conversation_id: str = '',
        auth_type: str = None,
        email: str = None,
        password: str = None,
        cookies_path: str = '',
        captcha_solver: str = 'pypasser',
        solver_apikey: str = '',
        proxy: str = None,
        moderation: bool = True,
        verbose: bool = False,
    ):
        self.__init_logger(verbose)

        self.__session_token = session_token
        self.__conversation_id = conversation_id
        self.__auth_type = auth_type
        self.__email = email
        self.__password = password
        self.__cookies_path = cookies_path
        self.__captcha_solver = captcha_solver
        self.__solver_apikey = solver_apikey
        self.__proxy = proxy
        self.__moderation = moderation

        if not self.__session_token and (
            not self.__email or not self.__password or not self.__auth_type
        ):
            raise ValueError(
                'Please provide either a session token or login credentials'
            )
        if self.__auth_type not in [None, 'google', 'windowslive', 'openai']:
            raise ValueError('Invalid authentication type')
        if self.__captcha_solver == '2captcha' and not self.__solver_apikey:
            raise ValueError('Please provide a 2captcha apikey')
        if self.__proxy and not re.findall(
            r'(https?|socks(4|5)?):\/\/.+:\d{1,5}', self.__proxy
        ):
            raise ValueError('Invalid proxy format')
        if self.__auth_type == 'openai' and self.__captcha_solver == 'pypasser':
            try:
                import ffmpeg_downloader as ffdl
            except ModuleNotFoundError:
                raise ValueError(
                    'Please install ffmpeg_downloader, PyPasser, and pocketsphinx by running `pip install ffmpeg_downloader PyPasser pocketsphinx`'
                )

            ffmpeg_installed = bool(ffdl.ffmpeg_version)
            self.logger.debug(f'ffmpeg installed: {ffmpeg_installed}')
            if not ffmpeg_installed:
                import subprocess as sp

                sp.run(['ffdl', 'install'])
            os.environ['PATH'] += os.pathsep + ffdl.ffmpeg_dir

        self.__init_browser()

    def __del__(self):
        if hasattr(self, 'driver'):
            self.logger.debug('Closing browser...')
            self.driver.quit()
        if hasattr(self, 'display'):
            self.logger.debug('Closing display...')
            self.display.stop()

    def __init_logger(self, verbose: bool) -> None:
        self.logger = logging.getLogger('pyChatGPT')
        self.logger.setLevel(logging.DEBUG)
        if verbose:
            formatter = logging.Formatter('[%(funcName)s] %(message)s')
            stream_handler = logging.StreamHandler()
            stream_handler.setFormatter(formatter)
            self.logger.addHandler(stream_handler)

    def __init_browser(self) -> None:
        if platform.system() == 'Linux' and 'DISPLAY' not in os.environ:
            self.logger.debug('Starting virtual display...')
            try:
                from pyvirtualdisplay import Display

                self.display = Display()
            except ModuleNotFoundError:
                raise ValueError(
                    'Please install PyVirtualDisplay to start a virtual display by running `pip install PyVirtualDisplay`'
                )
            except FileNotFoundError as e:
                if 'No such file or directory: \'Xvfb\'' in str(e):
                    raise ValueError(
                        'Please install Xvfb to start a virtual display by running `sudo apt install xvfb`'
                    )
                raise e
            self.display.start()

        self.logger.debug('Initializing browser...')
        options = uc.ChromeOptions()
        options.add_argument('--window-size=1024,768')
        if self.__proxy:
            options.add_argument(f'--proxy-server={self.__proxy}')
        try:
            self.driver = uc.Chrome(options=options)
        except TypeError as e:
            if str(e) == 'expected str, bytes or os.PathLike object, not NoneType':
                raise ValueError('Chrome installation not found')
            raise e

        if self.__cookies_path and os.path.exists(self.__cookies_path):
            self.logger.debug('Restoring cookies...')
            try:
                with open(self.__cookies_path, 'r', encoding='utf-8') as f:
                    cookies = json.load(f)
                for cookie in cookies:
                    if cookie['name'] == '__Secure-next-auth.session-token':
                        self.__session_token = cookie['value']
            except json.decoder.JSONDecodeError:
                self.logger.debug(f'Invalid cookies file: {self.__cookies_path}')

        if self.__session_token:
            self.logger.debug('Restoring session_token...')
            self.driver.execute_cdp_cmd(
                'Network.setCookie',
                {
                    'domain': 'chat.openai.com',
                    'path': '/',
                    'name': '__Secure-next-auth.session-token',
                    'value': self.__session_token,
                    'httpOnly': True,
                    'secure': True,
                },
            )

        if not self.__moderation:
            self.logger.debug('Blocking moderation...')
            self.driver.execute_cdp_cmd(
                'Network.setBlockedURLs',
                {'urls': ['https://chat.openai.com/backend-api/moderations']},
            )

        self.logger.debug('Ensuring Cloudflare cookies...')
        self.__ensure_cf()

        self.logger.debug('Opening chat page...')
        self.driver.get('https://chat.openai.com/chat/' + self.__conversation_id)
        self.__check_blocking_elements()

    def __ensure_cf(self, retry: int = 3) -> None:
        self.logger.debug('Opening new tab...')
        original_window = self.driver.current_window_handle
        self.driver.switch_to.new_window('tab')

        self.logger.debug('Getting Cloudflare challenge...')
        self.driver.get('https://chat.openai.com/api/auth/session')
        try:
            WebDriverWait(self.driver, 15).until_not(
                EC.presence_of_element_located(self.__cf_challenge)
            )
        except SeleniumExceptions.TimeoutException:
            self.logger.debug(f'Cloudflare challenge failed, retrying {retry}...')
            self.driver.save_screenshot(f'cf_failed_{retry}.png')
            if retry > 0:
                self.logger.debug('Closing tab...')
                self.driver.close()
                self.driver.switch_to.window(original_window)
                return self.__ensure_cf(retry - 1)
            raise ValueError('Cloudflare challenge failed')
        self.logger.debug('Cloudflare challenge passed')

        self.logger.debug('Validating authorization...')
        response = self.driver.page_source
        if response[0] != '{':
            response = self.driver.find_element(By.TAG_NAME, 'pre').text
        response = json.loads(response)
        if (not response) or (
            'error' in response and response['error'] == 'RefreshAccessTokenError'
        ):
            self.logger.debug('Authorization is invalid')
            if not self.__auth_type:
                raise ValueError('Invalid session token')
            self.__login()
        self.logger.debug('Authorization is valid')

        self.logger.debug('Closing tab...')
        self.driver.close()
        self.driver.switch_to.window(original_window)

    def __check_capacity(self, target_url: str):
        while True:
            try:
                self.logger.debug('Checking if ChatGPT is at capacity...')
                WebDriverWait(self.driver, 3).until(
                    EC.presence_of_element_located(
                        (By.XPATH, '//div[text()="ChatGPT is at capacity right now"]')
                    )
                )
                self.logger.debug('ChatGPT is at capacity, retrying...')
                self.driver.get(target_url)
            except SeleniumExceptions.TimeoutException:
                self.logger.debug('ChatGPT is not at capacity')
                break

    def __login(self) -> None:
        self.logger.debug('Opening new tab...')
        original_window = self.driver.current_window_handle
        self.driver.switch_to.new_window('tab')

        self.logger.debug('Opening login page...')
        self.driver.get('https://chat.openai.com/auth/login')
        self.__check_capacity('https://chat.openai.com/auth/login')

        self.logger.debug('Clicking login button...')
        WebDriverWait(self.driver, 5).until(
            EC.element_to_be_clickable(self.__login_btn)
        ).click()

        WebDriverWait(self.driver, 5).until(
            EC.presence_of_element_located((By.XPATH, '//h1[text()="Welcome back"]'))
        )

        from . import Auth0

        Auth0.login(self)

        self.logger.debug('Checking if login was successful')
        try:
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, '//h1[text()="ChatGPT"]'))
            )
            if self.__cookies_path:
                self.logger.debug('Saving cookies...')
                with open(self.__cookies_path, 'w', encoding='utf-8') as f:
                    json.dump(
                        [
                            i
                            for i in self.driver.get_cookies()
                            if i['name'] == '__Secure-next-auth.session-token'
                        ],
                        f,
                    )
        except SeleniumExceptions.TimeoutException as e:
            self.driver.save_screenshot('login_failed.png')
            raise e

        self.logger.debug('Closing tab...')
        self.driver.close()
        self.driver.switch_to.window(original_window)

    def __check_blocking_elements(self) -> None:
        self.logger.debug('Looking for blocking elements...')
        try:
            intro = WebDriverWait(self.driver, 3).until(
                EC.presence_of_element_located(self.__intro)
            )
            self.logger.debug('Dismissing intro...')
            self.driver.execute_script('arguments[0].remove()', intro)
        except SeleniumExceptions.TimeoutException:
            pass

        alerts = self.driver.find_elements(*self.__alert)
        if alerts:
            self.logger.debug('Dismissing alert...')
            self.driver.execute_script('arguments[0].remove()', alerts[0])

    def send_message(self, message: str) -> dict:
        self.logger.debug('Ensuring Cloudflare cookies...')
        self.__ensure_cf()

        self.logger.debug('Sending message...')
        textbox = WebDriverWait(self.driver, 5).until(
            EC.element_to_be_clickable(self.__textbox)
        )
        textbox.click()
        self.driver.execute_script(
            '''
        var element = arguments[0], txt = arguments[1];
        element.value += txt;
        element.dispatchEvent(new Event("change"));
        ''',
            textbox,
            message,
        )
        textbox.send_keys(Keys.ENTER)

        self.logger.debug('Waiting for completion...')
        WebDriverWait(self.driver, 120).until_not(
            EC.presence_of_element_located(self.__streaming)
        )

        self.logger.debug('Getting response...')
        responses = self.driver.find_elements(*self.__big_response)
        if responses:
            response = responses[-1]
            if 'text-red' in response.get_attribute('class'):
                self.logger.debug('Response is an error')
                raise ValueError(response.text)
        response = self.driver.find_elements(*self.__small_response)[-1]

        content = markdownify(response.get_attribute('innerHTML')).replace(
            'Copy code`', '`'
        )
        return {'message': content, 'conversation_id': '', 'parent_id': ''}

    def refresh_chat_page(self) -> None:
        chat_url = 'https://chat.openai.com/chat'
        if not self.driver.current_url.startswith(chat_url):
            return self.__verbose_print(f'[refresh] current_url is not {chat_url}')

        self.driver.get(chat_url)
        self.__check_capacity(chat_url)
        self.__check_blocking_elements()
