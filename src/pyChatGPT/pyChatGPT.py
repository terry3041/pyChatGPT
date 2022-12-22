from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
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
        moderation: bool = True,
        verbose: bool = False,
        window_size: tuple = (800, 600),
        twocaptcha_apikey: str = '',
        openai_auth_semi_automatic: bool = True,
        login_cookies_path: str = '',
    ) -> None:
        '''
        Initialize the ChatGPT class\n
        Either provide a session token or email and password\n
        Parameters:
        - session_token: (optional) Your session token in cookies named as `__Secure-next-auth.session-token` from https://chat.openai.com/chat
        - email: (optional) Your email
        - password: (optional) Your password
        - auth_type: The type of authentication to use. Can only be `google` or `openai` at the moment
        - proxy: (optional) The proxy to use, in URL format (i.e. `https://ip:port`)
        - moderation: (optional) Whether to enable message moderation. Default is `True`
        - verbose: (optional) Whether to print debug messages
        - window_size: (optional) window_size for web driver
        - twocaptcha_apikey: (optional) 2captcha apikey, for solving reCAPTCHA. Use the apikey only for auth_type='openai'
        - openai_auth_semi_automatic: (optional) allow solving reCAPTCHA by user when 2captcha method have failed.
        - login_cookies_path: cookies path to be saved or loaded.
        '''
        self.__verbose = verbose

        self.__proxy = proxy
        if self.__proxy and not re.findall(
            r'(https?|socks(4|5)?):\/\/.+:\d{1,5}', self.__proxy
        ):
            raise ValueError('Invalid proxy format')

        self.__email = email
        self.__password = password
        self.__auth_type = auth_type
        self.__window_size = window_size
        self.__moderation = moderation
        self.__twocaptcha_apikey = twocaptcha_apikey
        self.__openai_auth_semi_automatic = openai_auth_semi_automatic
        self.__login_cookies_path = login_cookies_path
        if self.__auth_type not in [None, 'google', 'windowslive', 'openai']:
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
        self.__verbose_print('[0] Platform:', platform.system())
        self.__verbose_print('[0] Display:', 'DISPLAY' in os.environ)
        self.__verbose_print('[0] Headless:', self.__is_headless)
        self.__init_browser()

    def __del__(self):
        '''
        Close the browser and virtual display (if any)
        '''
        if hasattr(self, 'driver'):
            self.driver.quit()
        if hasattr(self, 'display'):
            self.display.stop()

    def __verbose_print(self, *args, **kwargs) -> None:
        '''
        Print if verbose is enabled
        '''
        if self.__verbose:
            print(*args, **kwargs)

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
            self.__verbose_print('[init] Starting virtual display')
            self.display.start()

        # Start the browser
        options = uc.ChromeOptions()
        options.add_argument('--window-size=%s,%s' % self.__window_size)
        if self.__proxy:
            options.add_argument(f'--proxy-server={self.__proxy}')
        try:
            self.__verbose_print('[init] Starting browser')
            self.driver = uc.Chrome(options=options, enable_cdp_events=True)
        except TypeError as e:
            if str(e) == 'expected str, bytes or os.PathLike object, not NoneType':
                raise ValueError('Chrome installation not found')
            raise e

        # Restore session token
        if not self.__auth_type:
            self.__verbose_print('[init] Restoring session token')
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

        # Block moderation
        if not self.__moderation:
            self.__verbose_print('[init] Blocking moderation')
            self.driver.execute_cdp_cmd(
                'Network.setBlockedURLs',
                {'urls': ['https://chat.openai.com/backend-api/moderations']},
            )

        # Ensure that the Cloudflare cookies is still valid
        self.__verbose_print('[init] Ensuring Cloudflare cookies')
        self.__ensure_cf()

        # Open the chat page
        self.__verbose_print('[init] Opening chat page')
        self.driver.get('https://chat.openai.com/chat')

        # Dismiss the ChatGPT intro
        self.__verbose_print('[init] Check if there is intro')
        try:
            WebDriverWait(self.driver, 3).until(
                EC.presence_of_element_located((By.ID, 'headlessui-portal-root'))
            )
            self.__verbose_print('[init] Dismissing intro')
            self.driver.execute_script(
                """
            var element = document.getElementById('headlessui-portal-root');
            if (element)
                element.parentNode.removeChild(element);
            """
            )
        except SeleniumExceptions.TimeoutException:
            self.__verbose_print('[init] Did not found one')
            pass

        # Check if there is an alert
        self.__verbose_print('[init] Check if there is alert')
        alerts = self.__is_high_demand()
        if alerts:
            self.__verbose_print('[init] Dismissing alert')
            self.driver.execute_script(
                """
            var element = document.querySelector('div[role="alert"]');
            if (element)
                element.parentNode.removeChild(element);
            """
            )

    def __is_high_demand(self) -> list or None:
        '''
        Check if there is an alert and close it
        '''
        alerts = self.driver.find_elements(By.XPATH, '//div[@role="alert"]')
        return alerts

    def __save_chat_gpt_cookies(self, path):
        with open(path, 'w', encoding='utf-8') as f:
            cookies_list = self.driver.execute_cdp_cmd(
                "Network.getCookies", {"urls": ["https://chat.openai.com/chat"]}
            )["cookies"]
            json.dump(cookies_list, f, indent=2, ensure_ascii=False)

    def __load_chat_gpt_cookies(self, path):
        with open(path, 'r', encoding='utf-8') as f:
            cookies_list = json.load(f)
        for cookie in cookies_list:
            if cookie["name"] == "__Secure-next-auth.session-token":
                self.driver.execute_cdp_cmd('Network.setCookie', cookie)

    def __login(self) -> None:
        '''
        Login to ChatGPT
        '''
        # Get the login page
        self.__verbose_print('[login] Opening new tab')
        original_window = self.driver.current_window_handle
        self.driver.switch_to.new_window('tab')

        if self.__login_cookies_path and os.path.exists(self.__login_cookies_path):
            # load cookie json
            try:
                self.__verbose_print('[login] loading cookies')
                self.__load_chat_gpt_cookies(self.__login_cookies_path)
                self.driver.get('https://chat.openai.com/chat')
                self.__verbose_print('[login] Checking if login was successful')
                WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, '//h1[text()="ChatGPT"]'))
                )
                self.__verbose_print('[login] Login with cookies successfully.')
                self.driver.close()
                self.driver.switch_to.window(original_window)
                return
            except json.decoder.JSONDecodeError:
                self.__verbose_print(
                    '[login] Cookies json is not valid, please check',
                    self.__login_cookies_path,
                )
            except SeleniumExceptions.TimeoutException:
                self.__verbose_print(
                    '[login] Login with cookies failed, trying login next.'
                )

        self.__verbose_print('[login] Opening login page')
        self.driver.get('https://chat.openai.com/auth/login')
        while True:
            try:
                self.__verbose_print('[login] Checking if ChatGPT is at capacity')
                WebDriverWait(self.driver, 3).until(
                    EC.presence_of_element_located(
                        (By.XPATH, '//div[text()="ChatGPT is at capacity right now"]')
                    )
                )
                self.__verbose_print('[login] ChatGPT is at capacity, retrying')
                self.driver.get('https://chat.openai.com/auth/login')
            except SeleniumExceptions.TimeoutException:
                self.__verbose_print('[login] ChatGPT is not at capacity')
                break

        # Click Log in button
        self.__verbose_print('[login] Clicking Log in button')
        WebDriverWait(self.driver, 5).until(
            EC.presence_of_element_located(
                (By.XPATH, '//div[text()="Welcome to ChatGPT"]')
            )
        )
        self.driver.find_element(By.XPATH, '//button[text()="Log in"]').click()

        WebDriverWait(self.driver, 5).until(
            EC.presence_of_element_located((By.XPATH, '//h1[text()="Welcome back"]'))
        )

        if self.__auth_type == 'google':
            # click button with data-provider="google"
            self.__verbose_print('[login] Clicking Google button')
            self.driver.find_element(
                By.XPATH, f'//button[@data-provider="{self.__auth_type}"]'
            ).click()
            # Enter email
            self.__google_login()
        elif self.__auth_type == 'openai':
            self.__openai_login()

        # Check if logged in correctly
        try:
            self.__verbose_print('[login] Checking if login was successful')
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, '//h1[text()="ChatGPT"]'))
            )
        except SeleniumExceptions.TimeoutException as e:
            self.driver.save_screenshot('login_failed.png')
            raise e
            # raise ValueError('Login failed')
        if self.__login_cookies_path:
            self.__save_chat_gpt_cookies(self.__login_cookies_path)
        # Close the tab
        self.__verbose_print('[login] Closing tab')
        self.driver.close()
        self.driver.switch_to.window(original_window)

    def __google_login(self):
        try:
            self.__verbose_print('[login] Checking if Google remembers email')
            WebDriverWait(self.driver, 3).until(
                EC.element_to_be_clickable(
                    (By.XPATH, f'//div[@data-identifier="{self.__email}"]')
                )
            )
            self.__verbose_print('[login] Google remembers email')
            self.driver.find_element(
                By.XPATH, f'//div[@data-identifier="{self.__email}"]'
            ).click()
        except SeleniumExceptions.TimeoutException:
            self.__verbose_print('[login] Google does not remember email')
            self.__verbose_print('[login] Entering email')
            WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, '//input[@type="email"]'))
            )
            self.driver.find_element(By.XPATH, '//input[@type="email"]').send_keys(
                self.__email
            )
            self.__verbose_print('[login] Clicking Next')
            self.driver.find_element(By.XPATH, '//*[@id="identifierNext"]').click()

            # Enter password
            self.__verbose_print('[login] Entering password')
            WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, '//input[@type="password"]'))
            )
            self.driver.find_element(By.XPATH, '//input[@type="password"]').send_keys(
                self.__password
            )
            self.__verbose_print('[login] Clicking Next')
            self.driver.find_element(By.XPATH, '//*[@id="passwordNext"]').click()
        # wait verification code
        try:
            self.__verbose_print('[login] Check if verification code is required')
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.TAG_NAME, 'samp'))
            )
            self.__verbose_print('[login] code is required')
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
            self.__verbose_print('[login] code is not required')
            pass

    def __have_recaptcha_value(self):
        try:
            self.driver.switch_to.default_content()
            recaptcha_result = self.driver.find_element(
                By.XPATH, '//input[@name="captcha" and @type="hidden"]'
            )
            return recaptcha_result.get_attribute('value') != ''
        except SeleniumExceptions.NoSuchElementException:
            return False

    def __have_image_recaptcha(self):
        self.driver.switch_to.default_content()
        try:
            WebDriverWait(self.driver, 3).until(
                EC.frame_to_be_available_and_switch_to_it(
                    (
                        By.CSS_SELECTOR,
                        "iframe[title='recaptcha challenge expires in two minutes']",
                    )
                )
            )
        except SeleniumExceptions.TimeoutException:
            return False

    def __2captcha_solve(self, enterprise=1, retry=8):
        self.driver.switch_to.default_content()
        import twocaptcha

        self.__verbose_print('[reCAPTCHA] trying twocaptcha max retry =', retry)
        solver = twocaptcha.TwoCaptcha(self.__twocaptcha_apikey, pollingInterval=5)
        # get result using 2Captcha
        el = self.driver.find_element(
            By.XPATH, '//div[@data-recaptcha-provider="recaptcha_enterprise"]'
        )
        sitekey = el.get_attribute('data-recaptcha-sitekey')
        result = None
        for i in range(retry):
            try:
                result = solver.recaptcha(
                    sitekey=sitekey,
                    url=self.driver.current_url,
                    invisible=1,
                    enterprise=enterprise,
                )
            except Exception as e:
                self.__verbose_print('twocaptcha solver error', e)
            if result is not None:
                break
        if result is None:
            return
        captcha_info_element = self.driver.find_element(
            By.XPATH, '//input[@name="captcha"]'
        )
        self.driver.execute_script(
            "arguments[0].setAttribute('value',arguments[1])",
            captcha_info_element,
            result['code'],
        )
        # self.driver.find_element(By.XPATH, '//input[@name="captcha"]').get_attribute('value')

    def __openai_login(self):
        self.__verbose_print('[login] Entering email')
        WebDriverWait(self.driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, '//input[@name="username"]'))
        )
        self.driver.find_element(By.XPATH, '//input[@name="username"]').send_keys(
            self.__email
        )
        # sometimes need to click Continue first to show reCAPTCHA
        self.driver.find_element(By.XPATH, '//button[text()="Continue"]').click()
        # switch reCAPTCHA and click
        need_check_recaptcha_result = False
        try:
            time.sleep(0.5)
            WebDriverWait(self.driver, 3).until(
                EC.frame_to_be_available_and_switch_to_it(
                    (By.CSS_SELECTOR, "iframe[title='reCAPTCHA']")
                )
            )
            WebDriverWait(self.driver, 3).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        '//label[@class="rc-anchor-center-item rc-anchor-checkbox-label"]',
                    )
                )
            )
            self.driver.find_element(
                By.XPATH,
                '//label[@class="rc-anchor-center-item rc-anchor-checkbox-label"]',
            ).click()
            need_check_recaptcha_result = True
        except SeleniumExceptions.NoSuchFrameException as e:
            self.__verbose_print(e)
        except SeleniumExceptions.TimeoutException as e:
            self.__verbose_print(e)

        # check whether reCAPTCHA value is filled.
        try:
            WebDriverWait(self.driver, 3).until(
                EC.text_to_be_present_in_element_attribute(
                    (By.XPATH, '//input[@name="captcha"]'), 'value', '_'
                )
            )
        except SeleniumExceptions.TimeoutException:
            if self.__twocaptcha_apikey:
                self.__2captcha_solve()

        if need_check_recaptcha_result:
            if self.__have_recaptcha_value():
                self.__verbose_print('[login] Congrats, solved reCAPTCHA.')
            elif self.__openai_auth_semi_automatic:
                self.__verbose_print(
                    '[login] Ops, you have to solve reCAPTCHA on browser.'
                )
                while need_check_recaptcha_result:
                    # check image selection reCAPTCHA
                    # self.__have_image_recaptcha()
                    time.sleep(1)
                    if self.__have_recaptcha_value():
                        break

        # switch back
        self.driver.switch_to.default_content()
        # Exit reCAPTCHA iframe by clicking on blank space, then "Continue" button is available
        action = ActionChains(self.driver)
        action.move_by_offset(1, 1)
        action.click()
        action.perform()

        time.sleep(0.5)
        self.__verbose_print('[login] Clicking Continue')
        self.driver.find_element(By.XPATH, '//button[text()="Continue"]').click()
        time.sleep(0.5)
        # Enter password
        self.__verbose_print('[login] Entering password')
        WebDriverWait(self.driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, '//input[@type="password"]'))
        )
        self.driver.find_element(By.XPATH, '//input[@type="password"]').send_keys(
            self.__password
        )
        self.__verbose_print('[login] Clicking Next')
        self.driver.find_element(By.XPATH, '//button[text()="Continue"]').click()

    def __ensure_cf(self, retry: int = 0) -> None:
        '''
        Ensure that the Cloudflare cookies is still valid\n
        Parameters:
        - retry: The number of times this function has been called recursively
        '''
        # Open a new tab
        self.__verbose_print('[cf] Opening new tab')
        original_window = self.driver.current_window_handle
        self.driver.switch_to.new_window('tab')

        # Get the Cloudflare challenge
        self.__verbose_print('[cf] Getting authorization')
        self.driver.get('https://chat.openai.com/api/auth/session')
        try:
            WebDriverWait(self.driver, 15).until_not(
                EC.presence_of_element_located((By.ID, 'challenge-form'))
            )
        except SeleniumExceptions.TimeoutException:
            self.driver.save_screenshot(f'cf_failed_{retry}.png')
            if retry <= 4:
                self.__verbose_print(
                    f'[cf] Cloudflare challenge failed, retrying {retry + 1}'
                )
                self.__verbose_print('[cf] Closing tab')
                self.driver.close()
                self.driver.switch_to.window(original_window)
                return self.__ensure_cf(retry + 1)
            else:
                resp_text = self.driver.page_source
                raise ValueError(f'Cloudflare challenge failed: {resp_text}')

        # Validate the authorization
        self.__verbose_print('[cf] Validating authorization')
        resp = self.driver.page_source
        if resp[0] != '{':  # its probably not a json
            self.__verbose_print('[cf] resp is not json')
            resp = self.driver.find_element(By.TAG_NAME, 'pre').text
        data = json.loads(resp)
        if data and 'error' in data:
            self.__verbose_print(f'[cf] {data["error"]}')
            if data['error'] == 'RefreshAccessTokenError':
                if not self.__auth_type:
                    raise ValueError('Session token expired')
                self.__login()
            else:
                raise ValueError(f'Authorization error: {data["error"]}')
        elif not data:
            self.__verbose_print('[cf] Authorization is empty')
            if not self.__auth_type:
                raise ValueError('Invalid session token')
            self.__login()
        self.__verbose_print('[cf] Authorization is valid')

        # Close the tab
        self.__verbose_print('[cf] Closing tab')
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
        # Ensure that the Cloudflare cookies is still valid
        self.__verbose_print('[send_msg] Ensuring Cloudflare cookies')
        self.__ensure_cf()

        # Send the message
        self.__verbose_print('[send_msg] Sending message')
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
        self.__verbose_print('[send_msg] Waiting for completion')
        WebDriverWait(self.driver, 5).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'result-streaming'))
        )
        WebDriverWait(self.driver, 120).until_not(
            EC.presence_of_element_located((By.CLASS_NAME, 'result-streaming'))
        )

        # Get the response element
        self.__verbose_print('[send_msg] Finding response element')
        response = self.driver.find_elements(
            By.XPATH, '//div[starts-with(@class, "markdown prose w-full break-words")]'
        )[-1]

        # Check if the response is an error
        self.__verbose_print('[send_msg] Checking if response is an error')

        if 'text-red' in response.get_attribute('class'):
            self.__verbose_print('[send_msg] Response is an error')
            raise ValueError(response.text)
        self.__verbose_print('[send_msg] Response is not an error')

        # Return the response
        msg = markdownify.markdownify(response.get_attribute('innerHTML')).replace(
            'Copy code`', '`'
        )
        return {'message': msg, 'conversation_id': '', 'parent_id': ''}

    def reset_conversation(self) -> None:
        '''
        Reset the conversation
        '''
        self.__verbose_print('Resetting conversation')
        self.driver.find_element(By.LINK_TEXT, 'New chat').click()
