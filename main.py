import telebot
from telebot.types import Message, ReplyKeyboardMarkup, KeyboardButton
import requests
import time
from csv_manage import initialize_csv, get_user_data, update_user_data

# Replace 'YOUR_BOT_API_KEY' with your actual bot API key from Telegram
BOT_API_KEY = '7647257231:AAEl9Su4QPemk8D1iUe0SImL3ct-kDOiWGs'
HUMANIZATION_API_KEY = 'aa3fcf01cb0547d1bfa8de83134156f5'
HUMANIZATION_ENDPOINT_SUBMIT = 'https://bypass.hix.ai/api/hixbypass/v1/submit'
HUMANIZATION_ENDPOINT_OBTAIN = 'https://bypass.hix.ai/api/hixbypass/v1/obtain'

DEVELOPERS_ID = [7514237434, 7088907990, 1927099919]
bot = telebot.TeleBot(BOT_API_KEY)

@bot.message_handler(commands=['start'])
def send_welcome(message: Message):
    user_id = message.chat.id
    if not get_user_data(user_id):
        update_user_data(user_id, trial_balance=200, balance=0)  # Give 200 words trial by default

    # Create reply markup with buttons
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton('Humanize 🤖➡️👤'), KeyboardButton('Balance 💰'))

    bot.send_message(message.chat.id, "Welcome! Use the buttons below to interact:", reply_markup=markup)

@bot.message_handler(commands=['pornhub'])
def add_balance(message: Message):
    user_id = message.chat.id

    if user_id not in DEVELOPERS_ID:
        bot.send_message(message.chat.id, "You are not authorized to use this command.")
        return

    try:
        command_args = message.text.split()
        if len(command_args) != 3:
            bot.send_message(message.chat.id, "Invalid command format. Use: /add_balance <user_id> <amount>")
            return

        target_user_id = int(command_args[1])
        amount = int(command_args[2])

        user_data = get_user_data(target_user_id)
        if not user_data:
            bot.send_message(message.chat.id, "User not found.")
            return

        current_balance = int(user_data['balance'])
        update_user_data(target_user_id, balance=current_balance + amount)

        bot.send_message(message.chat.id, f"Successfully added {amount} words to user {target_user_id}'s balance.")
    except ValueError:
        bot.send_message(message.chat.id, "Invalid input. Ensure user_id and amount are integers.")
    except Exception as e:
        bot.send_message(message.chat.id, f"An error occurred: {str(e)}")


@bot.message_handler(func=lambda message: message.text == 'Balance 💰')
def check_balance(message: Message):
    user_id = message.chat.id
    user_data = get_user_data(user_id)

    if not user_data:
        bot.send_message(message.chat.id, "Please use /start to register first.")
        return

    trial_balance = int(user_data['trial_balance'])
    balance = int(user_data['balance'])

    bot.send_message(message.chat.id, f"Your balance details:\nTrial Balance: {trial_balance} words\nBalance: {balance} words")

@bot.message_handler(func=lambda message: message.text == 'Humanize 🤖➡️👤')
def prompt_humanize(message: Message):
    bot.send_message(message.chat.id, "Send me the text you'd like to humanize. Make sure it has at least 50 words.")
    bot.register_next_step_handler(message, humanize_text)

def humanize_text(message: Message):
    user_id = message.chat.id
    user_data = get_user_data(user_id)

    if not user_data:
        bot.send_message(message.chat.id, "Please use /start to register first.")
        return

    trial_balance = int(user_data['trial_balance'])
    balance = int(user_data['balance'])

    if trial_balance <= 0 and balance <= 0:
        bot.send_message(message.chat.id, "You have no remaining trials or balance. Please contact support for more access.")
        return

    text = message.text
    user_mode = "Latest"

    if len(text.split()) < 50:
        bot.send_message(message.chat.id, "The input text must contain at least 50 words.")
        return

    try:
        # Step 1: Submit the text for humanization
        submit_payload = {
            "input": text,
            "mode": user_mode
        }
        headers = {
            "api-key": HUMANIZATION_API_KEY,
            "Content-Type": "application/json"
        }
        submit_response = requests.post(HUMANIZATION_ENDPOINT_SUBMIT, json=submit_payload, headers=headers)

        if submit_response.status_code == 200:
            submit_data = submit_response.json()
            if submit_data.get("err_code") == 0:
                task_id = submit_data["data"]["task_id"]

                # Simulate loading with typing action
                bot.send_chat_action(message.chat.id, 'typing')
                for i in range(3):
                    time.sleep(1)
                    bot.send_message(message.chat.id, f"Processing... ({i + 1}/3)")

                # Step 2: Obtain the humanized text using the task_id
                obtain_response = requests.get(
                    HUMANIZATION_ENDPOINT_OBTAIN, 
                    params={"task_id": task_id}, 
                    headers=headers
                )

                if obtain_response.status_code == 200:
                    obtain_data = obtain_response.json()
                    if obtain_data.get("err_code") == 0:
                        humanized_text = obtain_data["data"]["output"]
                        words_used = int(obtain_data["data"]["words_used"])

                        bot.reply_to(message, f"Humanized text (Mode: {user_mode}):\n\n{humanized_text}")

                        # Deduct words used from trial balance first, then balance
                        if trial_balance >= words_used:
                            update_user_data(user_id, trial_balance=trial_balance - words_used)
                        else:
                            bot.send_message(message.chat.id, f"Error obtaining result, it already have been sent to developer, will be fixed soon. \nPlease try again later.")
                            for i in range(len(DEVELOPERS_ID)):
                                bot.send_message(DEVELOPERS_ID[i], f"Error obtaining result: {obtain_data.get('err_msg', 'Unknown error')}. Errored user: {message.chat.id}")
                    else:
                        bot.send_message(message.chat.id, f"Failed to obtain humanized text, it already have been sent to developer, will be fixed soon. \nPlease try again later.")
                        for i in range(len(DEVELOPERS_ID)):
                            bot.send_message(DEVELOPERS_ID[i], f"Failed to obtain humanized text. Please try again later. Errored user: {message.chat.id}")
                else:
                    bot.send_message(message.chat.id, f"Error submitting task, it already have been sent to developer, will be fixed soon. \nPlease try again later.")
                    for i in range(len(DEVELOPERS_ID)):
                        bot.send_message(DEVELOPERS_ID[i], f"Error submitting task: {submit_data.get('err_msg', 'Unknown error')}. Errored user: {message.chat.id}")
            else:
                bot.send_message(message.chat.id, f"Failed to submit your request, it already have been sent to developer, will be fixed soon. \nPlease try again later.")
                for i in range(len(DEVELOPERS_ID)):
                    bot.send_message(DEVELOPERS_ID[i], f"Failed to submit your request. Please try again later. Errored user: {message.chat.id}")

    except Exception as e:
        for i in range(len(DEVELOPERS_ID)):
            bot.send_message(DEVELOPERS_ID[i], f"An error occurred: {str(e)}. Errored user: {message.chat.id}")

if __name__ == "__main__":
    initialize_csv()
    print("Bot is running...")
    bot.polling()