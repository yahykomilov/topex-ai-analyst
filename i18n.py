"""Строки интерфейса на трёх языках: русский, узбекский (латиница), английский.

Владелец переключает язык кнопками (см. state.get_lang / set_lang).
Ключи одинаковые для всех языков; t(lang, key) достаёт строку с фолбэком на RU.
Плейсхолдеры в фигурных скобках подставляются через t(lang, key, name=...).
"""

# порядок и отображаемые имена языков (для кнопок-переключателей)
LANGS = ["ru", "uz", "en"]
LANG_NAMES = {"ru": "🇷🇺 Рус", "uz": "🇺🇿 O‘zb", "en": "🇬🇧 Eng"}

I18N: dict[str, dict[str, str]] = {
    "ru": {
        "menu_title": (
            "📋 Главное меню\n\n"
            "👥 Сотрудники — выберите менеджера, посмотрите его звонки, разбор AI и статистику.\n"
            "📈 Отчёт за день — сколько клиентов обслужили, топ дня, системные ошибки и ТЗ каждому "
            "сотруднику (автоматически приходит в 20:00).\n"
            "📊 Общая статистика — итоги по всему отделу.\n\n"
            "🎧 Также можно просто прислать сюда запись звонка или текст расшифровки — "
            "я сразу сделаю аудит."
        ),
        "btn_employees": "👥 Сотрудники",
        "btn_daily": "📈 Отчёт за день",
        "btn_stats": "📊 Общая статистика",
        "btn_search": "🔍 Поиск сотрудника",
        "btn_back_menu": "⬅️ Меню",
        "btn_menu": "📋 Меню",
        "btn_back_calls": "⬅️ К звонкам сотрудника",
        "btn_back_employees": "👥 К сотрудникам",
        "btn_to_employee": "⬅️ К сотруднику",
        "btn_pick_date": "📅 Выбрать дату",
        "btn_other_date": "📅 Другая дата",
        "btn_back": "⬅️ Назад",
        "btn_audio_review": "📋 Аудио + разбор",
        "lang_switched": "🌐 Язык переключён на русский.",
        "employees_title": "👥 Сотрудники (в скобках — количество разобранных звонков):",
        "employees_empty": (
            "Пока нет ни сотрудников, ни разобранных звонков.\n\n"
            "Пришлите запись звонка сюда — или дождитесь нового звонка из AmoCRM."
        ),
        "search_prompt": "🔍 Введите имя сотрудника (или часть имени):",
        "search_none": "Никого не нашёл по запросу: ",
        "search_title": "🔍 Найдено по запросу «{q}»:",
        "mgr_default_name": "Сотрудник",
        "mgr_no_calls": "Разобранных звонков пока нет.",
        "calls_pick_hint": (
            "Выберите звонок (✅❌❓ — уже разобран: аудио + PDF, "
            "⬜ — новый: разберу при нажатии):"
        ),
        "calls_none_crm": "Звонков с записью в CRM пока не видно.",
        "no_number": "без номера",
        "dates_pick": "📅 Выберите дату — покажу все разговоры за этот день:",
        "no_calls_yet": "Звонков пока нет",
        "no_calls_day": "За {day} звонков нет",
        "day_calls_header": (
            "👨‍💼 {name} • 📅 {day}\n\n"
            "Разговоры за этот день ({n}):\n"
            "✅❌❓ — разобраны, ⬜ — разберу при нажатии"
        ),
        "analyzing_short": "Разбираю звонок...",
        "downloading": "🎧 Скачиваю запись, расшифровываю и готовлю PDF (1-2 минуты)...",
        "call_not_found_crm": "❌ Звонок не найден в CRM (возможно, устарел). Откройте карточку сотрудника заново.",
        "analyze_failed": "⚠️ Не удалось разобрать звонок (нет речи или ошибка записи).",
        "error_generic": "❌ Ошибка: {err}",
        "call_not_found": "Звонок не найден.",
        "audio_unavailable": "(аудиозапись недоступна)",
        "transcript_title": "📃 Полный текст разговора (дословно, как записано):\n\n{text}",
        "transcript_empty": "Текст расшифровки отсутствует.",
        "report_empty": "Отчёт отсутствует.",
        "stats_dept_title": "📊 Общая статистика отдела\n",
        "stats_by_employee": "\n👥 По сотрудникам:",
        "calls_short": "зв.",
        "avg_score_suffix": ", ср. балл {x}/10",
        "daily_building": "📈 Собираю общий отчёт за день...",
        "daily_empty": "За сегодня пока нет ни одного разобранного звонка — отчёт будет, когда появятся звонки.",
        "daily_error": "❌ Ошибка при построении отчёта: {err}",
        "daily_auto_header": "🌙 Автоматический отчёт за день:",
        "status_amo_ok": "🟢 AmoCRM подключён: {name} (проверка каждые {sec} сек)",
        "status_amo_err": "🔴 AmoCRM: ошибка подключения — {err}",
        "status_amo_off": "⚪ AmoCRM не подключён. Отправьте /connect, чтобы подключить свой аккаунт.",
        "status_body": (
            "📡 Статус бота\n\n{amo}\n"
            "⏱ Минимальная длительность звонка: {sec} сек\n"
            "💾 Звонков в базе: {n}"
        ),
        "private_bot": "⛔ Бот приватный. Отправьте /start, если вы владелец.",
        "auditing": "🧠 Провожу жёсткий аудит звонка...",
        "send_audio_hint": "Пришлите аудиофайл (mp3/wav/ogg/m4a), голосовое или .txt с расшифровкой.",
        "file_too_big": "⚠️ Файл больше 20 МБ — Telegram не даёт ботам скачивать такие файлы. Сожмите запись или пришлите частями.",
        "got_recording": "🎧 Получил запись. Расшифровываю...",
        "no_speech": "⚠️ В записи почти нет речи — нечего анализировать.",
        "transcribed_auditing": "🧠 Расшифровал. Провожу жёсткий аудит звонка...",
        "send_call_hint": (
            "Пришлите запись звонка (аудио/голосовое) или полный текст расшифровки "
            "(не короче 100 символов).\n\nМеню: /menu"
        ),
        "pdf_caption": "📄 Полный разбор звонка (PDF)",
        "doc_unavailable": "Разбор для этого звонка недоступен.",
        "owner_assigned": "✅ Вы назначены владельцем бота.",
        "private_taken": "⛔ Бот приватный и уже привязан к другому пользователю.",
        "preparing_report": "Готовлю отчёт...",
        "choose_lang": "🌐 Выберите язык:",
        "pdf_title": "Разбор звонка — {name}",
        "pdf_score": "Оценка",
        "wd_0": "Пн", "wd_1": "Вт", "wd_2": "Ср", "wd_3": "Чт", "wd_4": "Пт", "wd_5": "Сб", "wd_6": "Вс",
        # оценки/вердикты
        "stats_total": "📞 Всего звонков: {n}",
        "stats_ok": "✅ Успешные: {n} ({p}%)",
        "stats_fail": "❌ Неуспешные: {n} ({p}%)",
        "stats_doubt": "❓ Под вопросом: {n} ({p}%)",
        "stats_avg": "⭐ Средний балл: {x}/10",
        # статусы звонка amoCRM (полные / короткие)
        "cs_label_1": "📞 Планируется", "cs_short_1": "план",
        "cs_label_2": "📅 Запланирован", "cs_short_2": "запл.",
        "cs_label_3": "🔄 Совершён", "cs_short_3": "сов.",
        "cs_label_4": "✅ Разговор", "cs_short_4": "разг.",
        "cs_label_5": "📳 Пропущен", "cs_short_5": "проп.",
        "cs_label_6": "❌ Недозвон", "cs_short_6": "недозв.",
        "cs_label_7": "🚫 Нет соединения", "cs_short_7": "нет соед.",
        # мастер подключения amoCRM
        "amo_intro": "🔌 Подключаем ваш amoCRM. Отправляйте значения по одному сообщению.",
        "amo_secret": "Шаг 1 из 3 — секретный ключ интеграции amoCRM:",
        "amo_integration_id": "Шаг 2 из 3 — ID интеграции:",
        "amo_token": "Шаг 3 из 3 — долгосрочный токен (длинный, начинается на eyJ...):",
        "amo_host": "Шаг 4 из 4 — адрес вашего amoCRM (например: topextexnikum.amocrm.ru):",
        "amo_checking": "⏳ Проверяю подключение к {host}...",
        "amo_connected": "✅ Подключено: {name}\n\nБот следит за новыми звонками. /menu — меню, /connect — сменить аккаунт.",
        "amo_fail": "❌ Не удалось подключиться к {host}.\n{err}\n\nПроверьте токен и адрес, затем отправьте /connect, чтобы ввести заново.",
    },
    "uz": {
        "menu_title": (
            "📋 Asosiy menyu\n\n"
            "👥 Xodimlar — menejerni tanlang, uning qo‘ng‘iroqlari, AI tahlili va statistikasini ko‘ring.\n"
            "📈 Kunlik hisobot — nechta mijozga xizmat ko‘rsatilgani, kun eng yaxshisi, xatolar va har bir "
            "xodimga vazifa (har kuni soat 20:00 da avtomatik keladi).\n"
            "📊 Umumiy statistika — butun bo‘lim natijalari.\n\n"
            "🎧 Shuningdek shu yerga qo‘ng‘iroq yozuvini yoki matnini yuborsangiz — darrov tahlil qilaman."
        ),
        "btn_employees": "👥 Xodimlar",
        "btn_daily": "📈 Kunlik hisobot",
        "btn_stats": "📊 Umumiy statistika",
        "btn_search": "🔍 Xodimni qidirish",
        "btn_back_menu": "⬅️ Menyu",
        "btn_menu": "📋 Menyu",
        "btn_back_calls": "⬅️ Xodim qo‘ng‘iroqlariga",
        "btn_back_employees": "👥 Xodimlarga",
        "btn_to_employee": "⬅️ Xodimga",
        "btn_pick_date": "📅 Sana tanlash",
        "btn_other_date": "📅 Boshqa sana",
        "btn_back": "⬅️ Orqaga",
        "btn_audio_review": "📋 Audio + tahlil",
        "lang_switched": "🌐 Til o‘zbekchaga o‘tkazildi.",
        "employees_title": "👥 Xodimlar (qavs ichida — tahlil qilingan qo‘ng‘iroqlar soni):",
        "employees_empty": (
            "Hozircha na xodim, na tahlil qilingan qo‘ng‘iroq bor.\n\n"
            "Shu yerga qo‘ng‘iroq yozuvini yuboring — yoki AmoCRM’dan yangi qo‘ng‘iroqni kuting."
        ),
        "search_prompt": "🔍 Xodim ismini (yoki bir qismini) kiriting:",
        "search_none": "So‘rov bo‘yicha hech kim topilmadi: ",
        "search_title": "🔍 «{q}» bo‘yicha topildi:",
        "mgr_default_name": "Xodim",
        "mgr_no_calls": "Hozircha tahlil qilingan qo‘ng‘iroq yo‘q.",
        "calls_pick_hint": (
            "Qo‘ng‘iroqni tanlang (✅❌❓ — tahlil qilingan: audio + PDF, "
            "⬜ — yangi: bosilganda tahlil qilaman):"
        ),
        "calls_none_crm": "CRM’da yozuvli qo‘ng‘iroqlar hozircha ko‘rinmayapti.",
        "no_number": "raqamsiz",
        "dates_pick": "📅 Sanani tanlang — o‘sha kungi barcha suhbatlarni ko‘rsataman:",
        "no_calls_yet": "Hozircha qo‘ng‘iroq yo‘q",
        "no_calls_day": "{day} kuni qo‘ng‘iroq yo‘q",
        "day_calls_header": (
            "👨‍💼 {name} • 📅 {day}\n\n"
            "Shu kungi suhbatlar ({n}):\n"
            "✅❌❓ — tahlil qilingan, ⬜ — bosilganda tahlil qilaman"
        ),
        "analyzing_short": "Qo‘ng‘iroqni tahlil qilyapman...",
        "downloading": "🎧 Yozuvni yuklab olyapman, matnga o‘giryapman va PDF tayyorlayapman (1-2 daqiqa)...",
        "call_not_found_crm": "❌ Qo‘ng‘iroq CRM’da topilmadi (eskirgan bo‘lishi mumkin). Xodim kartasini qayta oching.",
        "analyze_failed": "⚠️ Qo‘ng‘iroqni tahlil qilib bo‘lmadi (nutq yo‘q yoki yozuv xatosi).",
        "error_generic": "❌ Xatolik: {err}",
        "call_not_found": "Qo‘ng‘iroq topilmadi.",
        "audio_unavailable": "(audio yozuvi mavjud emas)",
        "transcript_title": "📃 Suhbatning to‘liq matni (so‘zma-so‘z, yozib olinganidek):\n\n{text}",
        "transcript_empty": "Matn yozuvi mavjud emas.",
        "report_empty": "Hisobot mavjud emas.",
        "stats_dept_title": "📊 Bo‘lim umumiy statistikasi\n",
        "stats_by_employee": "\n👥 Xodimlar bo‘yicha:",
        "calls_short": "qo‘ng‘.",
        "avg_score_suffix": ", o‘rtacha ball {x}/10",
        "daily_building": "📈 Kunlik umumiy hisobotni yig‘yapman...",
        "daily_empty": "Bugun hali biror tahlil qilingan qo‘ng‘iroq yo‘q — qo‘ng‘iroqlar paydo bo‘lganda hisobot bo‘ladi.",
        "daily_error": "❌ Hisobot tuzishda xatolik: {err}",
        "daily_auto_header": "🌙 Avtomatik kunlik hisobot:",
        "status_amo_ok": "🟢 AmoCRM ulangan: {name} (har {sec} soniyada tekshiriladi)",
        "status_amo_err": "🔴 AmoCRM: ulanish xatosi — {err}",
        "status_amo_off": "⚪ AmoCRM ulanmagan. Akkauntingizni ulash uchun /connect yuboring.",
        "status_body": (
            "📡 Bot holati\n\n{amo}\n"
            "⏱ Qo‘ng‘iroqning minimal davomiyligi: {sec} soniya\n"
            "💾 Bazadagi qo‘ng‘iroqlar: {n}"
        ),
        "private_bot": "⛔ Bot yopiq. Agar egasi bo‘lsangiz, /start yuboring.",
        "auditing": "🧠 Qo‘ng‘iroqni qat’iy tahlil qilyapman...",
        "send_audio_hint": "Audio fayl (mp3/wav/ogg/m4a), ovozli xabar yoki matnli .txt yuboring.",
        "file_too_big": "⚠️ Fayl 20 MB dan katta — Telegram botlarga bunday fayllarni yuklab olishga ruxsat bermaydi. Yozuvni siqing yoki qismlarga bo‘lib yuboring.",
        "got_recording": "🎧 Yozuvni oldim. Matnga o‘giryapman...",
        "no_speech": "⚠️ Yozuvda deyarli nutq yo‘q — tahlil qiladigan narsa yo‘q.",
        "transcribed_auditing": "🧠 Matnga o‘girdim. Qo‘ng‘iroqni qat’iy tahlil qilyapman...",
        "send_call_hint": (
            "Qo‘ng‘iroq yozuvini (audio/ovozli) yoki to‘liq matnini "
            "(100 belgidan kam bo‘lmagan) yuboring.\n\nMenyu: /menu"
        ),
        "pdf_caption": "📄 Qo‘ng‘iroqning to‘liq tahlili (PDF)",
        "doc_unavailable": "Bu qo‘ng‘iroq uchun tahlil mavjud emas.",
        "owner_assigned": "✅ Siz bot egasi etib tayinlandingiz.",
        "private_taken": "⛔ Bot yopiq va allaqachon boshqa foydalanuvchiga bog‘langan.",
        "preparing_report": "Hisobot tayyorlayapman...",
        "choose_lang": "🌐 Tilni tanlang:",
        "pdf_title": "Qo‘ng‘iroq tahlili — {name}",
        "pdf_score": "Baho",
        "wd_0": "Du", "wd_1": "Se", "wd_2": "Ch", "wd_3": "Pa", "wd_4": "Ju", "wd_5": "Sh", "wd_6": "Ya",
        "stats_total": "📞 Jami qo‘ng‘iroqlar: {n}",
        "stats_ok": "✅ Muvaffaqiyatli: {n} ({p}%)",
        "stats_fail": "❌ Muvaffaqiyatsiz: {n} ({p}%)",
        "stats_doubt": "❓ Shubhali: {n} ({p}%)",
        "stats_avg": "⭐ O‘rtacha ball: {x}/10",
        "cs_label_1": "📞 Rejalashtirilgan", "cs_short_1": "reja",
        "cs_label_2": "📅 Rejada", "cs_short_2": "rejada",
        "cs_label_3": "🔄 Amalga oshgan", "cs_short_3": "bajar.",
        "cs_label_4": "✅ Suhbat", "cs_short_4": "suhbat",
        "cs_label_5": "📳 O‘tkazib yuborilgan", "cs_short_5": "o‘tk.",
        "cs_label_6": "❌ Javob yo‘q", "cs_short_6": "javob yo‘q",
        "cs_label_7": "🚫 Aloqa yo‘q", "cs_short_7": "aloqa yo‘q",
        "amo_intro": "🔌 amoCRM'ni ulaymiz. Qiymatlarni bittadan xabar qilib yuboring.",
        "amo_secret": "1-qadam / 3 — amoCRM integratsiyasining maxfiy kaliti:",
        "amo_integration_id": "2-qadam / 3 — integratsiya ID si:",
        "amo_token": "3-qadam / 3 — uzoq muddatli token (uzun, eyJ... bilan boshlanadi):",
        "amo_host": "4-qadam / 4 — amoCRM manzilingiz (masalan: topextexnikum.amocrm.ru):",
        "amo_checking": "⏳ {host} ga ulanishni tekshiryapman...",
        "amo_connected": "✅ Ulandi: {name}\n\nBot yangi qo‘ng‘iroqlarni kuzatadi. /menu — menyu, /connect — akkauntni almashtirish.",
        "amo_fail": "❌ {host} ga ulab bo‘lmadi.\n{err}\n\nToken va manzilni tekshiring, so‘ng qayta kiritish uchun /connect yuboring.",
    },
    "en": {
        "menu_title": (
            "📋 Main menu\n\n"
            "👥 Employees — pick a manager, see their calls, the AI review and stats.\n"
            "📈 Daily report — how many clients were served, top of the day, systemic mistakes and a task "
            "for each employee (arrives automatically at 20:00).\n"
            "📊 Overall stats — results for the whole team.\n\n"
            "🎧 You can also just send a call recording or a transcript here — I'll audit it right away."
        ),
        "btn_employees": "👥 Employees",
        "btn_daily": "📈 Daily report",
        "btn_stats": "📊 Overall stats",
        "btn_search": "🔍 Find employee",
        "btn_back_menu": "⬅️ Menu",
        "btn_menu": "📋 Menu",
        "btn_back_calls": "⬅️ Back to calls",
        "btn_back_employees": "👥 Back to employees",
        "btn_to_employee": "⬅️ Back to employee",
        "btn_pick_date": "📅 Pick a date",
        "btn_other_date": "📅 Another date",
        "btn_back": "⬅️ Back",
        "btn_audio_review": "📋 Audio + review",
        "lang_switched": "🌐 Language switched to English.",
        "employees_title": "👥 Employees (in brackets — number of analyzed calls):",
        "employees_empty": (
            "No employees or analyzed calls yet.\n\n"
            "Send a call recording here — or wait for a new call from AmoCRM."
        ),
        "search_prompt": "🔍 Enter the employee's name (or part of it):",
        "search_none": "Nobody found for: ",
        "search_title": "🔍 Found for «{q}»:",
        "mgr_default_name": "Employee",
        "mgr_no_calls": "No analyzed calls yet.",
        "calls_pick_hint": (
            "Pick a call (✅❌❓ — already analyzed: audio + PDF, "
            "⬜ — new: I'll analyze it on tap):"
        ),
        "calls_none_crm": "No calls with a recording in the CRM yet.",
        "no_number": "no number",
        "dates_pick": "📅 Pick a date — I'll show all conversations for that day:",
        "no_calls_yet": "No calls yet",
        "no_calls_day": "No calls on {day}",
        "day_calls_header": (
            "👨‍💼 {name} • 📅 {day}\n\n"
            "Conversations for this day ({n}):\n"
            "✅❌❓ — analyzed, ⬜ — I'll analyze on tap"
        ),
        "analyzing_short": "Analyzing the call...",
        "downloading": "🎧 Downloading the recording, transcribing and preparing a PDF (1-2 minutes)...",
        "call_not_found_crm": "❌ Call not found in the CRM (it may be outdated). Open the employee card again.",
        "analyze_failed": "⚠️ Could not analyze the call (no speech or a recording error).",
        "error_generic": "❌ Error: {err}",
        "call_not_found": "Call not found.",
        "audio_unavailable": "(audio recording unavailable)",
        "transcript_title": "📃 Full text of the conversation (verbatim, as recorded):\n\n{text}",
        "transcript_empty": "No transcript available.",
        "report_empty": "No report available.",
        "stats_dept_title": "📊 Overall team stats\n",
        "stats_by_employee": "\n👥 By employee:",
        "calls_short": "calls",
        "avg_score_suffix": ", avg {x}/10",
        "daily_building": "📈 Building the daily overall report...",
        "daily_empty": "No analyzed calls yet today — the report will appear once there are calls.",
        "daily_error": "❌ Error while building the report: {err}",
        "daily_auto_header": "🌙 Automatic daily report:",
        "status_amo_ok": "🟢 AmoCRM connected: {name} (checked every {sec} sec)",
        "status_amo_err": "🔴 AmoCRM: connection error — {err}",
        "status_amo_off": "⚪ AmoCRM not connected. Send /connect to connect your account.",
        "status_body": (
            "📡 Bot status\n\n{amo}\n"
            "⏱ Minimum call duration: {sec} sec\n"
            "💾 Calls in the database: {n}"
        ),
        "private_bot": "⛔ The bot is private. Send /start if you are the owner.",
        "auditing": "🧠 Running a strict audit of the call...",
        "send_audio_hint": "Send an audio file (mp3/wav/ogg/m4a), a voice message or a .txt transcript.",
        "file_too_big": "⚠️ The file is over 20 MB — Telegram doesn't let bots download such files. Compress the recording or send it in parts.",
        "got_recording": "🎧 Got the recording. Transcribing...",
        "no_speech": "⚠️ Almost no speech in the recording — nothing to analyze.",
        "transcribed_auditing": "🧠 Transcribed. Running a strict audit of the call...",
        "send_call_hint": (
            "Send a call recording (audio/voice) or the full transcript "
            "(at least 100 characters).\n\nMenu: /menu"
        ),
        "pdf_caption": "📄 Full call review (PDF)",
        "doc_unavailable": "No review available for this call.",
        "owner_assigned": "✅ You are set as the bot owner.",
        "private_taken": "⛔ The bot is private and already linked to another user.",
        "preparing_report": "Preparing the report...",
        "choose_lang": "🌐 Choose a language:",
        "pdf_title": "Call review — {name}",
        "pdf_score": "Score",
        "wd_0": "Mon", "wd_1": "Tue", "wd_2": "Wed", "wd_3": "Thu", "wd_4": "Fri", "wd_5": "Sat", "wd_6": "Sun",
        "stats_total": "📞 Total calls: {n}",
        "stats_ok": "✅ Successful: {n} ({p}%)",
        "stats_fail": "❌ Failed: {n} ({p}%)",
        "stats_doubt": "❓ Doubtful: {n} ({p}%)",
        "stats_avg": "⭐ Average score: {x}/10",
        "cs_label_1": "📞 Planned", "cs_short_1": "plan",
        "cs_label_2": "📅 Scheduled", "cs_short_2": "sched.",
        "cs_label_3": "🔄 Completed", "cs_short_3": "done",
        "cs_label_4": "✅ Conversation", "cs_short_4": "talk",
        "cs_label_5": "📳 Missed", "cs_short_5": "missed",
        "cs_label_6": "❌ No answer", "cs_short_6": "no ans.",
        "cs_label_7": "🚫 No connection", "cs_short_7": "no conn.",
        "amo_intro": "🔌 Let's connect your amoCRM. Send the values one message at a time.",
        "amo_secret": "Step 1 of 3 — the amoCRM integration secret key:",
        "amo_integration_id": "Step 2 of 3 — the integration ID:",
        "amo_token": "Step 3 of 3 — the long-lived token (long, starts with eyJ...):",
        "amo_host": "Step 4 of 4 — your amoCRM address (for example: topextexnikum.amocrm.ru):",
        "amo_checking": "⏳ Checking the connection to {host}...",
        "amo_connected": "✅ Connected: {name}\n\nThe bot is now watching new calls. /menu — menu, /connect — change account.",
        "amo_fail": "❌ Couldn't connect to {host}.\n{err}\n\nCheck the token and address, then send /connect to enter them again.",
    },
}


def t(lang: str, key: str, **fmt) -> str:
    """Строка для языка lang; фолбэк на RU, затем на сам ключ. fmt — для .format()."""
    ru = I18N["ru"]
    s = I18N.get(lang, ru).get(key) or ru.get(key) or key
    return s.format(**fmt) if fmt else s
