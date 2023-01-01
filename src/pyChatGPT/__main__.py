from pyChatGPT import ChatGPT
import os


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


if __name__ == '__main__':
    while True:
        session_token = input('Please enter your session token: ')
        conversation_id = input(
            'Please enter your conversation id (if you want to continue old chat): '
        )
        chat = ChatGPT(session_token, conversation_id)
        break

    clear_screen()
    print(
        'Conversation started. Type "reset" to reset the conversation. Type "quit" to quit.\n'
    )
    while True:
        prompt = input('\nYou: ')
        if prompt.lower() == 'reset':
            chat.reset_conversation()
            clear_screen()
            print(
                'Conversation started. Type "reset" to reset the conversation. Type "quit" to quit.\n'
            )
            continue
        if prompt.lower() == 'quit':
            break
        print('\nChatGPT: ', end='')
        response = chat.send_message(prompt)
        print(response['message'], end='')
