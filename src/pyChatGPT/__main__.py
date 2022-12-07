from pyChatGPT import ChatGPT
import os


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


if __name__ == '__main__':
    while True:
        authMethod = input('Please enter your auth method (token or email): ')
        if authMethod.lower() == 'token':
            session_token = input('Please enter your session token: ')
            chat = ChatGPT(session_token)
            break
        elif authMethod.lower() == 'email':
            email = input('Please enter your email: ')
            password = input('Please enter your password: ')
            chat = ChatGPT(email, password)
            break
        clear_screen()

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
        print('\nChatGPT:', end=' ')
        response = chat.send_message(prompt)
        print(response['message'])
