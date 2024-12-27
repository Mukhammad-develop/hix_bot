import csv

DATABASE_FILE = 'user_data.csv'

# Initialize the database file if it doesn't exist
def initialize_csv():
    try:
        with open(DATABASE_FILE, mode='x', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['user_id', 'trial_balance', 'balance'])
    except FileExistsError:
        pass

# Read user data from the CSV
def get_user_data(user_id):
    with open(DATABASE_FILE, mode='r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if int(row['user_id']) == user_id:
                return row
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
