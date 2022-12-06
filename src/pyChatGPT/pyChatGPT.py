import requests
import uuid
import json


class ChatGPT:
    def __init__(self, session_token: str, conversation_id: str = None) -> None:
        self.session_token = session_token
        self.headers = {
            'Cookie': f'__Secure-next-auth.session-token={self.session_token}',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36 Edg/107.0.1418.62',
        }
        self.conversation_id = conversation_id
        self.parent_id = str(uuid.uuid4())
        if not self.session_token:
            raise ValueError('Please provide a session token')
        self.refresh_auth()

    def refresh_auth(self) -> None:
        r = requests.get(
            'https://chat.openai.com/api/auth/session',
            headers=self.headers,
        )
        try:
            access_token = r.json()['accessToken']
            self.headers['Authorization'] = f'Bearer {access_token}'
        except KeyError:
            print(r.text)
            raise ValueError('Invalid session token')
        except Exception:
            print(r.text)
            raise ValueError('Unknown error')

    def reset_conversation(self) -> None:
        self.conversation_id = None
        self.parent_id = str(uuid.uuid4())

    def send_message(self, message: str) -> dict:
        r = requests.post(
            'https://chat.openai.com/backend-api/conversation',
            headers=self.headers,
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
        )
        try:
            data = list(r.iter_lines())[-4].decode('utf-8').lstrip('data: ')
            data = json.loads(data)
            return {
                'message': data['message']['content']['parts'][0],
                'conversation_id': data['conversation_id'],
                'parent_id': data['message']['id'],
            }
        except Exception:
            print(r.text)
            raise ValueError('Unknown error')
