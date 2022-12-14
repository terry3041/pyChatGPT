from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.common import exceptions as SeleniumExceptions
import undetected_chromedriver as uc

from pyvirtualdisplay import Display
import markdownify
import platform
import time
import json
import os
import re


class ChatGPT:
    '''
    An unofficial Python wrapper for OpenAI's ChatGPT API
    '''

    def __init__(
        self,
        session_token: str = None,
        email: str = None,
        password: str = None,
        auth_type: str = None,
        proxy: str = None,
        verbose: bool = False,
    ) -> None:
        '''
        Initialize the ChatGPT class\n
        Either provide a session token or email and password\n
        Parameters:
        - session_token: (optional) Your session token in cookies named as `__Secure-next-auth.session-token` from https://chat.openai.com/chat
        - email: (optional) Your email
        - password: (optional) Your password
        - auth_type: The type of authentication to use. Can only be `google` at the moment
        - proxy: (optional) The proxy to use, in URL format (i.e. `https://ip:port`)
        - verbose: (optional) Whether to print debug messages
        '''
        self.verbose = verbose

        self.proxy = proxy
        if self.proxy and not re.findall(
            r'(https?|socks(4|5)?):\/\/.+:\d{1,5}', self.proxy
        ):
            raise ValueError('Invalid proxy format')

        self.__email = email
        self.__password = password
        self.__auth_type = auth_type
        if self.__auth_type not in [None, 'google', 'windowslive']:
            raise ValueError('Invalid authentication type')
        self.__session_token = session_token
        if not self.__session_token:
            if not self.__email or not self.__password or not self.__auth_type:
                raise ValueError(
                    'Please provide either a session token or login credentials'
                )

        self.__is_headless = (
            platform.system() == 'Linux' and 'DISPLAY' not in os.environ
        )
        self.__verbose_print('Platform:', platform.system())
        self.__verbose_print('Display:', 'DISPLAY' in os.environ)
        self.__verbose_print('Headless:', self.__is_headless)
        self.__init_browser()

    def __verbose_print(self, *args, **kwargs) -> None:
        '''
        Print if verbose is enabled
        '''
        if self.verbose:
            print(*args, **kwargs)

    def close(self) -> None:
        '''
        Close the browser and stop the virtual display (if any)
        '''
        if hasattr(self, 'driver'):
            self.driver.quit()
        if hasattr(self, 'display'):
            self.display.stop()

    def __init_browser(self) -> None:
        '''
        Initialize the browser
        '''
        # Detect if running on a headless server
        if self.__is_headless:
            try:
                self.display = Display()
            except FileNotFoundError as e:
                if 'No such file or directory: \'Xvfb\'' in str(e):
                    raise ValueError(
                        'Headless machine detected. Please install Xvfb to start a virtual display: sudo apt install xvfb'
                    )
                raise e
            self.__verbose_print('Starting virtual display')
            self.display.start()

        # Start the browser
        options = uc.ChromeOptions()
        options.add_argument('--window-size=800,600')
        if self.proxy:
            options.add_argument(f'--proxy-server={self.proxy}')
        try:
            self.__verbose_print('Starting browser')
            self.driver = uc.Chrome(options=options, enable_cdp_events=True)
        except TypeError as e:
            if str(e) == 'expected str, bytes or os.PathLike object, not NoneType':
                raise ValueError('Chrome installation not found')
            raise e

        # Restore session token
        if not self.__auth_type:
            self.__verbose_print('Restoring session token')
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

        # Ensure that the Cloudflare challenge is still valid
        self.__verbose_print('Ensuring Cloudflare challenge')
        self.__ensure_cf()

        # Open the chat page
        self.__verbose_print('Opening chat page')
        self.driver.get('https://chat.openai.com/chat')

        # Dismiss the ChatGPT intro
        self.__verbose_print('Dismissing intro')
        self.driver.execute_script(
            """
        var element = document.getElementById('headlessui-portal-root');
        if (element)
            element.parentNode.removeChild(element);
        """
        )

    def __login(self) -> None:
        '''
        Login to ChatGPT
        '''
        # Get the login page
        self.__verbose_print('Opening new tab')
        original_window = self.driver.current_window_handle
        self.driver.switch_to.new_window('tab')

        self.__verbose_print('Opening login page')
        self.driver.get('https://chat.openai.com/auth/login')
        while True:
            try:
                self.__verbose_print('Checking if ChatGPT is at capacity')
                WebDriverWait(self.driver, 3).until(
                    EC.presence_of_element_located(
                        (By.XPATH, '//div[text()="ChatGPT is at capacity right now"]')
                    )
                )
                self.__verbose_print('ChatGPT is at capacity, retrying')
                self.driver.get('https://chat.openai.com/auth/login')
            except SeleniumExceptions.TimeoutException:
                break

        # Click Log in button
        self.__verbose_print('Clicking Log in button')
        WebDriverWait(self.driver, 3).until(
            EC.presence_of_element_located(
                (By.XPATH, '//div[text()="Welcome to ChatGPT"]')
            )
        )
        self.driver.find_element(By.XPATH, '//button[text()="Log in"]').click()

        # click button with data-provider="google"
        self.__verbose_print('Clicking Google button')
        WebDriverWait(self.driver, 5).until(
            EC.presence_of_element_located((By.XPATH, '//h1[text()="Welcome back"]'))
        )
        self.driver.find_element(
            By.XPATH, f'//button[@data-provider="{self.__auth_type}"]'
        ).click()

        if self.__auth_type == 'google':
            # Enter email
            try:
                self.__verbose_print('Checking if Google remembers email')
                WebDriverWait(self.driver, 3).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, f'//div[@data-identifier="{self.__email}"]')
                    )
                )
                self.__verbose_print('Google remembers email')
                self.driver.find_element(
                    By.XPATH, f'//div[@data-identifier="{self.__email}"]'
                ).click()
            except SeleniumExceptions.TimeoutException:
                self.__verbose_print('Google does not remember email')
                self.__verbose_print('Entering email')
                WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, '//input[@type="email"]'))
                )
                self.driver.find_element(By.XPATH, '//input[@type="email"]').send_keys(
                    self.__email
                )
                self.__verbose_print('Clicking Next')
                self.driver.find_element(By.XPATH, '//*[@id="identifierNext"]').click()

                # Enter password
                self.__verbose_print('Entering password')
                WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, '//input[@type="password"]'))
                )
                self.driver.find_element(
                    By.XPATH, '//input[@type="password"]'
                ).send_keys(self.__password)
                self.__verbose_print('Clicking Next')
                self.driver.find_element(By.XPATH, '//*[@id="passwordNext"]').click()

            # wait verification code
            try:
                self.__verbose_print('Checking if verification code is required')
                WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.TAG_NAME, 'samp'))
                )
                self.__verbose_print('Verification code is required')
                prev_code = self.driver.find_elements(By.TAG_NAME, 'samp')[0].text
                print('Verification code:', prev_code)
                while True:
                    code = self.driver.find_elements(By.TAG_NAME, 'samp')
                    if not code:
                        break
                    if code[0].text != prev_code:
                        print('Verification code:', code[0].text)
                        prev_code = code[0].text
                    time.sleep(1)
            except SeleniumExceptions.TimeoutException:
                pass

        # Check if logged in correctly
        try:
            self.__verbose_print('Checking if login was successful')
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, '//h1[text()="ChatGPT"]'))
            )
        except SeleniumExceptions.TimeoutException:
            self.driver.save_screenshot('login_failed.png')
            raise ValueError('Login failed')

        # Close the tab
        self.__verbose_print('Closing tab')
        self.driver.close()
        self.driver.switch_to.window(original_window)

    def __ensure_cf(self, retry: int = 0) -> None:
        '''
        Ensure that the Cloudflare challenge is still valid\n
        Parameters:
        - retry: The number of times this function has been called recursively
        '''
        # Open a new tab
        self.__verbose_print('Opening new tab')
        original_window = self.driver.current_window_handle
        self.driver.switch_to.new_window('tab')

        # Get the Cloudflare challenge
        self.__verbose_print('Getting authorization')
        self.driver.get('https://chat.openai.com/api/auth/session')
        try:
            WebDriverWait(self.driver, 15).until_not(
                EC.presence_of_element_located((By.ID, 'challenge-form'))
            )
        except SeleniumExceptions.TimeoutException:
            self.driver.save_screenshot(f'cf_failed_{retry}.png')
            if retry <= 2:
                self.__verbose_print(
                    f'Cloudflare challenge failed, retrying {retry + 1}'
                )
                self.__verbose_print('Closing tab')
                self.driver.close()
                self.driver.switch_to.window(original_window)
                return self.__ensure_cf(retry + 1)
            else:
                resp_text = self.driver.page_source
                raise ValueError(f'Cloudflare challenge failed: {resp_text}')

        # Validate the authorization
        resp = self.driver.page_source
        if resp[0] != '{':  # its probably not a json
            resp = self.driver.find_element(By.TAG_NAME, 'pre').text
        data = json.loads(resp)
        if data and 'error' in data:
            self.__verbose_print(data['error'])
            if data['error'] == 'RefreshAccessTokenError':
                if not self.__auth_type:
                    raise ValueError('Session token expired')
                self.__login()
            else:
                raise ValueError(f'Authorization error: {data["error"]}')
        elif not data:
            self.__verbose_print('Authorization is empty')
            if not self.__auth_type:
                raise ValueError('Invalid session token')
            self.__login()
        self.__verbose_print('Authorization is valid')

        # Close the tab
        self.__verbose_print('Closing tab')
        self.driver.close()
        self.driver.switch_to.window(original_window)

    def send_message(self, message: str) -> dict:
        '''
        Send a message to the chatbot\n
        Parameters:
        - message: The message you want to send\n
        Returns a `dict` with the following keys:
        - message: The message the chatbot sent
        - conversation_id: The conversation ID
        - parent_id: The parent ID
        '''
        # Ensure that the Cloudflare challenge is still valid
        self.__verbose_print('Ensuring Cloudflare challenge')
        self.__ensure_cf()

        # Send the message
        self.__verbose_print('Sending message')
        WebDriverWait(self.driver, 5).until(
            EC.element_to_be_clickable((By.TAG_NAME, 'textarea'))
        )
        textbox = self.driver.find_element(By.TAG_NAME, 'textarea')

        # Sending emoji (from https://stackoverflow.com/a/61043442)
        textbox.click()
        self.driver.execute_script(
            """
        var element = arguments[0], txt = arguments[1];
        element.value += txt;
        element.dispatchEvent(new Event('change'));
        """,
            textbox,
            message,
        )
        textbox.send_keys(Keys.ENTER)

        # Wait for the response to be ready
        self.__verbose_print('Waiting for completion')
        WebDriverWait(self.driver, 90).until_not(
            EC.presence_of_element_located((By.CLASS_NAME, 'result-streaming'))
        )

        # Get the response element
        self.__verbose_print('Finding response element')
        response = self.driver.find_elements(
            By.XPATH, "//div[starts-with(@class, 'request-:')]"
        )[-1]

        # Check if the response is an error
        self.__verbose_print('Checking if response is an error')
        if 'text-red' in response.get_attribute('class'):
            self.__verbose_print('Response is an error')
            raise ValueError(response.text)
        self.__verbose_print('Response is not an error')

        # Return the response
        return {
            'message': markdownify.markdownify(response.get_attribute('innerHTML')),
            'conversation_id': '',
            'parent_id': '',
        }

    def reset_conversation(self) -> None:
        '''
        Reset the conversation
        '''
        self.__verbose_print('Resetting conversation')
        self.driver.find_element(By.LINK_TEXT, 'New Thread').click()
