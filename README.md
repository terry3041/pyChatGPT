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

session_token = 'abc123'
api = ChatGPT(session_token)
resp = api.send_message('Hello, world!')
print(resp['message'])
```

### Insipration

This project is inspired by

-   [ChatGPT](https://github.com/acheong08/ChatGPT)
-   [chatgpt-api](https://github.com/transitive-bullshit/chatgpt-api)
