from pyChatGPT import ChatGPT
import os


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


if __name__ == '__main__':
    session_token = input('Please enter your session token: ')
    chat = ChatGPT(session_token)
    clear_screen()
    print(
        'Conversation started. Type "reset" to reset the conversation. Type "reauth" to reauthenticate.'
    )
    while True:
        prompt = input('\nYou: ')
        if prompt.lower() == 'reset':
            chat.reset_conversation()
            clear_screen()
            print(
                'Conversation started. Type "reset" to reset the conversation. Type "reauth" to reauthenticate.'
            )
            continue
        if prompt.lower() == 'reauth':
            chat.refresh_auth()
            print('Reauthenticated.')
            continue
        print('\nChatGPT: ', end='')
        response = chat.send_message(prompt)
        print(response['message'])
