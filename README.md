# pyChatGPT

An unofficial Python wrapper for OpenAI's ChatGPT API

## Getting Started

### Installation

```bash
pip install pyChatGPT
```

### Usage

#### Interactive mode

```bash
python -m pyChatGPT
```

#### Import as a module

```python
from pyChatGPT import ChatGPT

session_token = 'abc123'  # `__Secure-next-auth.session-token` cookie from https://chat.openai.com/chat
api = ChatGPT(session_token)
resp = api.send_message('Hello, world!')
print(resp['message'])

api.refresh_auth()  # refresh the authorization token
api.reset_conversation()  # reset the conversation
```

## Insipration

This project is inspired by

-   [ChatGPT](https://github.com/acheong08/ChatGPT)
-   [chatgpt-api](https://github.com/transitive-bullshit/chatgpt-api)
