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
        parent_id: str = None,
        proxy: str = None,
        user_agent: str = None,
        cf_clearance: str = None,
    ) -> None:
        '''
        Initialize the ChatGPT class\n
        Either provide a session token or email and password\n
        Parameters:
        - session_token: (optional) Your session token in cookies named as `__Secure-next-auth.session-token` from https://chat.openai.com/chat
        - email: (optional) Your OpenAI email
        - password: (optional) Your OpenAI password
        - conversation_id: (optional) The conversation ID if you want to continue a conversation
        - parent_id: (optional) The parent ID if you want to continue a conversation
        - proxy: (optional) The proxy to use, in URL format (i.e. `https://ip:port`)
        '''
        self.conversation_id = conversation_id
        if parent_id:
            self.parent_id = parent_id
        else:
            self.parent_id = str(uuid.uuid4())
        self.proxies = {'http': proxy, 'https': proxy} if proxy else {}
        self.headers = {
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate',
            'accept-language': 'en-US;q=0.9,en;q=0.8',
            'origin': 'https://chat.openai.com',
            'referer': 'https://chat.openai.com/chat',
            'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Microsoft Edge";v="108"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36 Edg/108.0.1462.46',
            'x-openai-assistant-app-id': '',
        }

        if user_agent:
            self.headers['user-agent'] = user_agent

        self.session = requests.Session()
        self.session.headers = self.headers
        self.session.proxies = self.proxies

        self.session_token = session_token
        self.cf_clearance = cf_clearance
        if not self.session_token:
            if not email or not password:
                raise ValueError('No session token or login credentials are provideddd')
            self._login(email, password)
        else:
            self.headers[
                'Cookie'
            ] = f'__Secure-next-auth.session-token={self.session_token}; cf_clearance={self.cf_clearance};'
            self.refresh_auth()

    def _login(self, email: str, password: str) -> str:
        '''
        Login to OpenAI\n
        Parameters:
        - email: Your OpenAI email
        - password: Your OpenAI password\n
        Returns the session token
        '''
        self.session.headers = self.headers
        self.session.proxies = self.proxies

        # Get the CSRF token
        resp = self.session.get('https://chat.openai.com/api/auth/csrf')
        if resp.status_code != 200:
            raise ValueError(f'Status code {resp.status_code}: {resp.text}')
        csrf_token = resp.json()['csrfToken']

        # Get state
        resp = self.session.post(
            'https://chat.openai.com/api/auth/signin/auth0?prompt=login',
            data={'callbackUrl': '/', 'csrfToken': csrf_token, 'json': 'true'},
        )
        if resp.status_code != 200:
            raise ValueError(f'Status code {resp.status_code}: {resp.text}')
        redirect_url = resp.json()['url']

        # Redirect to auth0 /login/identifier
        resp = self.session.get(redirect_url)
        if resp.status_code != 200:
            raise ValueError(f'Status code {resp.status_code}: {resp.text}')
        if '<img alt="captcha"' in resp.text:
            raise ValueError('Captcha detected')
        pattern = r'<input type="hidden" name="state" value="(.*)" \/>'
        results = re.findall(pattern, resp.text)
        if not results:
            raise ValueError(f'Could not get state: {resp.text}')
        state = results[0]

        # Post email
        resp = self.session.post(
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
        resp = self.session.post(
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
        cookies = self.session.cookies.get_dict()
        if '__Secure-next-auth.session-token' not in cookies:
            raise ValueError(f'Could not get session token: {cookies}')
        return cookies['__Secure-next-auth.session-token']

    def refresh_auth(self) -> None:
        '''
        Refresh the authorization token
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
