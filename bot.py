"""
Loan Calculator Telegram Bot

Features:
1. Calculate loan installments
2. Calculate effective loan interest rate
3. Support loans with and without deposit

Author: Mehdi
"""

import os

from dotenv import load_dotenv
from scipy.optimize import root_scalar
import telebot
from telebot import types

# ==========================================================
# Configuration
# ==========================================================

# load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("BOT_TOKEN not found in .env file")

bot = telebot.TeleBot(TOKEN)

# In-memory storage for active user sessions.
# Data will be lost if the bot restarts
users = {}


# ==========================================================
# Financial Calculations
# ==========================================================


def pva_equation_simple(rate, present_value, installment, periods):
    """
    Present Value of Annuity equation
    Used for loans without deposit.
    """

    return installment * (1 - (1 + rate) ** (-periods)) / rate - present_value


def pva_equation_with_deposit(rate, present_value, installment, periods):
    """
    Present Value of Annuity equation.
    Used for loans with deposit.
    """

    if rate == 0:
        return installment * periods - present_value
    return installment * (1 - (1 + rate) ** (-periods)) / rate - present_value


# ==========================================================
# Main Menu
# ==========================================================

menu = types.ReplyKeyboardMarkup(resize_keyboard=True)
btn1 = types.KeyboardButton("📊 محاسبه بهره وام")
btn2 = types.KeyboardButton("💳 محاسبه اقساط وام")
menu.row(btn1, btn2)


# ==========================================================
# Start Command
# ==========================================================


@bot.message_handler(commands=["start"])
def start(message):
    users[message.chat.id] = {}
    bot.send_message(
        message.chat.id,
        "  خوش آمدید.👋\n\n لطفاً از منوی زیر یکی از گزینه ها را انتخاب کنید.",
        reply_markup=menu,
    )


# ==========================================================
# Installment Calculator
# ==========================================================


@bot.message_handler(func=lambda message: message.text == "💳 محاسبه اقساط وام")
def installment_calculator(message):
    users[message.chat.id] = {}

    msg = bot.send_message(message.chat.id, "💰 مبلغ وام را وارد کنید:")

    bot.register_next_step_handler(msg, get_loan_for_installment)


def get_loan_for_installment(message):
    try:
        users[message.chat.id]["loan_amount"] = int(message.text)
        msg = bot.send_message(message.chat.id, "📈درصد سود سالانه  را وارد کنید:(%)")
        bot.register_next_step_handler(msg, get_rate_for_installment)

    except ValueError:
        msg = bot.send_message(message.chat.id, "فقط عدد وارد کنید❌")
        bot.register_next_step_handler(msg, get_loan_for_installment)
        return


def get_rate_for_installment(message):
    try:
        users[message.chat.id]["annual_rate"] = float(message.text)
        msg = bot.send_message(message.chat.id, "📅تعداد اقساط را وارد کنید:")
        bot.register_next_step_handler(msg, calculate_installment)

    except ValueError:
        msg = bot.send_message(message.chat.id, "فقط عدد وارد کنید❌")
        bot.register_next_step_handler(msg, get_rate_for_installment)
        return


def calculate_installment(message):
    """
    Calculate monthly installment.
    """

    try:

        chat_id = message.chat.id
        count = users[chat_id]["count"] = int(message.text)
        loan = users[chat_id]["loan_amount"]
        annual_rate = users[chat_id]["annual_rate"]
        monthly_rate = annual_rate / 100 / 12

        if monthly_rate == 0:
            installment = loan / count
        else:

            installment = (loan * monthly_rate) / (1 - (1 + monthly_rate) ** -count)

        total_payment = installment * count

        result = f"""
        🏦 نتیجه محاسبه اقساط

        💰 مبلغ وام: {loan:,} تومان
        📈 نرخ سالانه: {annual_rate:.2f}%

        📅 مدت بازپرداخت: {count} ماه

        💳 قسط ماهانه: {installment:,.0f} تومان

        💸 جمع بازپرداخت:
        {total_payment:,.0f} تومان
        """

        bot.send_message(chat_id, result)

        show_restart(chat_id)

    except Exception as e:
        bot.send_message(chat_id, f"❌ خطا: {e}")


# ==========================================================
# Loan Interest Calculator
# ==========================================================


@bot.message_handler(func=lambda message: message.text == "📊 محاسبه بهره وام")
def go_to_calculator(message):
    """
    Entry point for loan interest calculation.

    User chooses whether the loan requires a blocked deposit
    or is a standard loan without deposit.
    """

    # Clear previous user session data
    users[message.chat.id] = {}

    markup = types.InlineKeyboardMarkup()

    btn1 = types.InlineKeyboardButton("وام بدون سپرده", callback_data="without_deposit")
    btn2 = types.InlineKeyboardButton("وام با سپرده", callback_data="with_deposit")

    markup.row(btn1, btn2)

    bot.send_message(
        message.chat.id,
        " 🏦نوع وام را انتخاب کنید",
        reply_markup=markup,
    )


@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    """
    Handle all inline keyboard interactions.

    Possible actions:
    - without_deposit
    - with_deposit
    - restart
    - exit
    """

    users.setdefault(call.message.chat.id, {})

    # Save selected loan type
    if call.data == "without_deposit":
        users[call.message.chat.id]["loan_type"] = "without_deposit"
        msg = bot.send_message(
            call.message.chat.id,
            "💰شما گزینه وام بدون سپرده را انتخاب کردید \n\nمبلغ وام را وارد کنید:",
        )
        bot.register_next_step_handler(msg, get_loan_amount)

    # Save selected loan type
    elif call.data == "with_deposit":
        users[call.message.chat.id]["loan_type"] = "with_deposit"
        msg = bot.send_message(
            call.message.chat.id,
            "💰شما گزینه وام با سپرده را انتخاب کردید\n\n مبلغ وام را وارد کنید:",
        )
        bot.register_next_step_handler(msg, get_loan_amount)

    # Reset user session and return to main menu
    elif call.data == "restart":
        users[call.message.chat.id] = {}
        start(call.message)

    elif call.data == "exit":
        bot.send_message(
            call.message.chat.id,
            "  امیدواریم این محاسبه در تصمیم‌گیری مالی شما کمک ‌کننده بوده باشد.🙏",
        )


# ==========================================================
# User Input Collection
# ==========================================================
#
# Flow:
# Loan Amount
#      ↓
# Installment Amount
#      ↓
# Number of Installments
#      ↓
# Loan Fee
#      ↓
# Deposit Info (if needed)
#      ↓
# Result Calculation
#
# Each function validates user input before
# passing control to the next step.
# ==========================================================


def get_loan_amount(message):
    try:
        users[message.chat.id]["loan_amount"] = int(message.text)
        msg = bot.send_message(message.chat.id, "💳مبلغ اقساط را وارد کنید:")
        bot.register_next_step_handler(msg, get_installment_amount)

    except ValueError:
        msg = bot.send_message(message.chat.id, "فقط عدد وارد کنید❌")
        bot.register_next_step_handler(msg, get_loan_amount)
        return


def get_installment_amount(message):
    try:
        users[message.chat.id]["installment_amount"] = int(message.text)
        msg = bot.send_message(message.chat.id, "📅تعداد اقساط را وارد کنید:")
        bot.register_next_step_handler(msg, get_count)
    except ValueError:
        msg = bot.send_message(message.chat.id, "فقط عدد وارد کنید❌")
        bot.register_next_step_handler(msg, get_installment_amount)
        return


def get_count(message):
    try:
        users[message.chat.id]["count"] = int(message.text)
        msg = bot.send_message(message.chat.id, "کارمزد وام را وارد کنید:")
        bot.register_next_step_handler(msg, get_fee)
    except ValueError:
        msg = bot.send_message(message.chat.id, "فقط عدد وارد کنید❌")
        bot.register_next_step_handler(msg, get_count)


def get_fee(message):
    try:
        if users[message.chat.id]["loan_type"] == "without_deposit":
            users[message.chat.id]["fee"] = int(message.text)
            get_result(message)
        else:
            users[message.chat.id]["fee"] = int(message.text)
            msg = bot.send_message(message.chat.id, "💳مبلغ سپرده را وارد کنید:")
            bot.register_next_step_handler(msg, deposit_amount)

    except ValueError:
        msg = bot.send_message(message.chat.id, "فقط عدد وارد کنید❌")
        bot.register_next_step_handler(msg, get_fee)


def deposit_amount(message):
    try:
        users[message.chat.id]["deposit"] = int(message.text)

        msg = bot.send_message(
            message.chat.id, "📅تعداد ماه‌های بلوکه شدن سپرده را وارد کنید:"
        )
        bot.register_next_step_handler(msg, get_lock_periods)

    except ValueError:
        msg = bot.send_message(message.chat.id, "فقط عدد وارد کنید❌")
        bot.register_next_step_handler(msg, deposit_amount)
        return


def get_lock_periods(message):
    try:
        chat_id = message.chat.id

        users[chat_id]["lock_periods"] = int(message.text)
        get_result(message)

    except ValueError:
        msg = bot.send_message(message.chat.id, "فقط عدد وارد کنید❌")
        bot.register_next_step_handler(msg, get_lock_periods)
        return


# ==========================================================
# Loan Calculation Engine
# ==========================================================


def get_result(message):
    """
    Calculate the effective interest rate of the loan.

    Method:
    1. Determine actual received amount.
    2. Adjust for deposit opportunity cost if applicable.
    3. Solve the annuity equation numerically using Brent's method.
    4. Convert monthly rate to annual effective rate.
    5. Display final report to the user.
    """

    try:

        chat_id = message.chat.id
        loan_amount = users[chat_id]["loan_amount"]
        installment_amount = users[chat_id]["installment_amount"]
        count = users[chat_id]["count"]
        fee = users[chat_id]["fee"]
        loan_type = users[chat_id]["loan_type"]
        total_payment = installment_amount * count
        net_received = loan_amount - fee

        if loan_type == "without_deposit":
            net_pva = loan_amount - fee

            # Solve the annuity equation numerically to find
            # the effective monthly interest rate.
            result = root_scalar(
                pva_equation_simple,
                args=(net_pva, installment_amount, count),
                bracket=[1e-9, 1],
                method="brentq",
            )

        else:
            deposit_amount = users[chat_id]["deposit"]
            lock_periods = users[chat_id]["lock_periods"]

            deposit_fv = deposit_amount * (1 + 0.03) ** lock_periods
            deposit_cost = deposit_fv - deposit_amount
            net_pva = loan_amount - deposit_cost - fee

            result = root_scalar(
                pva_equation_with_deposit,
                args=(net_pva, installment_amount, count),
                bracket=[1e-9, 1],
                method="brentq",
            )

        monthly_rate = result.root
        annual_rate = ((1 + monthly_rate) ** 12 - 1) * 100
        total_rate = ((1 + monthly_rate) ** count - 1) * 100

        result_text = f"""
        🏦 نتیجه محاسبه وام

        💰 مبلغ وام: {loan_amount:,} تومان
        💵 مبلغ دریافتی واقعی: {net_received:,} تومان
        💳 قسط ماهانه: {installment_amount:,} تومان
        📅 تعداد اقساط: {count} ماه
        💸 جمع بازپرداخت: {total_payment:,} تومان

       

        📊 هزینه کل وام: {total_payment - net_received:,} تومان
        📊 نرخ ماهانه: {monthly_rate:.2f}%
        📈 نرخ سالانه مؤثر: {annual_rate:.2f}%
        🔥 نرخ کل دوره: {total_rate:.2f}%
        """

        if loan_type == "with_deposit":
            result_text += f"""
       

        💰 مبلغ سپرده: {deposit_amount:,} تومان
        🔒 مدت بلوکه: {lock_periods} ماه
        💸 هزینه فرصت: {deposit_cost:,.0f} تومان
        """

        result_text += "\n محاسبات با موفقیت انجام شد.✅"

        bot.send_message(chat_id, result_text)
        show_restart(chat_id)

    except Exception as e:
        bot.send_message(chat_id, f"❌ خطا در محاسبه: {e}")
        show_restart(chat_id)


# -------------------------------------------------------------------------------


def show_restart(chat_id):
    """
    Display action buttons after a calculation is completed.

    Allows the user to either:
    - Start a new calculation
    - Exit the conversation
    """

    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton("🔄 محاسبه جدید", callback_data="restart")
    btn2 = types.InlineKeyboardButton("❌ پایان", callback_data="exit")
    markup.row(btn1, btn2)

    bot.send_message(
        chat_id, "آیا مایل به انجام محاسبه دیگری هستید؟", reply_markup=markup
    )


# ==========================================================
# Application Entry Point
# ==========================================================


if __name__ == "__main__":

    print("Loan Calculator Bot Started...")

    # Keep the bot running continuously and
    # automatically reconnect on network failures.
    bot.infinity_polling()
