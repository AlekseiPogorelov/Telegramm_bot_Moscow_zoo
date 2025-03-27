import telebot
from telebot import types
import random
import config


bot = telebot.TeleBot(config.TOKEN)

user_scores = {}
user_answers = {}


@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item = types.KeyboardButton('Начать викторину')
    markup.add(item)

    bot.send_message(message.chat.id,
                     "🐾 Добро пожаловать в викторину Московского зоопарка! 🐾\n\n"
                     "Ответьте на 10 вопросов, и мы определим ваше тотемное животное.\n"
                     "В конце вы сможете взять опеку над своим тотемным животным в нашем зоопарке!",
                     reply_markup=markup)


@bot.message_handler(func=lambda message: message.text == 'Начать викторину')
def start_quiz(message):
    user_scores[message.chat.id] = {animal: 0 for animal in config.animals_data.keys()}
    user_answers[message.chat.id] = []
    ask_question(message, 0)


def ask_question(message, question_index):
    if question_index >= len(config.quiz_questions):
        show_result(message)
        return

    question = config.quiz_questions[question_index]
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)

    buttons = [types.KeyboardButton(option) for option in question['options']]
    markup.add(*buttons)

    progress = f"Вопрос {question_index + 1}/{len(config.quiz_questions)}"
    bot.send_message(message.chat.id, f"{progress}\n\n{question['question']}", reply_markup=markup)

    @bot.message_handler(func=lambda m: m.text in question['options'])
    def handle_answer(m):
        if m.chat.id not in user_scores:
            return

        selected_option = m.text
        option_index = question['options'].index(selected_option)
        user_answers[m.chat.id].append(selected_option)

        # Обновляем баллы для каждого животного
        for animal in config.animals_data.keys():
            if option_index == question['weights'].get(animal, 0):
                user_scores[m.chat.id][animal] += 1


        ask_question(m, question_index + 1)


def show_result(message):
    if message.chat.id not in user_scores:
        bot.send_message(message.chat.id, "Что-то пошло не так. Попробуйте начать викторину снова.")
        return

    scores = user_scores[message.chat.id]
    top_animals = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3]
    totem_animal = top_animals[0][0]
    animal_info = config.animals_data[totem_animal]

    # Отправляем изображение животного
    try:
        bot.send_photo(message.chat.id, animal_info['image'],
                       caption=f"Ваше тотемное животное - {totem_animal}! 🎉")
    except:
        bot.send_message(message.chat.id, f"Ваше тотемное животное - {totem_animal}! 🎉")


    desc_message = (
        f"🐾 {animal_info['description']}\n\n"
        f"Другие животные, которые вам подходят:\n"
        f"2. {top_animals[1][0]} ({top_animals[1][1]} баллов)\n"
        f"3. {top_animals[2][0]} ({top_animals[2][1]} баллов)\n\n"
        f"Хотите узнать больше о своем тотемном животном?"
    )

    bot.send_message(message.chat.id, desc_message)

    # Создаем кнопки
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("Взять опеку", url=animal_info['sponsor_link']),
        types.InlineKeyboardButton("Пройти еще раз", callback_data='restart_quiz'),
        types.InlineKeyboardButton("📋 Скопировать результат", callback_data=f"copy_result_{totem_animal}"),
        types.InlineKeyboardButton("📞 Связаться", callback_data=f"contact_{totem_animal}")
    )

    bot.send_message(message.chat.id,
                     f"Вы можете взять опеку над {totem_animal} в нашем зоопарке и поддерживать его содержание!",
                     reply_markup=markup)

    # Удаляем результаты пользователя
    del user_scores[message.chat.id]
    del user_answers[message.chat.id]


@bot.callback_query_handler(func=lambda call: call.data == 'restart_quiz')
def restart_quiz(call):
    start_quiz(call.message)


@bot.callback_query_handler(func=lambda call: call.data.startswith('copy_result_'))
def handle_copy_result(call):
    animal = call.data.split('_')[-1]
    animal_info = config.animals_data[animal]

    result_text = (
        f"Мое тотемное животное - {animal}! 🦁🐯🐻\n\n"
        f"{animal_info['description']}\n\n"
        "Пройди викторину и узнай свое: @m99_zoo_bot"
    )


    bot.answer_callback_query(
        call.id,
        "Текст скопирован! Теперь можешь вставить его куда угодно.",
        show_alert=True
    )


    bot.send_message(call.message.chat.id, f"```\n{result_text}\n```", parse_mode="Markdown")


@bot.callback_query_handler(func=lambda call: call.data.startswith('contact_'))
def handle_contact_request(call):
    totem_animal = call.data.split('_')[1]
    user = call.from_user


    user_data = {
        'user_id': user.id,
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'animal': totem_animal,
        'status': 'waiting'
    }


    bot.send_message(
        call.message.chat.id,
        "📨 Ваш запрос отправлен сотруднику зоопарка. Ожидайте ответа в ближайшее время!\n"
        "Вы можете написать свой вопрос прямо сейчас:"
    )

    # Отправляем уведомление сотруднику
    contact_markup = types.InlineKeyboardMarkup()
    contact_markup.add(types.InlineKeyboardButton(
        "Ответить пользователю",
        callback_data=f"reply_to_{user.id}"
    ))

    bot.send_message(
        config.ADMIN_CHAT_ID,
        f"🆕 Новый запрос от пользователя:\n\n"
        f"👤 {user.first_name} {user.last_name} (@{user.username})\n"
        f"🦁 Тотемное животное: {totem_animal}\n"
        f"📝 Результат викторины: {config.animals_data[totem_animal]['description']}",
        reply_markup=contact_markup
    )


    bot.register_next_step_handler(call.message, process_user_question, user_data)


def process_user_question(message, user_data):
    # Сохраняем вопрос пользователя
    user_data['question'] = message.text
    user_data['status'] = 'question_received'

    # Отправляем вопрос сотруднику
    bot.send_message(
        config.ADMIN_CHAT_ID,
        f"❓ Вопрос от пользователя {user_data['first_name']}:\n\n"
        f"{message.text}\n\n"
        f"Тотемное животное: {user_data['animal']}",
        reply_markup=types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton(
                "📨 Ответить",
                callback_data=f"reply_to_{user_data['user_id']}"
            )
        )
    )

    bot.send_message(
        message.chat.id,
        "✅ Ваш вопрос получен! Сотрудник зоопарка ответит вам в ближайшее время."
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith('reply_to_'))
def handle_admin_reply(call):
    user_id = call.data.split('_')[-1]


    bot.send_message(
        config.ADMIN_CHAT_ID,
        f"Введите ваш ответ для пользователя (ID: {user_id}):"
    )


    bot.register_next_step_handler(
        call.message,
        process_admin_reply,
        user_id
    )


def process_admin_reply(message, user_id):

    try:
        bot.send_message(
            user_id,
            f"📩 Ответ от сотрудника зоопарка:\n\n{message.text}"
        )
        bot.send_message(
            config.ADMIN_CHAT_ID,
            "✅ Ваш ответ успешно отправлен пользователю!"
        )
    except Exception as e:
        bot.send_message(
            config.ADMIN_CHAT_ID,
            f"❌ Не удалось отправить ответ. Ошибка: {str(e)}"
        )


bot.polling(none_stop=True)