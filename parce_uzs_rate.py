import requests

def get_uzs_rate():
    try:
        # Получаем курс с сайта Центрального банка Узбекистана
        response = requests.get('https://cbu.uz/ru/arkhiv-kursov-valyut/json/')
        data = response.json()
        for currency in data:
            if currency['Ccy'] == 'USD':
                print("current rate of USD to UZS : ", currency['Rate'], "-------------------------------------------------------------------\n")
                return float(currency['Rate'])
    except:
        # Если не удалось получить курс, возвращаем примерный курс
        print('exception', "12890.0", "-------------------------------------------------------------------\n")
        return 12890.0

def round_uzs(amount):
    if amount < 100000:  # Для сумм меньше 100k
        return round(amount / 1000) * 1000
    elif amount < 1000000:  # Для сумм от 100k до 1M
        return round(amount / 5000) * 5000
    else:  # Для сумм больше 1M
        return round(amount / 10000) * 10000 