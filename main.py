import telebot
from telebot.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, InputFile
import requests
import time
from datetime import datetime
from csv_manage import initialize_csv, get_user_data, update_user_data, save_payment_to_csv
from parce_uzs_rate import get_uzs_rate, round_uzs
import os
import csv

# Replace 'YOUR_BOT_API_KEY' with your actual bot API key from Telegram
BOT_API_KEY = '7647257231:AAEl9Su4QPemk8D1iUe0SImL3ct-kDOiWGs'
HUMANIZATION_API_KEY = 'aa3fcf01cb0547d1bfa8de83134156f5'
HUMANIZATION_ENDPOINT_SUBMIT = 'https://bypass.hix.ai/api/hixbypass/v1/submit'
HUMANIZATION_ENDPOINT_OBTAIN = 'https://bypass.hix.ai/api/hixbypass/v1/obtain'

DEVELOPERS_ID = [7514237434, 7088907990, 1927099919]
bot = telebot.TeleBot(BOT_API_KEY)

# Получаем текущий курс
UZS_RATE = get_uzs_rate()

PACKAGES = [
    {"id": 1, "words": 2000, "price_usd": 5, "price_uzs": round_uzs(5 * UZS_RATE)},
    {"id": 2, "words": 4000, "price_usd": 7, "price_uzs": round_uzs(7 * UZS_RATE)},
    {"id": 3, "words": 10000, "price_usd": 10, "price_uzs": round_uzs(10 * UZS_RATE)}, 
    {"id": 4, "words": 20000, "price_usd": 16, "price_uzs": round_uzs(16 * UZS_RATE)},
    {"id": 5, "words": 50000, "price_usd": 35, "price_uzs": round_uzs(35 * UZS_RATE)}
]

CHANNEL_ID = '2459567258'  # Replace with your actual channel ID

def send_action_to_channel(action_message):
    """Send a message to the specified channel."""
    bot.send_message(CHANNEL_ID, action_message)

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
            bot.send_message(message.chat.id, "Invalid command format. Use: /pornhub <user_id> <amount>")
            return

        target_user_id = int(command_args[1])
        amount = int(command_args[2])

        user_data = get_user_data(target_user_id)
        if not user_data:
            bot.send_message(message.chat.id, "User not found.")
            return

        current_balance = int(user_data['balance'])
        update_user_data(target_user_id, balance=current_balance + amount)

        # Сохранение данных в CSV файл
        with open('balance_updates.csv', mode='a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['user_id', 'units', 'datetime'])  # Добавление названий столбцов
            writer.writerow([target_user_id, amount, datetime.now().strftime("%d/%m/%Y %H:%M")])

        bot.send_message(message.chat.id, f"Successfully added {amount} words to user {target_user_id}'s balance.")
        
        # Send action to channel
        send_action_to_channel(f"Added {amount} words to user {target_user_id}'s balance by {user_id}.")
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

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Top up", callback_data="show_packages"))

    bot.send_message(
        message.chat.id,
        f"Your balance details:\nTrial Balance: {trial_balance} words\nBalance: {balance} words",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "show_packages")
def show_packages(call):
    markup = InlineKeyboardMarkup()
    packages_text = "Choose a package to top up:\n\n"
    
    for pkg in PACKAGES:
        packages_text += f"{pkg['id']}. {pkg['words']:,} words ${pkg['price_usd']} = {pkg['price_uzs']:,} UZS\n"
        markup.add(InlineKeyboardButton(f"Package {pkg['id']}", callback_data=f"package_{pkg['id']}"))

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=packages_text,
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("package_"))
def handle_package_selection(call):
    package_id = int(call.data.split("_")[1])
    package = next((pkg for pkg in PACKAGES if pkg["id"] == package_id), None)
    
    if not package:
        return

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Proof the payment", callback_data=f"proof_{package_id}"))

    payment_info = (
        f"You selected Package {package['id']}:\n"
        f"• {package['words']:,} words\n"
        f"• ${package['price_usd']}\n"
        f"• {package['price_uzs']:,} UZS\n\n"
        f"Please send payment to:\n"
        f"Card number: XXXX XXXX XXXX XXXX\n"
        f"Card holder: NAME SURNAME\n\n"
        f"After payment, click the button below to submit your proof."
    )

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=payment_info,
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("proof_"))
def request_payment_proof(call):
    package_id = int(call.data.split("_")[1])
    bot.send_message(call.message.chat.id, "Please send a photo of your payment proof.")
    bot.register_next_step_handler(call.message, lambda m: handle_payment_proof(m, package_id))

def handle_payment_proof(message: Message, package_id: int):
    if not message.photo:
        bot.send_message(message.chat.id, "Please send a photo of your payment proof.")
        return

    package = next((pkg for pkg in PACKAGES if pkg["id"] == package_id), None)
    if not package:
        return

    # Notify all developers
    ticket_id, current_time = save_payment_to_csv(message, package)

    proof_info = (
        f"🔔 New payment proof received!\n\n"
        f"🧾 Ticket ID          {ticket_id}\n"
        f"👤 User ID            {message.from_user.id}\n"
        f"📝 Username      @{message.from_user.username}\n"
        f"📦 Package           {package['id']}\n"
        f"💰 Amount           ${package['price_usd']} ({package['price_uzs']:,} UZS)\n"
        f"📝 Words              {package['words']:,}\n"
        f"⏳ Status              in progress\n"
        f"📅 Date                 {current_time}\n\n"
        f"If something seems incorrect, you can contact the admin at @admin."
    )

    photo = message.photo[-1]
    for dev_id in DEVELOPERS_ID:
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("Accept", callback_data=f"accept_{ticket_id}"),
            InlineKeyboardButton("Decline", callback_data=f"decline_{ticket_id}")
        )
        bot.send_photo(dev_id, photo.file_id, caption=proof_info, reply_markup=markup)

    bot.reply_to(
        message,
        "Thank you! Your payment proof has been submitted and is being reviewed. "
        "Your balance will be updated once the payment is confirmed."
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("accept_") or call.data.startswith("decline_"))
def handle_payment_decision(call):
    # Если это callback для причины отклонения, передаем его другому обработчику
    if any(call.data.startswith(f"decline_{reason}_") for reason in ["amount", "received", "proof"]):
        handle_decline_reason(call)
        return

    parts = call.data.split("_", 1)
    if len(parts) != 2:
        bot.send_message(call.message.chat.id, "Invalid data format.")
        return

    action, ticket_id = parts
    try:
        ticket_id = int(ticket_id)
    except ValueError:
        bot.send_message(call.message.chat.id, "Invalid ticket ID format.")
        return

    # Read the balance_top_up.csv to find the ticket
    with open('balance_top_up.csv', mode='r', newline='') as file:
        reader = csv.DictReader(file)
        rows = list(reader)  # Сначала сохраняем строки
        ticket = next((row for row in rows if int(row['ticket_id']) == ticket_id), None)
        if ticket:
            user_id = int(ticket['user_id'])
        else:
            bot.send_message(call.message.chat.id, "Ticket not found.")
            return

    if action == "accept":
        # Update user balance
        words = int(ticket['words'])
        user_data = get_user_data(user_id)
        if user_data:
            new_balance = int(user_data['balance']) + words
            update_user_data(user_id, balance=new_balance)

        # Update ticket status
        ticket['status'] = 'accepted'
        bot.send_message(user_id, f"Your payment has been accepted. {words} words have been added to your balance.\nIf something seems incorrect, you can contact the admin at @admin.")
    elif action == "decline":
        # Update ticket status
        ticket['status'] = 'declined'

        # Create reply markup with buttons for decline reasons
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("Payment incorrect amount", callback_data=f"decline_amount_{ticket_id}"),
            InlineKeyboardButton("Payment not received", callback_data=f"decline_received_{ticket_id}"),
            InlineKeyboardButton("Proof issue", callback_data=f"decline_proof_{ticket_id}")
        )
        # Send the markup to the admin
        bot.send_message(call.message.chat.id, "Select the reason for declining the payment:", reply_markup=markup)

        # Send action to channel
        send_action_to_channel(f"Ticket {ticket_id} accepted. {words} words added to user {user_id}'s balance.")

    # Write back the updated rows to the CSV
    with open('balance_top_up.csv', mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=reader.fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    bot.send_message(call.message.chat.id, f"Ticket {ticket_id} has been {ticket['status']}.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("decline_amount_") or call.data.startswith("decline_received_") or call.data.startswith("decline_proof_"))
def handle_decline_reason(call):
    parts = call.data.split("_", 2)
    if len(parts) != 3:
        bot.send_message(call.message.chat.id, "Invalid data format.")
        return

    action, reason, ticket_id = parts
    ticket_id = int(ticket_id)
    admin_id = call.message.chat.id

    # Найти user_id из CSV по ticket_id
    with open('balance_top_up.csv', mode='r', newline='') as file:
        reader = csv.DictReader(file)
        rows = list(reader)  # Сначала сохраняем строки
        ticket = next((row for row in rows if int(row['ticket_id']) == ticket_id), None)
        if ticket:
            user_id = int(ticket['user_id'])
        else:
            bot.send_message(admin_id, "Ticket not found.")
            return

    # Сообщения для пользователя
    if reason == "amount":
        decline_message = "Your payment was declined due to incorrect amount. Please try again with the correct amount.\n\nIf you think this is a mistake, please contact the admin at @admin."
    elif reason == "received":
        decline_message = "Your payment was declined because it was not received. Please ensure the payment was sent correctly.\n\nIf you think this is a mistake, please contact the admin at @admin."
    elif reason == "proof":
        decline_message = "Your payment was declined due to an issue with the proof provided. Please send a clearer proof of payment.\n\nIf you think this is a mistake, please contact the admin at @admin."

    # Отправить сообщение пользователю
    bot.send_message(user_id, decline_message)

    # Обновить сообщение для админа, убрав кнопки
    bot.edit_message_reply_markup(
        chat_id=admin_id,
        message_id=call.message.message_id,
        reply_markup=None
    )
    
    # Подтверждение для админа
    bot.answer_callback_query(
        call.id,
        text=f"Decline reason sent to user. Reason: {reason}"
    )

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
        submit_response = True #requests.post(HUMANIZATION_ENDPOINT_SUBMIT, json=submit_payload, headers=headers)

        if True: #submit_response.status_code == 200
            submit_data = {"err_code": 0,
                            "err_msg": "string",
                            "data": {
                                "task_id": "string"
                            }
                        } #submit_response.json()
        
            if submit_data.get("err_code") == 0:
                task_id = submit_data["data"]["task_id"]

                # Simulate loading with typing action
                bot.send_chat_action(message.chat.id, 'typing')
                for i in range(3):
                    time.sleep(1)
                    bot.send_message(message.chat.id, f"Processing... ({i + 1}/3)")

                # Step 2: Obtain the humanized text using the task_id
                obtain_response = True #requests.get(HUMANIZATION_ENDPOINT_OBTAIN, params={"task_id": task_id}, headers=headers)

                if True: #obtain_response.status_code == 200
                    obtain_data = {
                                    "err_code": 0,
                                    "err_msg": "Success",
                                    "data": {
                                        "input": "How to Give a Great Gift to Someone\n\n\nChoosing the perfect gift for someone can be a delightful experience when you consider their preferences and interests. Here's a guide on how to give a great gift that will be appreciated and cherished:\n\n\n1. Know the Recipient: Take the time to understand the person you're buying for. Consider their hobbies, interests, and personality. What makes them happy?\n\n\n2. Listen and Observe: Pay attention to any hints or mentions of things they want or need. Sometimes, people drop subtle hints about what they'd like as a gift.\n\n\n3. Consider Practicality: A useful gift can be just as thoughtful as a sentimental one. Think about what would make the recipient's life easier or more enjoyable.",
                                        "input_words": 122,
                                        "task_id": "2c451bac-c5ea-4e77-a21a-23ebc14ba47f",
                                        "words_used": 97,
                                        "output": "How to Give a Great Gift to Someone\n\nChoosing the perfect present for another requires deep reflection on their passions and pursuits. A guide for bestowing a gift certain to be cherished:\n\n1. Fathoming the recipient entails comprehending their diversions, interests, and persona. What lifts their spirit? \n\n2. Heed hints and allusions to objects they covet or necessities they require, whether oblique or overt. Subtle signposts sometimes indicate coveted offerings.\n\n3. Pondering usefulness alongside sentiment, a present easing life or amplifying joy merits equal thought. Consider how your selection may delight through facilitating pleasure or alleviating burden.",
                                        "subtask_status": "completed",
                                        "task_status": True,
                                        "detection_result": "human",
                                        "detection_score": 100,
                                        "mode": "Fast"
                                    }
                                } #obtain_response.json()
                    if obtain_data.get("err_code") == 0 or True:
                        humanized_text = obtain_data["data"]["output"]
                        words_used = int(obtain_data["data"]["words_used"])

                        bot.reply_to(message, f"Humanized text (Mode: {user_mode}):\n\n{humanized_text}")

                        # Deduct words used from trial balance first, then balance
                        try:
                            if trial_balance >= words_used:
                                update_user_data(user_id, trial_balance=trial_balance - words_used)
                            elif trial_balance + balance >= words_used:
                                remaining_words = words_used - trial_balance
                                update_user_data(user_id, trial_balance=0, balance=balance - remaining_words)
                            else:
                                bot.send_message(message.chat.id, "You have insufficient balance. Please top up your balance.")
                                return
                        except Exception as e:
                            error_message = f"An error occurred: {str(e)}. Errored user: {message.chat.id}"
                            for dev_id in DEVELOPERS_ID:
                                bot.send_message(dev_id, error_message)
                            bot.send_message(message.chat.id, "An error occurred. The issue has been reported to the admin.")
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

@bot.message_handler(commands=['send_csv'])
def send_csv_files(message: Message):
    user_id = message.chat.id

    if user_id not in DEVELOPERS_ID:
        bot.send_message(user_id, "You are not authorized to use this command.")
        return

    csv_directory = '.'  # Current directory
    csv_files = [f for f in os.listdir(csv_directory) if f.endswith('.csv')]

    if not csv_files:
        bot.send_message(user_id, "No CSV files available.")
        return

    for csv_file in csv_files:
        with open(csv_file, 'rb') as file:
            bot.send_document(user_id, file, visible_file_name=csv_file)

    bot.send_message(user_id, "All CSV files have been sent.")

if __name__ == "__main__":
    initialize_csv()
    print("Bot is running...")
    bot.polling()