from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By

import undetected_chromedriver as uc
import requests
import uuid
import json


class ChatGPT:
    '''
    An unofficial Python wrapper for OpenAI's ChatGPT API
    '''

    def __init__(
        self,
        session_token: str,
        conversation_id: str = None,
        parent_id: str = None,
        proxy: str = None,
    ) -> None:
        '''
        Initialize the ChatGPT class\n
        Either provide a session token or email and password\n
        Parameters:
        - session_token: Your session token in cookies named as `__Secure-next-auth.session-token` from https://chat.openai.com/chat
        - conversation_id: (optional) The conversation ID if you want to continue a conversation
        - parent_id: (optional) The parent ID if you want to continue a conversation
        - proxy: (optional) The proxy to use, in URL format (i.e. `https://ip:port`)
        '''
        self.conversation_id = conversation_id
        if parent_id:
            self.parent_id = parent_id
        else:
            self.parent_id = str(uuid.uuid4())

        self.proxy = proxy
        self.proxies = {'http': proxy, 'https': proxy} if proxy else {}
        self.headers = {
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate',
            'accept-language': 'en-US;q=0.9,en;q=0.8',
            'origin': 'https://chat.openai.com',
            'referer': 'https://chat.openai.com/chat',
            'x-openai-assistant-app-id': '',
        }
        self.session = requests.Session()
        self.session.headers = self.headers
        self.session.proxies = self.proxies

        self.session_token = session_token
        self.refresh_cookies()

    def refresh_cookies(self) -> None:
        '''
        Refresh the session cookies
        '''
        options = uc.ChromeOptions()
        if self.proxy:
            options.add_argument(f'--proxy-server={self.proxy}')
        self.driver = uc.Chrome(options=options)

        self.driver.get('https://chat.openai.com/')
        self.headers['user-agent'] = self.driver.execute_script(
            'return navigator.userAgent'
        )
        self.driver.add_cookie(
            {'name': '__Secure-next-auth.session-token', 'value': self.session_token}
        )
        WebDriverWait(self.driver, 10).until(
            EC.text_to_be_present_in_element((By.TAG_NAME, 'h1'), 'ChatGPT')
        )
        for cookie in self.driver.get_cookies():
            self.session.cookies.set(cookie['name'], cookie['value'])
        self.driver.close()
        self.driver.quit()

    def refresh_auth(self) -> None:
        '''
        Refresh the session's authorization
        '''
        resp = self.session.get('https://chat.openai.com/api/auth/session')
        if resp.status_code != 200:
            raise ValueError(f'Status code {resp.status_code}: {resp.text}')

        data = resp.json()
        if not data:
            raise ValueError('Invalid session token')
        access_token = data['accessToken']
        self.headers['Authorization'] = f'Bearer {access_token}'

    def reset_conversation(self) -> None:
        '''
        Reset the conversation
        '''
        self.conversation_id = None
        self.parent_id = str(uuid.uuid4())

    def moderation(self) -> None:
        '''
        Fake moderation request
        '''
        resp = self.session.post(
            'https://chat.openai.com/backend-api/moderations',
            json={'input': 'Hello', 'model': 'text-moderation-playground'},
        )
        if resp.status_code != 200:
            raise ValueError(f'Status code {resp.status_code}: {resp.text}')
        data = resp.json()
        if data['blocked'] or data['flagged']:
            raise ValueError(f'Message is blocked or flagged: {resp.text}')

    def send_message(self, message: str) -> dict:
        '''
        Send a message to the chatbot\n
        Parameters:
        - message: The message you want to send\n
        Returns a `dict` with the following keys:
        - message: The message the chatbot sent
        - conversation_id: The conversation ID
        - parent_id: The parent message ID
        '''
        self.refresh_auth()
        self.moderation()
        resp = self.session.post(
            'https://chat.openai.com/backend-api/conversation',
            json={
                'action': 'next',
                'messages': [
                    {
                        'id': str(uuid.uuid4()),
                        'role': 'user',
                        'content': {'content_type': 'text', 'parts': [message]},
                    }
                ],
                'conversation_id': self.conversation_id,
                'parent_message_id': self.parent_id,
                'model': 'text-davinci-002-render',
            },
            stream=True,
        )
        if resp.status_code != 200:
            raise ValueError(f'Status code {resp.status_code}: {resp.text}')

        data = list(resp.iter_lines())[-4].decode('utf-8').lstrip('data: ')
        data = json.loads(data)
        self.conversation_id = data['conversation_id']
        self.parent_id = data['message']['id']
        return {
            'message': data['message']['content']['parts'][0],
            'conversation_id': self.conversation_id,
            'parent_id': self.parent_id,
        }
