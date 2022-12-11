# pyChatGPT

[![PyPi](https://img.shields.io/pypi/v/pyChatGPT.svg)](https://pypi.python.org/pypi/pyChatGPT)
[![License](https://img.shields.io/github/license/terry3041/pyChatGPT.svg?color=green)](https://github.com/terry3041/pyChatGPT/blob/main/LICENSE)
![PyPi](https://img.shields.io/badge/code_style-black+flake8-blue.svg)

An unofficial Python wrapper for OpenAI's ChatGPT API

## Getting Started

### Installation

```bash
pip install pyChatGPT
```

### Usage

#### Obtaining session_token

1. Go to https://chat.openai.com/chat and open the developer tools by `F12`.
2. Find the `__Secure-next-auth.session-token` cookie in `Application` > `Storage` > `Cookies` > `https://chat.openai.com`.
3. Copy the value in the `Cookie Value` field.

![image](https://user-images.githubusercontent.com/19218518/206170122-61fbe94f-4b0c-4782-a344-e26ac0d4e2a7.png)

#### Interactive mode

```bash
python -m pyChatGPT
```

#### Import as a module

```python
from pyChatGPT import ChatGPT

session_token = 'abc123'  # `__Secure-next-auth.session-token` cookie from https://chat.openai.com/chat
api = ChatGPT(session_token)  # auth with session token
api2 = ChatGPT(email='example@domain.com', password='password')  # auth with email and password
api3 = ChatGPT(session_token, conversation_id='some-random-uuid', parent_id='another-random-uuid')  # specify a conversation id
api4 = ChatGPT(session_token, proxy='http://proxy.example.com:8080')  # specify proxy

resp = api.send_message('Hello, world!')
print(resp['message'])

api.refresh_auth()  # refresh the authorization token
api.reset_conversation()  # reset the conversation
```

## Insipration

This project is inspired by

-   [ChatGPT](https://github.com/acheong08/ChatGPT)
-   [chatgpt-api](https://github.com/transitive-bullshit/chatgpt-api)

## Disclaimer

This project is not affiliated with OpenAI in any way. Use at your own risk. I am not responsible for any damage caused by this project. Please read the [OpenAI Terms of Service](https://beta.openai.com/terms) before using this project.

## License

This project is licensed under the GPLv3 License - see the [LICENSE](LICENSE) file for details.
