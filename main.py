import telebot
from telebot.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, InputFile
import requests
from datetime import datetime
import time
from csv_manage import initialize_csv, get_user_data, update_user_data, save_payment_to_csv, handle_payment_decision_to_csv, balance_updates_to_csv, get_username, initialize_ticket_data_csv
from parce_uzs_rate import get_uzs_rate, round_uzs
import os
import csv
import random

# Replace 'YOUR_BOT_API_KEY' with your actual bot API key from Telegram
BOT_API_KEY = '7716546162:AAFtHSmcoxiYyqvhArRjghaZbqIzbH85lnM'
HUMANIZATION_API_KEY = 'aa3fcf01cb0547d1bfa8de83134156f5'
HUMANIZATION_ENDPOINT_SUBMIT = 'https://bypass.hix.ai/api/hixbypass/v1/submit'
HUMANIZATION_ENDPOINT_OBTAIN = 'https://bypass.hix.ai/api/hixbypass/v1/obtain'

user_mode = "Latest"
DEVELOPERS_ID = [7514237434, 7088907990, 1927099919]
bot = telebot.TeleBot(BOT_API_KEY)

# Получаем текущий курс
UZS_RATE = get_uzs_rate()

PACKAGES = [
    {"id": 1, "words": 2000, "price_usd": 3, "price_uzs": round_uzs(3 * UZS_RATE)},
    {"id": 2, "words": 4000, "price_usd": 5, "price_uzs": round_uzs(5 * UZS_RATE)},
    {"id": 3, "words": 10000, "price_usd": 10, "price_uzs": round_uzs(10 * UZS_RATE)}, 
    {"id": 4, "words": 15000, "price_usd": 13, "price_uzs": round_uzs(13 * UZS_RATE)},
    {"id": 5, "words": 25000, "price_usd": 20, "price_uzs": round_uzs(20 * UZS_RATE)}
]

CHANNEL_ID = '-1002459567258'  # Replace with your actual channel link

PENDING_PROOFS = {}  # Store message IDs for pending proofs: {ticket_id: {dev_id: message_id}}

bot_data = {}

def send_action_to_channel(action_message):
    """Send a message to the specified channel."""
    bot.send_message(CHANNEL_ID, action_message)


@bot.message_handler(commands=['start'])
def send_welcome(message: Message):
    user_id = message.chat.id
    if not get_user_data(user_id):
        update_user_data(user_id, trial_balance=200, balance=0)  # Give 200 words trial by default

    # Create reply markup with buttons
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        KeyboardButton('Humanize 🤖➡️👤'),
        KeyboardButton('Balance 💰'),
        KeyboardButton('Top up history 📜')
    )

    bot.send_message(
        message.chat.id,
        "👋 **Welcome to HumanizeBot!**\n\n"
        "🎯 I can help you humanize text to bypass AI detection.\n\n"
        "🔽 Use the buttons below to:\n"
        "• **Humanize your text** 🤖➡️👤\n"
        "• **Check your balance** 💰\n"
        "• **View top-up history** 📜",
        reply_markup=markup,
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['pornhub'])
def add_balance(message: Message):
    user_id = message.chat.id
    user_username = message.from_user.username or "No username"

    if user_id not in DEVELOPERS_ID:
        bot.send_message(message.chat.id, "You are not authorized to use this command.")
        send_action_to_channel(f"Unauthorized access attempt to /pornhub command by user {user_id} (@{user_username})")
        return

    try:
        command_args = message.text.split()
        if len(command_args) != 3:
            bot.send_message(message.chat.id, "Invalid command format. Use: /pornhub <user_id> <amount>")
            send_action_to_channel(f"Invalid command format used by admin {user_id} ({user_username})")
            return

        target_user_id = int(command_args[1])
        amount = int(command_args[2])

        user_data = get_user_data(target_user_id)
        if not user_data:
            bot.send_message(message.chat.id, "User not found.")
            send_action_to_channel(f"Admin {user_id} ({user_username}) attempted to add balance for non-existent user {target_user_id}")
            return

        current_balance = int(user_data['balance'])
        new_balance = current_balance + amount
        update_user_data(target_user_id, balance=new_balance)

        datetime_now = datetime.now().strftime("%d/%m/%Y %H:%M")
        balance_updates_to_csv(target_user_id, amount, datetime_now)

        bot.send_message(
            message.chat.id,
            f"✅ Successfully added {amount} words to user {target_user_id}'s balance.",
            parse_mode='Markdown'
        )
        
        # Send action to channel
        target_username = get_username(target_user_id)
        send_action_to_channel(f"✅\n /pornhub were been used and\n {amount} words added to: \n\nUSER_ID: #{target_user_id} \nUSERNAME: {target_username} \nNEW BALANCE: {new_balance} words.")
    except ValueError:
        bot.send_message(message.chat.id, "Invalid input. Ensure user_id and amount are integers.")
        send_action_to_channel(f"‼️Admin {user_id} ({user_username}) provided invalid input for /pornhub command")
    except Exception as e:
        error_msg = f"‼️An error occurred: {str(e)}"
        bot.send_message(message.chat.id, error_msg)
        send_action_to_channel(f"‼️Error in /pornhub command by admin {user_id} ({user_username}): {error_msg}")


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
        f"💼 **Your balance details:**\n"
        f"🔹 **Trial Balance:** {trial_balance} words\n"
        f"🔹 **Balance:** {balance} words",
        reply_markup=markup,
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda call: call.data == "show_packages")
def show_packages(call):
    markup = InlineKeyboardMarkup()
    packages_text = "✨ **Select Your Perfect Package** ✨\n\n"
    
    package_names = {
        1: "🌱 Starter Pack",
        2: "🌿 Saving Pack", 
        3: "🌳 Pro Pack",
        4: "🌺 Premium Pack",
        5: "👑 Royal Pack"
    }
    
    buttons = []
    for pkg in PACKAGES:
        pkg_name = package_names[pkg['id']]
        packages_text += f"{pkg_name}\n"
        packages_text += f"      | {pkg['words']:,} words\n"
        packages_text += f"      | ${pkg['price_usd']} = {pkg['price_uzs']:,} UZS\n\n"
        
        button_text = f" {pkg_name}"
        buttons.append(InlineKeyboardButton(button_text, callback_data=f"package_{pkg['id']}"))
    
    # Add buttons one per row
    for button in buttons:
        markup.row(button)

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=packages_text,
        reply_markup=markup,
        parse_mode='Markdown'
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
        f"🎉 **Package {package['id']} Selected!**\n\n"
        f"📦 **Package Details:**\n"
        f"✨ {package['words']:,} words\n"
        f"💵 ${package['price_usd']}\n"
        f"💰 {package['price_uzs']:,} UZS\n\n"
        f"💳 **Payment Details:**\n"
        f"Card: XXXX XXXX XXXX XXXX\n"
        f"Name: NAME SURNAME\n\n"
        f"✅ Click the button below after payment\n"
        f"    to submit your proof!"
    )

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=payment_info,
        reply_markup=markup,
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("proof_"))
def request_payment_proof(call):
    package_id = int(call.data.split("_")[1])
    bot.send_message(
        call.message.chat.id,
        "📸 Please send a photo of your payment proof.",
        parse_mode='Markdown'
    )
    bot.register_next_step_handler(call.message, lambda m: handle_payment_proof(m, package_id))

def handle_payment_proof(message: Message, package_id: int):
    if not message.photo:
        bot.send_message(message.chat.id, "Please send a photo of your payment proof.")
        bot.register_next_step_handler(message, lambda m: handle_payment_proof(m, package_id))
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
    )

    photo = message.photo[-1]
    dev_messages = {}  # Store message IDs for each developer
    
    for dev_id in DEVELOPERS_ID:
        try:
            markup = InlineKeyboardMarkup()
            markup.add(
                InlineKeyboardButton("Accept", callback_data=f"accept_{ticket_id}_{dev_id}"),
                InlineKeyboardButton("Decline", callback_data=f"decline_{ticket_id}_{dev_id}")
            )
            sent_msg = bot.send_photo(dev_id, photo.file_id, caption=proof_info, reply_markup=markup)
            dev_messages[dev_id] = sent_msg.message_id
        except Exception as e:
            print(f"Failed to send proof to developer {dev_id}: {str(e)}")
            continue  # Skip to next developer if sending fails

    # Only store if we have any successful messages
    if dev_messages:
        PENDING_PROOFS[ticket_id] = dev_messages

    bot.reply_to(
        message,
        f"🧾 Ticket ID          {ticket_id}\n"
        f"👤 User ID            {message.from_user.id}\n"
        f"📝 Username      @{message.from_user.username}\n"
        f"📦 Package           {package['id']}\n"
        f"💰 Amount           ${package['price_usd']} ({package['price_uzs']:,} UZS)\n"
        f"📝 Words              {package['words']:,}\n"
        f"⏳ Status              in progress\n"
        f"📅 Date                 {current_time}\n\n"
        "\nThank you! Your payment proof has been submitted and is being reviewed. "
        "Your balance will be updated once the payment is confirmed by moderators."
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("accept_") or call.data.startswith("decline_"))
def handle_payment_decision(call):
    # Skip if it's a decline reason callback
    if any(call.data.startswith(f"decline_{reason}_") for reason in ["amount", "received", "proof"]):
        handle_decline_reason(call)
        return

    parts = call.data.split("_")
    if len(parts) != 3:
        bot.send_message(call.message.chat.id, "Invalid data format.")
        return

    action, ticket_id, dev_id = parts
    try:
        ticket_id = int(ticket_id)
        dev_id = int(dev_id)
    except ValueError:
        bot.send_message(call.message.chat.id, "Invalid format.")
        return

    # Read ticket data from CSV
    with open('ticket_data.csv', mode='r', newline='') as file:
        reader = csv.DictReader(file)
        rows = list(reader)
        ticket = next((row for row in rows if int(row['ticket_id']) == ticket_id), None)
        if not ticket:
            bot.send_message(call.message.chat.id, "Ticket not found.")
            return
        
        user_id = int(ticket['user_id'])

    # Get message IDs from global variable
    dev_messages = PENDING_PROOFS.get(ticket_id)
    if not dev_messages:
        bot.send_message(call.message.chat.id, "Ticket not found or already processed.")
        return

    if action == "accept":
        words = int(ticket['words'])
        user_data = get_user_data(user_id)
        if user_data:
            new_balance = int(user_data['balance']) + words
            update_user_data(user_id, balance=new_balance)
            
            # Send notifications
            bot.send_message(user_id, f"✅\nYour payment has been accepted. {words} words have been added to your balance. \n\n🎉   Your new balance is {new_balance} words.")
            send_action_to_channel(
                f"✅ Ticket Accepted\n\n"
                f"🧾 Ticket ID: {ticket_id}\n"
                f"👤 User ID: {user_id}\n"
                f"📝 Username: {ticket['username']}\n"
                f"📦 Package: {ticket['package']}\n"
                f"💰 Amount: ${ticket['amount_usd']} ({ticket['amount_uzs']} UZS)\n"
                f"📝 Words: {ticket['words']}\n"
                f"⏳ Status: accepted\n"
                f"📅 Date: {ticket['date']}\n"
                f"🎉 New Balance: {new_balance} words"
            )

            # Delete messages from all developers and clean up
            for dev_id, message_id in dev_messages.items():
                try:
                    bot.delete_message(dev_id, message_id)
                except Exception as e:
                    print(f"Failed to delete message {message_id} for developer {dev_id}: {str(e)}")
            
            del PENDING_PROOFS[ticket_id]

            # Update the status in the ticket_data.csv
            for row in rows:
                if int(row['ticket_id']) == ticket_id:
                    row['status'] = 'accepted'
                    break

            # Save the updated rows back to the CSV
            handle_payment_decision_to_csv('ticket_data.csv', rows, reader.fieldnames)

    elif action == "decline":
        ticket['status'] = 'declined'
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("Payment incorrect amount", callback_data=f"decline_amount_{ticket_id}"),
            InlineKeyboardButton("Payment not received", callback_data=f"decline_received_{ticket_id}"),
            InlineKeyboardButton("Proof issue", callback_data=f"decline_proof_{ticket_id}")
        )
        bot.edit_message_reply_markup(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=markup
        )

    handle_payment_decision_to_csv('ticket_data.csv', rows, reader.fieldnames)

@bot.callback_query_handler(func=lambda call: call.data.startswith("decline_amount_") or call.data.startswith("decline_received_") or call.data.startswith("decline_proof_"))
def handle_decline_reason(call):
    parts = call.data.split("_", 2)
    if len(parts) != 3:
        bot.send_message(call.message.chat.id, "Invalid data format.")
        return

    action, reason, ticket_id = parts
    ticket_id = int(ticket_id)
    admin_id = call.message.chat.id

    # Find user_id from CSV by ticket_id
    with open('ticket_data.csv', mode='r', newline='') as file:
        reader = csv.DictReader(file)
        rows = list(reader)
        ticket = next((row for row in rows if int(row['ticket_id']) == ticket_id), None)
        if ticket:
            user_id = int(ticket['user_id'])
        else:
            bot.send_message(admin_id, "Ticket not found.")
            return

    # Messages for user
    if reason == "amount":
        decline_message = f"‼️\nYour ticket: {ticket_id} request to top-up was declined due to the payment amount incorrect.\n\nIf you think this is a mistake, please contact the admin at @admin.\n\n\nSorry for the inconvenience."
    elif reason == "received": 
        decline_message = f"‼️\nYour ticket: {ticket_id} request to top-up was declined because the payment was not received. Please ensure the payment was sent correctly.\n\nIf you think this is a mistake, please contact the admin at @admin.\n\n\nSorry for the inconvenience."
    elif reason == "proof":
        decline_message = f"‼️\nYour ticket: {ticket_id} request to top-up was declined due to an issue with the proof provided in the screenshot of the payment. Please send a clearer proof of payment.\n\nIf you think this is a mistake, please contact the admin at @admin.\n\n\nSorry for the inconvenience."

    # Send message to user
    bot.send_message(user_id, decline_message)
    
    # Update admin's message caption instead of text
    bot.edit_message_caption(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        caption=f"‼️\nTicket {ticket_id} has been declined."
    )
    
    # Confirmation for admin
    bot.answer_callback_query(
        call.id,
        text=f"Decline reason sent to user. Reason: {reason}"
    )

    if reason == "proof":
        reason = "Proof issue"
    elif reason == "received":
        reason = "Payment not received"
    elif reason == "amount":
        reason = "Payment incorrect amount"

    # Send detailed ticket info to channel with reason
    send_action_to_channel(
        f"‼️ Ticket Declined\n\n"
        f"🧾 Ticket ID: {ticket_id}\n"
        f"👤 User ID: {user_id}\n"
        f"📝 Username: {ticket['username']}\n"
        f"📦 Package: {ticket['package']}\n"
        f"💰 Amount: ${ticket['amount_usd']} ({ticket['amount_uzs']} UZS)\n"
        f"📝 Words: {ticket['words']}\n"
        f"⏳ Status: declined\n"
        f"📅 Date: {ticket['date']}\n"
        f"❌ Reason: {reason}"
    )

    # Delete messages and clean up after declining
    dev_messages = PENDING_PROOFS.get(ticket_id)
    if dev_messages:
        for dev_id, message_id in dev_messages.items():
            try:
                bot.delete_message(dev_id, message_id)
            except Exception as e:
                print(f"Failed to delete message {message_id} for developer {dev_id}: {str(e)}")
        
        # Clean up the stored message IDs
        del PENDING_PROOFS[ticket_id]

@bot.message_handler(func=lambda message: message.text == 'Humanize 🤖➡️👤')
def prompt_humanize(message: Message):
    bot.send_message(
        message.chat.id,
        "📝 Send me the text you'd like to humanize. You can send multiple messages. Tap 'Done' when you're finished.",
        parse_mode='Markdown'
    )
    
    # Initialize a session to collect text
    user_id = message.chat.id
    bot_data[user_id] = {"text": "", "collecting": True}

    # Create reply markup with "Done" and "Cancel" buttons
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(KeyboardButton('Done'), KeyboardButton('Cancel'))
    bot.send_message(message.chat.id, "Waiting for your text...", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == 'Cancel')
def cancel_text_collection(message: Message):
    user_id = message.chat.id
    if user_id in bot_data:
        bot_data[user_id]["collecting"] = False
        bot_data[user_id]["text"] = ""  # Clear any collected text
        bot.send_message(message.chat.id, "Text collection has been canceled.", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True, row_width=2).add(
            KeyboardButton('Humanize 🤖➡️👤'),
            KeyboardButton('Balance 💰'),
            KeyboardButton('Top up history 📜')
        ))

@bot.message_handler(func=lambda message: message.text == 'Done')
def finish_text_collection(message: Message):
    user_id = message.chat.id
    if user_id in bot_data and bot_data[user_id]["collecting"]:
        bot_data[user_id]["collecting"] = False
        collected_text = bot_data[user_id]["text"]
        
        # Check if the collected text contains at least 100 words
        if len(collected_text.split()) < 100:
            bot.send_message(message.chat.id, "The input text must contain at least 100 words. Please continue sending your text.")
            bot_data[user_id]["collecting"] = True  # Allow user to continue sending text
            return
        
        # Proceed to humanize the collected text
        humanize_text(message, collected_text)
    else:
        bot.send_message(message.chat.id, "No text collected. Please start again.")

@bot.message_handler(func=lambda message: message.chat.id in bot_data and bot_data[message.chat.id]["collecting"])
def collect_text(message: Message):
    user_id = message.chat.id
    if user_id in bot_data:
        bot_data[user_id]["text"] += " " + message.text
        
        # Calculate the current word count
        word_count = len(bot_data[user_id]["text"].split())
        
        # Notify the user that the text has been saved and show the word count
        bot.send_message(
            message.chat.id,
            f"📝 Your text has been saved. Current word count: {word_count}. You can continue sending messages or tap 'Done' when finished.",
            parse_mode='Markdown'
        )

def humanize_text(message: Message, text: str):
    user_id = message.chat.id
    user_data = get_user_data(user_id)

    if not user_data:
        bot.send_message(message.chat.id, "Please use /start to register first.")
        return

    trial_balance = int(user_data['trial_balance'])
    balance = int(user_data['balance'])

    total_balance = trial_balance + balance
    required_words = len(text.split())

    if total_balance <= 0:
        bot.send_message(message.chat.id, "You have no remaining trials or balance. Please contact support for more access.")
        return

    if required_words > total_balance:
        bot.send_message(
            message.chat.id, 
            f"You need {required_words} words but only have {total_balance} words available in your balance. Please top up or contact support for more access.",
            reply_markup=ReplyKeyboardMarkup(resize_keyboard=True, row_width=2).add(
                KeyboardButton('Humanize 🤖➡️👤'),
                KeyboardButton('Balance 💰'),
                KeyboardButton('Top up history 📜')
            )
        )
        return

    if len(text.split()) < 100:
        bot.send_message(message.chat.id, "The input text must contain at least 100 words.")
        return

    try:
        # Submit the humanization task
        task_id = submit_humanization_task(text, user_mode)
        if not task_id:
            bot.send_message(
                message.chat.id, 
                "🔧 Oops! We've encountered a small hiccup in our text processing system. Our developers have been notified and are already working their magic to fix it! ✨\n\n🙏 Please try again in a few moments. We appreciate your patience! 🌟",
                reply_markup=ReplyKeyboardMarkup(resize_keyboard=True, row_width=2).add(
                    KeyboardButton('Humanize 🤖➡️👤'),
                    KeyboardButton('Balance 💰'),
                    KeyboardButton('Top up history 📜')
                )
            )
            return
        status_message = bot.send_message(message.chat.id, "🔄 Your text is being humanized. Please wait...", parse_mode='Markdown')

        # Simulate loading with periodic updates
        loading_messages = [
            "Processing your text... 🔄",
            "Analyzing text patterns 📊",
            "Enhancing readability ✨",
            "Optimizing word choices 📝",
            "Refining sentence structure 🔄",
            "Improving flow and rhythm 🎵",
            "Adding human touch 🎯",
            "Polishing the content ✨",
            "Making it shine ✨",
            "Finalizing edits ✏️"
        ]
        
        # duration
        loading_duration = 10  # Adjust this duration as needed
        
        # Simulate typing and change messages
        for i in range(loading_duration+1):
            bot.send_chat_action(message.chat.id, 'typing')
            try:
                bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=status_message.message_id,  # Use the status message ID
                    text=f"{loading_messages[i % len(loading_messages)]} {i}/{loading_duration}"
                )
            except Exception as e:
                print(f"Failed to edit message: {e}")
            time.sleep(1)  # Ensure this line is not commented out

        # Obtain the humanized text
        humanized_text = obtain_humanized_text(task_id)

        bot.reply_to(message, f"Humanized text (Mode: {user_mode}):\n\n{humanized_text}")

        # Deduct words used from trial balance first, then balance
        words_used = len(humanized_text.split())
        if trial_balance >= words_used:
            update_user_data(user_id, trial_balance=trial_balance - words_used)
        elif trial_balance + balance >= words_used:
            remaining_words = words_used - trial_balance
            update_user_data(user_id, trial_balance=0, balance=balance - remaining_words)
        else:
            bot.send_message(message.chat.id, "You have insufficient balance. Please top up your balance.")
            return

        # Add main menu reply markup
        main_menu_markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        main_menu_markup.add(
            KeyboardButton('Humanize 🤖➡️👤'),
            KeyboardButton('Balance 💰'),
            KeyboardButton('Top up history 📜')
        )
        bot.send_message(message.chat.id, "Main menu:", reply_markup=main_menu_markup)

    except Exception as e:
        for dev_id in DEVELOPERS_ID:
            bot.send_message(dev_id, f"An error occurred: {str(e)}. Errored user: {message.chat.id}")

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

    bot.send_message(
        user_id,
        "📂 All CSV files have been sent.",
        parse_mode='Markdown'
    )

@bot.message_handler(func=lambda message: message.text == 'Balance 💰')
def show_top_up_history(message: Message):
    user_id = message.chat.id
    user_data = get_user_data(user_id)

    if not user_data:
        bot.send_message(message.chat.id, "Please use /start to register first.")
        return

    # Read the top-up history from the ticket_data.csv
    history = []
    try:
        with open('ticket_data.csv', mode='r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if int(row['user_id']) == user_id and row['status'] == 'accepted':
                    history.append(f"Package: {row['package']}, Amount: ${row['amount_usd']} ({row['amount_uzs']} UZS), Date: {row['date']}")
    except FileNotFoundError:
        bot.send_message(message.chat.id, "No top-up history found.")
        return

    if not history:
        bot.send_message(message.chat.id, "No top-up history found.")
    else:
        history_text = "\n".join(history)
        bot.send_message(message.chat.id, f"Your top-up history:\n{history_text}")

@bot.message_handler(func=lambda message: message.text == 'Top up history 📜')
def show_all_tickets(message: Message):
    user_id = message.chat.id
    user_data = get_user_data(user_id)

    if not user_data:
        bot.send_message(message.chat.id, "Please use /start to register first.")
        return

    # Read all tickets from the ticket_data.csv
    tickets = []
    try:
        with open('ticket_data.csv', mode='r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if int(row['user_id']) == user_id:
                    ticket_info = (
                        f"🧾 Ticket ID: {row['ticket_id']}\n"
                        f"👤 User ID: {row['user_id']}\n"
                        f"📝 Username: {row['username']}\n"
                        f"📦 Package: {row['package']}\n"
                        f"💰 Amount: ${row['amount_usd']} ({row['amount_uzs']} UZS)\n"
                        f"📝 Words: {row['words']}\n"
                        f"⏳ Status: {row['status']}\n"
                        f"📅 Date: {row['date']}\n"
                        "----------------------------------------"
                    )
                    tickets.append(ticket_info)
    except FileNotFoundError:
        bot.send_message(message.chat.id, "No ticket history found.")
        return

    if not tickets:
        bot.send_message(message.chat.id, "No ticket history found.")
    else:
        tickets_text = "\n\n".join(tickets)
        try:
            bot.send_message(
                message.chat.id,
                f"📜 Your ticket history:\n\n{tickets_text}",
                parse_mode='Markdown'
            )
        except Exception as e:
            # Fallback without markdown if parsing fails
            bot.send_message(
                message.chat.id,
                f"📜 Your ticket history:\n\n{tickets_text.replace('*', '')}"
            )

def submit_humanization_task(text, mode):
    url = HUMANIZATION_ENDPOINT_SUBMIT
    headers = {
        'api-key': HUMANIZATION_API_KEY,
        'Content-Type': 'application/json'
    }
    data = {
        'input': text,
        'mode': mode
    }
    response = requests.post(url, headers=headers, json=data)
    print(response.json())
    if response.status_code == 200:
        result = response.json()
        if result['err_code'] == 0:
            return result['data']['task_id']
        else:
            for dev_id in DEVELOPERS_ID:
                bot.send_message(dev_id, f"Error in submission: {result['err_msg']}")
            return False
    else:
        for dev_id in DEVELOPERS_ID:
            bot.send_message(dev_id, f"Failed to submit task: {response.status_code}")
        return False

def obtain_humanized_text(task_id):
    url = HUMANIZATION_ENDPOINT_OBTAIN
    headers = {
        'api-key': HUMANIZATION_API_KEY
    }
    params = {
        'task_id': task_id
    }
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        result = response.json()
        if result['err_code'] == 0:
            return result['data']['output']
        else:
            raise Exception(f"Error in obtaining result: {result['err_msg']}")
    else:
        raise Exception(f"Failed to obtain task result: {response.status_code}")

if __name__ == "__main__":
    initialize_csv()
    initialize_ticket_data_csv()
    print("Bot is running...")
    bot.polling()