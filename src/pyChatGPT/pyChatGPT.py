from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.common import exceptions as SeleniumExceptions
import undetected_chromedriver as uc

from pyvirtualdisplay import Display
import markdownify
import platform
import json
import os
import re


class ChatGPT:
    '''
    An unofficial Python wrapper for OpenAI's ChatGPT API
    '''

    def __init__(
        self,
        session_token: str,
        proxy: str = None,
    ) -> None:
        '''
        Initialize the ChatGPT class\n
        Either provide a session token or email and password\n
        Parameters:
        - session_token: Your session token in cookies named as `__Secure-next-auth.session-token` from https://chat.openai.com/chat
        - proxy: (optional) The proxy to use, in URL format (i.e. `https://ip:port`)
        '''
        self.proxy = proxy
        if self.proxy and not re.findall(r'https?:\/\/.*:\d{1,5}', self.proxy):
            raise ValueError('Invalid proxy format')

        self.session_token = session_token
        self.is_headless = platform.system() == 'Linux' and 'DISPLAY' not in os.environ
        self.__init_browser()

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
        if self.is_headless:
            try:
                self.display = Display()
            except FileNotFoundError as e:
                if 'No such file or directory: \'Xvfb\'' in str(e):
                    raise ValueError(
                        'Headless machine detected. Please install Xvfb to start a virtual display: sudo apt install xvfb'
                    )
                raise e
            self.display.start()

        # Start the browser
        options = uc.ChromeOptions()
        options.add_argument('--window-size=800,600')
        if self.proxy:
            options.add_argument(f'--proxy-server={self.proxy}')
        try:
            self.driver = uc.Chrome(options=options, enable_cdp_events=True)
        except TypeError as e:
            if str(e) == 'expected str, bytes or os.PathLike object, not NoneType':
                raise ValueError('Chrome installation not found')
            raise e

        # Restore session token
        self.driver.execute_cdp_cmd(
            'Network.setCookie',
            {
                'domain': 'chat.openai.com',
                'path': '/',
                'name': '__Secure-next-auth.session-token',
                'value': self.session_token,
                'httpOnly': True,
                'secure': True,
            },
        )

        # Ensure that the Cloudflare challenge is still valid
        self.__ensure_cf()

        # Open the chat page
        self.driver.get('https://chat.openai.com/chat')

        # Dismiss the ChatGPT intro
        self.driver.execute_script(
            """
        var element = document.getElementById('headlessui-portal-root');
        if (element)
            element.parentNode.removeChild(element);
        """
        )

    def __ensure_cf(self, retry: int = 0) -> None:
        '''
        Ensure that the Cloudflare challenge is still valid\n
        Parameters:
        - retry: The number of times this function has been called recursively
        '''
        # Open a new tab
        original_window = self.driver.current_window_handle
        self.driver.switch_to.new_window('tab')
        if not self.is_headless:
            self.driver.minimize_window()

        # Get the Cloudflare challenge
        self.driver.get('https://chat.openai.com/api/auth/session')
        try:
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, 'pre'))
            )
        except SeleniumExceptions.TimeoutException:
            resp_text = self.driver.page_source
            if '<title>Just a moment...</title>' in resp_text:
                if retry <= 2:
                    self.driver.close()
                    self.driver.switch_to.window(original_window)
                    if not self.is_headless:
                        self.driver.minimize_window()
                    return self.__ensure_cf(retry + 1)
            raise ValueError(f'Cloudflare challenge failed: {resp_text}')

        # Validate the authorization
        resp = self.driver.find_element(By.TAG_NAME, 'pre').text
        data = json.loads(resp)
        if not data:
            raise ValueError('Invalid session token')

        # Close the tab
        self.driver.close()
        self.driver.switch_to.window(original_window)
        if not self.is_headless:
            self.driver.minimize_window()

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
        self.__ensure_cf()

        # Send the message
        self.driver.find_element(By.TAG_NAME, 'textarea').send_keys(message)
        self.driver.find_element(By.TAG_NAME, 'textarea').send_keys(Keys.ENTER)

        # Get the response element
        request = self.driver.find_elements(
            By.XPATH, "//div[starts-with(@class, 'request-:')]"
        )[-1]

        # Wait for the response to be ready
        WebDriverWait(self.driver, 90).until_not(
            EC.presence_of_element_located((By.CLASS_NAME, 'result-streaming'))
        )

        # Check if the response is an error
        if 'text-red' in request.get_attribute('class'):
            raise ValueError(request.text)

        # Return the response
        return {
            'message': markdownify.markdownify(request.get_attribute('innerHTML')),
            'conversation_id': '',
            'parent_id': '',
        }

    def reset_conversation(self) -> None:
        '''
        Reset the conversation
        '''
        self.driver.find_element(By.LINK_TEXT, 'New Thread').click()
