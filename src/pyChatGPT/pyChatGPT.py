import requests
import uuid
import json


class ChatGPT:
    '''
    An unofficial Python wrapper for OpenAI's ChatGPT API
    '''

    def __init__(
        self, session_token: str, conversation_id: str = None, proxy: str = None
    ) -> None:
        '''
        Initialize the ChatGPT class\n
        Parameters:
        - session_token: Your session token in cookies named as `__Secure-next-auth.session-token` from https://chat.openai.com/chat
        - conversation_id: (optional) The conversation ID if you want to continue a conversation
        - proxies: (optional) A `dict` of proxies to use, in the format of requests' proxies
        '''
        self.session_token = session_token
        self.conversation_id = conversation_id
        self.parent_id = str(uuid.uuid4())
        self.proxies = {'http': proxy, 'https': proxy} if proxy else {}
        self.headers = {
            'Cookie': f'__Secure-next-auth.session-token={self.session_token}',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36 Edg/107.0.1418.62',
        }
        self.refresh_auth()

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
