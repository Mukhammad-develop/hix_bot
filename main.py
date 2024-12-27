import telebot
from telebot.types import Message
import requests
import time

# Replace 'YOUR_BOT_API_KEY' with your actual bot API key from Telegram
BOT_API_KEY = '7647257231:AAEl9Su4QPemk8D1iUe0SImL3ct-kDOiWGs'
HUMANIZATION_API_KEY = 'aa3fcf01cb0547d1bfa8de83134156f5'
HUMANIZATION_ENDPOINT_SUBMIT = 'https://bypass.hix.ai/api/hixbypass/v1/submit'
HUMANIZATION_ENDPOINT_OBTAIN = 'https://bypass.hix.ai/api/hixbypass/v1/obtain'

bot = telebot.TeleBot(BOT_API_KEY)

@bot.message_handler(commands=['start'])
def send_welcome(message: Message):
    bot.reply_to(message, "Welcome! Send me text to humanize it. Use /help for more info.")

@bot.message_handler(commands=['request'])
def send_help(message: Message):
    help_text = (
        "Send me any text with at least 50 words, and I'll humanize it for you.\n"
        "The mode used for humanization will always be 'Latest'."
    )
    bot.reply_to(message, help_text)

@bot.message_handler(func=lambda msg: True)
def humanize_text(message: Message):
    user_mode = "Latest"
    text = message.text

    if len(text.split()) < 50:
        bot.reply_to(message, "The input text must contain at least 50 words.")
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
                        bot.reply_to(message, f"Humanized text (Mode: {user_mode}):\n\n{humanized_text}")
                    else:
                        bot.reply_to(message, f"Error obtaining result: {obtain_data.get('err_msg', 'Unknown error')}.")
                else:
                    bot.reply_to(message, "Failed to obtain humanized text. Please try again later.")
            else:
                bot.reply_to(message, f"Error submitting task: {submit_data.get('err_msg', 'Unknown error')}.")
        else:
            bot.reply_to(message, "Failed to submit your request. Please try again later.")

    except Exception as e:
        bot.reply_to(message, f"An error occurred: {str(e)}")

if __name__ == "__main__":
    print("Bot is running...")
    bot.polling()

