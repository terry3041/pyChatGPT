# pyChatGPT

[![PyPi](https://img.shields.io/pypi/v/pyChatGPT.svg)](https://pypi.python.org/pypi/pyChatGPT)
[![License](https://img.shields.io/github/license/terry3041/pyChatGPT.svg?color=green)](https://github.com/terry3041/pyChatGPT/blob/main/LICENSE)
![PyPi](https://img.shields.io/badge/code_style-black+flake8-blue.svg)

An unofficial Python wrapper for OpenAI's ChatGPT API

## Features

-   [x] Bypass Cloudflare's anti-bot protection using `undetected_chromedriver`
-   [x] ~~Captcha solver when auth with login credentials (experimental)~~
-   [x] [Support headless machines](#how-do-i-get-it-to-work-on-headless-linux-server)
-   [x] Proxy support (only without basic auth)
-   [x] Google login support (experimental)

## Getting Started

> On version 0.3.0, this library is using only the `undetected_chromedriver` to bypass Cloudflare's anti-bot protection. `requests` module is no longer used due to the complexity of the protection. **Please make sure you have [Google Chrome](https://www.google.com/chrome/) before using this wrapper.** From now on, this library will not support specifying a conversation (i.e. `parent_id` and `conversation_id` parameters) but you can still reset the conversation by calling `reset_conversation()`.

### Installation

```bash
pip install -U pyChatGPT
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
api1 = ChatGPT(session_token)  # auth with session token
api2 = ChatGPT(session_token, proxy='http://proxy.example.com:8080')  # specify proxy
api3 = ChatGPT(auth_type='google', email='example@gmail.com', password='password') # auth with google login
api4 = ChatGPT(session_token, verbose=True)  # verbose mode (print debug messages)

resp = api1.send_message('Hello, world!')
print(resp['message'])

api1.reset_conversation()  # reset the conversation
api1.close()  # close the session
```

## Frequently Asked Questions

### How do I get it to work on headless linux server?

```bash
# install chromium & X virtual framebuffer
sudo apt install chromium-browser xvfb

# start your script
python3 your_script.py
```

### How do I get it to work on Google Colab?

It is normal for the seession to be crashed when installing dependencies. Just ignore the error and run your script.

```python
# install dependencies
!apt install chromium-browser xvfb
!pip install -U selenium_profiles pyChatGPT

# install chromedriver
from selenium_profiles.utils.installer import install_chromedriver
install_chromedriver()
```

```python
# start your script as normal
!python3 -m pyChatGPT
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
