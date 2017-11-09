'''
    VIA POS Bot

    VIA Telegram Bot Hackathon 2017
    https://svia.nl/telegrambot

    NOTE: Eerste opzet.


    Werking:
    Bestel via de bot @viaposbot
    Lijst met dranken / schnapps
    Bij bestelling kiezen: Directe VIA tab afschrijving
'''

import logging, requests, json, time, pickle
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Updater, Filters, MessageHandler, CommandHandler, CallbackQueryHandler, ConversationHandler
from telegram.error import TelegramError, Unauthorized, BadRequest, TimedOut, ChatMigrated, NetworkError

via_pos_products = ""
NONE, LOGIN, PASSWORD, ORDER, ORDER_AMOUNT, CONFIRM_ORDER = range(6)
INVALID_BOT = None

# @viaposbot TOKEN
token=""


def start(bot, update):
    update.message.reply_text(
        "<b>VIA POS Bot</b>\n"\
        "<i>Telegram Hackathon - VIA 2017</i>\n"\
        "___________________________\n\n"\
        "Hoi {}! Ik ben de POS bot. Je kunt via mij bestellingen plaatsen en je saldo opvragen.\n"\
        "Je moet eerst inloggen om dit te doen.\n"\
        "Gebruik dit commando om in te loggen:\n\n"\
        "/login\n\n"\
        "Jouw Telegram naam wordt gebruikt voor het vinden van jouw tab. "\
        "Voor meer informatie kun je terecht op de VIA website.\n"\
        "___________________________\n\n".format(update.message.chat.first_name),
    parse_mode="HTML")

'''
TODO: hash passwords.
def hash_password(password):
    return bcrypt.hashpw(password, bcrypt.gensalt())

def check_password(password):
    return bcrypt.hashpw(password, hashed) == hashed
'''

def get_product_id(product_name):
    products = get_products()
    without_price = product_name.partition("€")[0] # TODO: REMOVE LAST SPACES
    global via_pos_products
    for product in via_pos_products:
        if(via_pos_products[product]['name'] in without_price):
            return via_pos_products[product]['id']
    return None

def get_product_name(product_id):
    products = get_products()
    global via_pos_products
    for product in via_pos_products:
        if(via_pos_products[product]['id'] == product_id):
            return via_pos_products[product]['name']
    return None

def get_product_price(product_id):
    products = get_products()
    global via_pos_products
    for product in via_pos_products:
        if(via_pos_products[product]['id'] == product_id):
            return to_number(via_pos_products[product]['price'])
    return None

def to_number(s):
    try:
        return int(s)
    except ValueError:
        return float(s)

def get_saldo(user_data):
    try:
        if(user_data['login_timestamp'] is False):
            return None
    except:
        return None
    headers = {
        'Referer': 'http://dev.automatis.nl/pos/saldo/',
    }
    params = (
        ('action', 'get_user_balance'),
        ('pin', user_data['password']),
        ('user', user_data['user']),
    )

    saldo = requests.get('http://dev.automatis.nl/pos/api/', headers=headers, params=params).content.decode("utf-8")
    return to_number(saldo)


def numeric_keyboard():
    return [
        [InlineKeyboardButton('1', callback_data='1'), InlineKeyboardButton('2', callback_data='2'), InlineKeyboardButton('3', callback_data='3')],
        [InlineKeyboardButton('4', callback_data='4'), InlineKeyboardButton('5', callback_data='5'), InlineKeyboardButton('6', callback_data='6')],
        [InlineKeyboardButton('7', callback_data='7'), InlineKeyboardButton('8', callback_data='8'), InlineKeyboardButton('9', callback_data='9')],
        [InlineKeyboardButton('0', callback_data='0')]
    ]


def get_users(user_name_query):
    headers = {
        'Referer': 'http://dev.automatis.nl/posbier/',
    }

    params = (
        ('action', 'get_users'),
        ('asArray', ''),
    )

    r = requests.get('http://dev.automatis.nl/pos/api/', headers=headers, params=params)

    users_dict = r.json()
    filtered = [x for x in users_dict if user_name_query in x['name'].lower()]

    return [[InlineKeyboardButton(f['name'], callback_data=f['id'])] for f in filtered]

def get_products():
    headers = {
        'Referer': 'http://dev.automatis.nl/posbier/',
    }

    params = (
        ('action', 'get_products'),
    )

    r = requests.get('http://dev.automatis.nl/pos/api/', headers=headers, params=params)
    global via_pos_products
    via_pos_products = r.json()
    keyboard = []
    for j in via_pos_products:
        text = via_pos_products[j]['name'] + " €" + via_pos_products[j]['price']
        keyboard.append([InlineKeyboardButton(text)])
    return keyboard

def saldo(bot, update, user_data):
    saldo = get_saldo(user_data)
    if(saldo is None):
        update.message.reply_text("Je bent nog niet ingelogd.")
    else:
        update.message.reply_text("Jouw saldo is nu: €{:.2f}".format(saldo))


def login_code(bot, update, user_data):
    keyboard = numeric_keyboard()
    reply_keyboard_markup = ReplyKeyboardMarkup(keyboard)
    bot.sendMessage(chat_id=update.callback_query.message.chat_id,
                     text="Hoi, {} {}. Voer nu je pincode in om in te loggen".format(
                        update.callback_query.message.chat.first_name,
                        update.callback_query.message.chat.last_name),
                     reply_markup=reply_keyboard_markup)
    user_data['password'] = ""
    user_data['STATE'] = PASSWORD

def logout(bot, update, user_data):
    user_data['user'] = ""
    user_data['password'] = ""
    user_data['STATE'] = NONE
    user_data['login_timestamp'] = None
    user_data['product_id'] = None
    user_data['product_amount'] = None
    update.message.reply_text("Je bent nu uitgelogd.")

def login(bot, update, args, user_data):
    user_data['STATE'] = LOGIN
    if(len(args) == 1):
        users = get_users(args[0])
    else:
        users = get_users(update.message.chat.first_name.lower())
    reply_markup = InlineKeyboardMarkup(users)
    update.message.reply_text(
    "Selecteer je tab als deze verschijnt.\n"\
    "Als je nog geen tab hebt, dan kun je deze laten aanmaken.\n"\
    "Als je er eentje hebt, maar er geen ziet, voer (een deel van) je naam in.\n\n"\
    "Usage: /login John", reply_markup=reply_markup)



def bestel(bot, update, user_data):
    if(not user_data['login_timestamp']):
        update.message.reply_text("Je kunt niet nog niet bestellen. Log eerst in met /login")
    else:
        user_data['STATE'] = ORDER
        keyboard = get_products()
        reply_keyboard_markup = ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, one_time_keyboard=True)
        update.message.reply_text("Kies wat je wilt bestellen:", reply_markup=reply_keyboard_markup)

def auth_login(bot, update, user_data):
    if(authenticate_user(user_data)):
        timestamp = time.time()
        user_data['login_timestamp'] = timestamp
        update.message.reply_text("{} {}, je bent nu ingelogd ☺️\n"\
        "Om te bestellen, gebruik: \n\n/bestel\n\n"\
        "Om uit te loggen, gebruik: \n\n/logout\n\n.".format(
                    update.message.chat.first_name,
                    update.message.chat.last_name))
    else:
        update.message.reply_text("Dit is een verkeerde code. Probeer het opnieuw.")
        user_data['password'] = ""
        login_code(bot, update, user_data)

def authenticate_user(user_data):
    headers = {
        'Referer': 'http://dev.automatis.nl/pos/saldo/',
    }
    params = (
        ('action', 'get_user_balance'),
        ('pin', user_data['password']),
        ('user', user_data['user']),
    )

    r = requests.get('http://dev.automatis.nl/pos/api/', headers=headers, params=params)
    if(r.status_code == 200):
        return True
    return False


def callback_handler(bot, update, user_data):
    query = update.callback_query
    if(user_data['STATE'] == LOGIN):
        user_data['user'] = query.data
        return login_code(bot, update, user_data)

def help(bot, update):
    update.message.reply_text("Use /start to start.")

def confirm_order(bot, update, user_data):
    confirm_order_text = "Weet je zeker dat je {} {} wilt bestellen voor €{:.2f}?".format(
        user_data['product_amount'], get_product_name(user_data['product_id']),
        user_data['product_amount'] * get_product_price(user_data['product_id'])
    )

    keyboard = [[InlineKeyboardButton('Ja'), InlineKeyboardButton('Nee')]]
    reply_keyboard_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    bot.sendMessage(chat_id=update.message.chat_id,
                     text=confirm_order_text,
                     reply_markup=reply_keyboard_markup)
    user_data['STATE'] = CONFIRM_ORDER

def order_amount(bot, update, user_data):
    keyboard = numeric_keyboard()
    reply_keyboard_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    bot.sendMessage(chat_id=update.message.chat_id,
                     text="Hoeveel {} wil je bestellen?".format(get_product_name(user_data['product_id'])),
                     reply_markup=reply_keyboard_markup)
    user_data['STATE'] = ORDER_AMOUNT

def order_product(bot, update, user_data):
    if(authenticate_user(user_data)):
        order_amount(bot, update, user_data)
    else:
        update.message.reply_text("Het product kon niet worden besteld. Je inloggegevens konden niet worden geverifieerd.")

def process_order(bot, update, user_data):
    data = {user_data['product_id']: user_data['product_amount']}

    headers = {
        'Referer': 'http://dev.automatis.nl/posbier/',
    }

    params = (
        ('action', 'buy_products'),
        ('bijpinnen', '0'),
        ('cart', json.dumps(data)),
        ('clientKey', 'kelder_bier_app'),
        ('forUser', '0'),
        ('method', 'list'),
        ('pincode', user_data['password']),
        ('user', user_data['user']),
    )

    r = requests.get('http://dev.automatis.nl/pos/api/', headers=headers, params=params)
    if(r.status_code == 200):
        return True
    return False

def check_saldo(bot, update, user_data):
    price = get_product_price(user_data['product_id']) * user_data['product_amount']
    saldo = get_saldo(user_data)
    if(price > saldo):
        return False
    return True

def message_handler(bot, update, user_data):
    if(user_data['STATE'] == PASSWORD):
        if(update.message.text):
            user_data['password'] += str(update.message.text)
            if(len(user_data['password']) > 3):
                update.message.reply_text("*\n*\n*\n*\n*\n*\n*\n*\n*\n*\n*\n*\n*\n*\n*\n*\n*\n*\n*\n*\n*\n*\n*\n*\n*\n*\n*\n*\n")
                return auth_login(bot, update, user_data)

    if(not user_data['login_timestamp']): return
    elif(user_data['STATE'] == ORDER):
        product_id = get_product_id(update.message.text)
        if(product_id is None):
            update.message.reply_text("Sorry, dit product ken ik niet! Probeer het opnieuw")
            bestel(bot, update, user_data)
        else:
            user_data['product_id'] = product_id
            order_product(bot, update, user_data)
    elif(user_data['STATE'] == ORDER_AMOUNT):
        user_data['product_amount'] = to_number(update.message.text)
        if(check_saldo(bot, update, user_data)):
            confirm_order(bot, update, user_data)
        else:
            update.message.reply_text("Je hebt niet genoeg saldo op je rekening.")
            user_data['STATE'] = NONE
    elif(user_data['STATE'] == CONFIRM_ORDER):
        if(update.message.text == "Ja"):
            result = process_order(bot, update, user_data)
            if(result):
                update.message.reply_text("€{:.2f} is van je rekening afgeschreven.".format(get_product_price(user_data['product_id']) * user_data['product_amount']))
                saldo(INVALID_BOT, update, user_data)
                update.message.reply_text("Dankjewel voor je bestelling!")
                user_data['STATE'] = NONE
            else:
                update.message.reply_text("Er is iets mis gegaan bij je bestelling.")
                user_data['STATE'] = NONE
        else:
            update.message.reply_text("Je hebt je bestelling gecanceled.")
            user_data['STATE'] = NONE

def load_user_data():
    try:
        f = open('userdata', 'rb')
        user_data = pickle.load(f)
        f.close()
        return user_data
    except FileNotFoundError:
        print("Data file not found")
        return False
    except:
        return False

def save_user_data(user_data):
    print("Saving user data...")
    try:
        f = open('userdata', 'wb+')
        pickle.dump(user_data, f)
        f.close()
    except:
        print("Error saving user_data")
        pass


def error_callback(bot, update, error):
    try:
        raise error
    except Unauthorized as e:
        print(e)
        # remove update.message.chat_id from conversation list
    except BadRequest as e:
        print(e)
    except TimedOut as e:
        print(e)
        # handle slow connection problems
    except NetworkError as e:
        print(e)
        # handle other connection problems
    except ChatMigrated as e:
        print(e)
        # the chat_id of a group has changed, use e.new_chat_id instead
    except TelegramError as e:
        print(e)
        # handle all other telegram related errors

def main():
    updater = Updater(token)
    logging.basicConfig()
    dp = updater.dispatcher
    loaded_data = load_user_data()

    if(loaded_data):
        print("Loaded User Data")
        dp.user_data = loaded_data


    dp.add_handler(MessageHandler(Filters.text, message_handler, pass_user_data=True))
    dp.add_handler(CallbackQueryHandler(callback_handler, pass_user_data=True))
    dp.add_error_handler(error_callback)

    # Commands
    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CommandHandler('login', login, pass_args=True, pass_user_data=True))
    dp.add_handler(CommandHandler('logout', logout, pass_user_data=True))
    dp.add_handler(CommandHandler('bestel', bestel, pass_user_data=True))
    dp.add_handler(CommandHandler('saldo', saldo, pass_user_data=True))
    dp.add_handler(CommandHandler('help', help))


    # Start the bot
    updater.start_polling()

    try:
        while(updater):
            time.sleep(60)
            save_user_data(dp.user_data)
    except KeyboardInterrupt:
        exit
    # Run the bot until the user presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT
    updater.idle()


if __name__ == "__main__":
    main()
