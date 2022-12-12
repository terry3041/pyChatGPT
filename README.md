# pyChatGPT

[![PyPi](https://img.shields.io/pypi/v/pyChatGPT.svg)](https://pypi.python.org/pypi/pyChatGPT)
[![License](https://img.shields.io/github/license/terry3041/pyChatGPT.svg?color=green)](https://github.com/terry3041/pyChatGPT/blob/main/LICENSE)
![PyPi](https://img.shields.io/badge/code_style-black+flake8-blue.svg)

An unofficial Python wrapper for OpenAI's ChatGPT API

## Getting Started

> On 2022/12/11, OpenAI has implemented Cloudflare's anti-bot protection on the ChatGPT API. This wrapper is now using `undetected_chromedriver` to bypass the protection. **Please make sure you have [Google Chrome](https://www.google.com/chrome/) before using this wrapper.**

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
api2 = ChatGPT(email='example@domain.com', password='password')  # auth with email and password (unreliable)
api3 = ChatGPT(session_token, conversation_id='some-random-uuid', parent_id='another-random-uuid')  # specify a conversation
api4 = ChatGPT(session_token, proxy='http://proxy.example.com:8080')  # specify proxy
api5 = ChatGPT(session_token, cf_refresh_interval=30)  # specify the interval to refresh the cf cookies (in minutes)

resp = api.send_message('Hello, world!')
print(resp['message'])

api.reset_conversation()  # reset the conversation
```

## Frequently Asked Questions

### How do I get it to work on headless linux server?

```bash
# install chromium
sudo apt install chromium

# install X virtual framebuffer
sudo apt install xvfb

# start a Xvfb with your script
xvfb-run -a python3 your_script.py
```

## Insipration

This project is inspired by

-   [ChatGPT](https://github.com/acheong08/ChatGPT)
-   [chatgpt-api](https://github.com/transitive-bullshit/chatgpt-api)
-   [PyChatGPT](https://github.com/rawandahmad698/PyChatGPT)

## Disclaimer

This project is not affiliated with OpenAI in any way. Use at your own risk. I am not responsible for any damage caused by this project. Please read the [OpenAI Terms of Service](https://beta.openai.com/terms) before using this project.

## License

This project is licensed under the GPLv3 License - see the [LICENSE](LICENSE) file for details.
