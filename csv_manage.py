import csv
import os
from datetime import datetime
import random

DATABASE_FILE = 'user_data.csv'

# Initialize the database file if it doesn't exist
def initialize_csv():
    try:
        with open(DATABASE_FILE, mode='x', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['user_id', 'trial_balance', 'balance'])
    except FileExistsError:
        pass

def initialize_ticket_data_csv():
    if not os.path.exists('ticket_data.csv'):
        with open('ticket_data.csv', mode='w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=[
                'ticket_id', 'user_id', 'username', 'package',
                'amount_usd', 'amount_uzs', 'words', 'status', 'date'
            ])
            writer.writeheader()

# Read user data from the CSV
def get_user_data(user_id):
    try:
        with open(DATABASE_FILE, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if int(row['user_id']) == user_id:
                    return row
    except FileNotFoundError:
        print(f"Error: {DATABASE_FILE} not found.")
    except Exception as e:
        print(f"An error occurred: {e}")
    return None

def get_username(user_id, csv_file_path='ticket_data.csv'):
    with open(csv_file_path, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if int(row['user_id']) == user_id:
                return row['username']
    return None

# Update or insert user data in the CSV
def update_user_data(user_id, trial_balance=None, balance=None):
    rows = []
    updated = False

    with open(DATABASE_FILE, mode='r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if int(row['user_id']) == user_id:
                if trial_balance is not None:
                    row['trial_balance'] = trial_balance
                if balance is not None:
                    row['balance'] = balance
                updated = True
            rows.append(row)

    if not updated:
        rows.append({'user_id': user_id, 'trial_balance': trial_balance or 200, 'balance': balance or 0})

    with open(DATABASE_FILE, mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=['user_id', 'trial_balance', 'balance'])
        writer.writeheader()
        writer.writerows(rows)

# проверка на уникальность ticket_id
def generate_unique_ticket_id(csv_file_path):
    existing_ids = set()

    # Чтение существующих ticket_id из CSV
    with open(csv_file_path, mode='r', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            existing_ids.add(int(row['ticket_id']))

    # Генерация уникального ticket_id
    while True:
        ticket_id = random.randint(100000, 999999)
        if ticket_id not in existing_ids:
            return ticket_id

# сохранение платежа в csv
def save_payment_to_csv(message, package):
    ticket_id = generate_unique_ticket_id('ticket_data.csv')
    current_time = datetime.now().strftime("%d/%m/%Y %H:%M")
    
    ticket_data = {
        'ticket_id': ticket_id,
        'user_id': message.from_user.id,
        'username': f"@{message.from_user.username}",
        'package': package['id'],
        'amount_usd': package['price_usd'],
        'amount_uzs': package['price_uzs'],
        'words': package['words'],
        'status': 'in progress',
        'date': current_time
    }
    
    file_exists = os.path.exists('ticket_data.csv')
    
    with open('ticket_data.csv', 'a', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=[
            'ticket_id', 'user_id', 'username', 'package',
            'amount_usd', 'amount_uzs', 'words', 'status', 'date'
        ])
        
        if not file_exists:
            writer.writeheader()
            
        writer.writerow(ticket_data)
    
    return ticket_id, current_time

def handle_payment_decision_to_csv(file_path, rows, fieldnames):
    with open(file_path, mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

def balance_updates_to_csv(target_user_id, amount, datetime):
    file_exists = os.path.exists('balance_updates.csv')
    
    with open('balance_updates.csv', mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        
        # Write header only if the file is being created for the first time
        if not file_exists:
            writer.writerow(['user_id', 'units', 'datetime'])
        
        writer.writerow([target_user_id, amount, datetime])

