import requests
import uuid
import json
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
        conversation_id: str = None,
        proxy: str = None,
    ) -> None:
        '''
        Initialize the ChatGPT class\n
        Either provide a session token or email and password\n
        Parameters:
        - session_token: (optional) Your session token in cookies named as `__Secure-next-auth.session-token` from https://chat.openai.com/chat
        - email: (optional) Your OpenAI email
        - password: (optional) Your OpenAI password
        - conversation_id: (optional) The conversation ID if you want to continue a conversation
        - proxy: (optional) The proxy to use, in URL format (i.e. `https://ip:port`)
        '''
        self.conversation_id = conversation_id
        self.parent_id = str(uuid.uuid4())
        self.proxies = {'http': proxy, 'https': proxy} if proxy else {}
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36 Edg/107.0.1418.62',
        }
        self.session_token = session_token
        if not self.session_token:
            if not email or not password:
                raise ValueError('No session token or login credentials are provideddd')
            self.session_token = self._login(email, password)
        self.headers[
            'Cookie'
        ] = f'__Secure-next-auth.session-token={self.session_token}'
        self.refresh_auth()

    def _login(self, email: str, password: str) -> str:
        '''
        Login to OpenAI\n
        Parameters:
        - email: Your OpenAI email
        - password: Your OpenAI password\n
        Returns the session token
        '''
        session = requests.Session()
        session.headers = self.headers
        session.proxies = self.proxies

        # Get the CSRF token
        resp = session.get('https://chat.openai.com/api/auth/csrf')
        csrf_token = resp.json()['csrfToken']

        # Get state
        resp = session.post(
            'https://chat.openai.com/api/auth/signin/auth0?prompt=login',
            data={'callbackUrl': '/', 'csrfToken': csrf_token, 'json': 'true'},
        )
        if resp.status_code != 200:
            raise ValueError(f'Status code {resp.status_code}: {resp.text}')
        redirect_url = resp.json()['url']

        # Redirect to auth0 /login/identifier
        resp = session.get(redirect_url)
        if resp.status_code != 200:
            raise ValueError(f'Status code {resp.status_code}: {resp.text}')
        pattern = r'<input type="hidden" name="state" value="(.*)" \/>'
        results = re.findall(pattern, resp.text)
        if not results:
            raise ValueError(f'Could not get state: {resp.text}')
        state = results[0]

        # Post email
        resp = session.post(
            f'https://auth0.openai.com/u/login/identifier?state={state}',
            data={
                'state': state,
                'username': email,
                'js-available': 'false',
                'webauthn-available': 'true',
                'is-brave': 'false',
                'webauthn-platform-available': 'false',
                'action': 'default',
            },
        )
        if resp.status_code != 200:
            raise ValueError(f'Status code {resp.status_code}: {resp.text}')

        # Post password
        resp = session.post(
            f'https://auth0.openai.com/u/login/password?state={state}',
            data={
                'state': state,
                'username': email,
                'password': password,
                'action': 'default',
            },
        )
        if resp.status_code != 200:
            raise ValueError(f'Status code {resp.status_code}: {resp.text}')

        # Get session token in CookieJar
        cookies = session.cookies.get_dict()
        if '__Secure-next-auth.session-token' not in cookies:
            raise ValueError(f'Could not get session token: {cookies}')
        return cookies['__Secure-next-auth.session-token']

    def refresh_auth(self) -> None:
        '''
        Refresh the authorization token
        '''
        resp = requests.get(
            'https://chat.openai.com/api/auth/session',
            headers=self.headers,
            proxies=self.proxies,
        )
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
        resp = requests.post(
            'https://chat.openai.com/backend-api/conversation',
            headers=self.headers,
            proxies=self.proxies,
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
