"""Тексты интерфейса на двух языках. Язык владельца хранится в state.json."""

import state

DEFAULT_LANG = "ru"

LANGUAGES = {"ru": "🇷🇺 Русский", "uz": "🇺🇿 O'zbekcha", "en": "🇬🇧 English"}

TEXTS = {
    "ru": {
        # --- меню и кнопки ---
        "menu_title": "📋 Главное меню",
        "btn_managers": "👥 Сотрудники",
        "btn_daily": "📈 Отчёт за день",
        "btn_stats": "📊 Общая статистика",
        "btn_language": "🌐 Язык / Til",
        "btn_menu": "⬅️ Меню",
        "btn_menu_plain": "📋 Меню",
        "btn_back": "⬅️ Назад",
        "btn_to_managers": "👥 К сотрудникам",
        "btn_to_manager": "⬅️ К сотруднику",
        "btn_to_calls": "⬅️ К звонкам сотрудника",
        "btn_pick_date": "📅 Выбрать дату",
        "btn_other_date": "📅 Другая дата",
        "btn_search": "🔍 Поиск по имени",
        "btn_audio_tz": "📋 Аудио + ТЗ (узбекча)",
        "menu_text": (
            "📋 Главное меню\n\n"
            "👥 Сотрудники — выберите менеджера, посмотрите его звонки, разбор AI и статистику.\n"
            "📈 Отчёт за день — сколько клиентов обслужили, топ дня, системные ошибки и ТЗ "
            "каждому сотруднику (автоматически приходит в 20:00).\n"
            "📊 Общая статистика — итоги по всему отделу.\n\n"
            "🎧 Также можно просто прислать сюда запись звонка или текст расшифровки — "
            "я сразу сделаю аудит."
        ),
        # --- доступ ---
        "owner_set": "✅ Вы назначены владельцем бота.",
        "private_bot": "⛔ Бот приватный и уже привязан к другому пользователю.",
        "private_hint": "⛔ Бот приватный. Отправьте /start, если вы владелец.",
        # --- язык ---
        "lang_prompt": "🌐 Выберите язык интерфейса:",
        "lang_changed": "✅ Язык интерфейса: Русский",
        # --- статус ---
        "status_title": "📡 Статус бота",
        "status_amo_ok": "🟢 AmoCRM подключён: {name} (проверка каждые {interval} сек)",
        "status_amo_error": "🔴 AmoCRM: ошибка подключения — {error}",
        "status_amo_off": (
            "⚪ AmoCRM не подключён (ручной режим). "
            "Добавьте AMO_SUBDOMAIN и AMO_ACCESS_TOKEN в файл .env"
        ),
        "status_min_duration": "⏱ Минимальная длительность звонка: {seconds} сек",
        "status_db_calls": "💾 Звонков в базе: {total}",
        # --- сотрудники ---
        "managers_title": "👥 Сотрудники (в скобках — количество разобранных звонков):",
        "managers_empty": (
            "Пока нет ни сотрудников, ни разобранных звонков.\n\n"
            "Пришлите запись звонка сюда — или дождитесь нового звонка из AmoCRM."
        ),
        "manager_unknown": "Сотрудник",
        "manager_no_calls": "Разобранных звонков пока нет.",
        "manager_pick_call": (
            "Выберите звонок (✅❌❓ — уже разобран: аудио + PDF, "
            "⬜ — новый: разберу при нажатии):"
        ),
        "manager_no_crm_calls": "Звонков с записью в CRM пока не видно.",
        "no_phone": "без номера",
        "dur_min": "м",
        "dur_sec": "с",
        # направление звонка хранится в базе по-русски — переводим только на показ
        "direction_in": "Входящий",
        "direction_out": "Исходящий",
        # --- поиск ---
        "search_prompt": (
            "🔍 Введите имя сотрудника (или его часть) — покажу подходящих.\n\n"
            "Отменить: /menu"
        ),
        "search_none": "🔍 По запросу «{query}» никого не нашёл. Попробуйте другую часть имени.",
        "search_results": "🔍 Нашёл по запросу «{query}» ({count}):",
        # --- даты ---
        "dates_title": "📅 Выберите дату — покажу все разговоры за этот день:",
        "dates_empty": "Звонков пока нет",
        "day_empty": "За {day} звонков нет",
        "day_title": (
            "👨‍💼 {name} • 📅 {day}\n\n"
            "Разговоры за этот день ({count}):\n"
            "✅❌❓ — разобраны, ⬜ — разберу при нажатии"
        ),
        "day_calls_label": "📅 {date} ({weekday}) • {count} зв.",
        "weekdays": ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"],
        # --- разбор звонка ---
        "analyzing": "Разбираю звонок...",
        "analyzing_long": "🎧 Скачиваю запись, расшифровываю и готовлю PDF (1-2 минуты)...",
        "report_title": "🧠 Разбор звонка (диалог, ошибки и оценка AI):",
        "call_not_in_crm": (
            "❌ Звонок не найден в CRM (возможно, устарел). "
            "Откройте карточку сотрудника заново."
        ),
        "call_not_analyzed": "⚠️ Не удалось разобрать звонок (нет речи или ошибка записи).",
        "call_not_found": "Звонок не найден.",
        "audio_unavailable": "(аудиозапись недоступна)",
        "tz_unavailable": "ТЗ недоступно для этого звонка.",
        "report_missing": "Отчёт отсутствует.",
        "transcript_missing": "Текст расшифровки отсутствует.",
        "transcript_title": "📃 Полный текст разговора (дословно, как записано):",
        "pdf_failed": "⚠️ PDF-отчёт собрать не удалось: {error}",
        "error": "❌ Ошибка: {error}",
        # --- PDF ---
        "pdf_title": "Разбор звонка",
        "pdf_manager": "Сотрудник: {name}",
        "pdf_date": "Дата: {date} • {direction} • {duration}",
        "pdf_score": "Оценка: {score}",
        "pdf_phone": "Телефон клиента: {phone}",
        "pdf_card": "Карточка в CRM: {url}",
        "pdf_uz_section": "ТЗ ДЛЯ СОТРУДНИКА (НА УЗБЕКСКОМ)",
        # --- статистика ---
        "stats_title": "📊 Общая статистика отдела\n",
        "stats_by_manager": "\n👥 По сотрудникам:",
        "stats_total": "📞 Всего звонков: {total}",
        "stats_answered": "☎️ Отвечено (был разговор): {answered}",
        "stats_ok": "✅ Успешные: {count} ({percent}% отвеченных)",
        "stats_fail": "❌ Неуспешные: {count} ({percent}% отвеченных)",
        "stats_doubt": "❓ Под вопросом: {count} ({percent}% отвеченных)",
        "stats_noanswer": "📵 Недозвон / не взяли трубку: {count}",
        "stats_avg": "⭐ Средний балл: {avg}/10",
        "stats_manager_line": "• {name}: {total} зв. (☎️{answered}/📵{noanswer}), ✅{ok}% ❌{fail}% ❓{doubt}%{avg}",
        "stats_manager_avg": ", ср. балл {avg}/10",
        # --- отчёт за день ---
        "daily_preparing": "Готовлю отчёт...",
        "daily_building": "📈 Собираю общий отчёт за день...",
        "daily_empty": (
            "За сегодня пока нет ни одного разобранного звонка — отчёт будет, "
            "когда появятся звонки."
        ),
        "daily_error": "❌ Ошибка при построении отчёта: {error}",
        "daily_auto": "🌙 Автоматический отчёт за день:",
        # --- ручная загрузка ---
        "manual_auditing": "🧠 Провожу жёсткий аудит звонка...",
        "manual_got_audio": "🎧 Получил запись. Расшифровываю...",
        "manual_transcribed": "🧠 Расшифровал. Провожу жёсткий аудит звонка...",
        "manual_no_speech": "⚠️ В записи почти нет речи — нечего анализировать.",
        "manual_send_audio": (
            "Пришлите аудиофайл (mp3/wav/ogg/m4a), голосовое или .txt с расшифровкой."
        ),
        "manual_too_big": (
            "⚠️ Файл больше 20 МБ — Telegram не даёт ботам скачивать такие файлы. "
            "Сожмите запись или пришлите частями."
        ),
        "manual_text_short": (
            "Пришлите запись звонка (аудио/голосовое) или полный текст расшифровки "
            "(не короче 100 символов).\n\nМеню: /menu"
        ),
        # --- статусы звонка ---
        "call_status_labels": {
            1: "📞 Планируется",
            2: "📅 Запланирован",
            3: "🔄 Совершён",
            4: "✅ Разговор",
            5: "📳 Пропущен",
            6: "❌ Недозвон",
            7: "🚫 Нет соединения",
        },
        "call_status_short": {
            1: "план",
            2: "запл.",
            3: "сов.",
            4: "разг.",
            5: "проп.",
            6: "недозв.",
            7: "нет соед.",
        },
        # --- авторизация и роли (auth.py вошло в main.py — текст сверен с реальным флоу 2026-08-05) ---
        "auth_login_prompt": "🔑 Введите логин:",
        "auth_password_prompt": "🔒 Введите пароль (сообщение будет удалено после проверки):",
        "auth_failed": "❌ Неверный логин или пароль.",
        "auth_inactive": "⛔ Ваш аккаунт отключён. Обратитесь к руководителю.",
        "auth_success": "✅ Добро пожаловать, {name}! Роль: {role}",
        "auth_logged_out": "👋 Вы вышли из аккаунта.",
        "auth_not_logged_in": "🔒 Сначала войдите: /login",
        "auth_no_access": "🚫 У вас нет доступа к этому разделу.",
        "role_operator": "Оператор",
        "role_rop": "РОП",
        "role_director": "Директор",
        "role_owner": "Владелец",
        "auth_already_logged": "Вы уже вошли как {name} ({role}). Сменить: /logout",
        "auth_operator_unbound": (
            "⚠️ Ваша учётка ещё не привязана к оператору в amoCRM — звонков не видно.\n"
            "Попросите руководителя выполнить: /bind <ваш логин> <id в amoCRM>"
        ),
        "auth_login_hint": "🔒 Вход: /login — или /login <логин> <пароль> одной строкой.",
        # --- экраны по ролям (директор / РОП / оператор) ---
        "menu_role_line": "👤 {name} • {role}{branch}",
        "menu_branch_suffix": " • филиал: {branch}",
        "menu_text_rop": (
            "📋 Меню РОПа\n\n"
            "👥 Мои операторы — рейтинг операторов филиала, их звонки и разбор AI.\n"
            "📊 Статистика филиала — итоги по вашему филиалу.\n"
            "⚠️ Ошибки филиала — звонки, где операторы ошиблись.\n"
            "📈 Отчёт за день — по вашему филиалу."
        ),
        "menu_text_operator": (
            "📋 Моё меню\n\n"
            "📞 Мои звонки — список ваших разговоров с оценкой и разбором AI.\n"
            "📊 Моя статистика — успешные / неуспешные / недозвоны и средний балл.\n"
            "⚠️ Мои ошибки — звонки, где AI нашёл ошибки: что именно и как исправить.\n"
            "📈 Мой отчёт за день — итоги вашего дня."
        ),
        "btn_branches": "🏢 Сводка по филиалам",
        "btn_branch_stats": "📊 Статистика филиала",
        "btn_branch_team": "👥 Мои операторы",
        "btn_dept_total": "📊 Итого по отделу",
        "btn_my_calls": "📞 Мои звонки",
        "btn_my_stats": "📊 Моя статистика",
        "btn_my_errors": "⚠️ Мои ошибки",
        "btn_errors": "⚠️ Ошибки",
        "btn_branch_errors": "⚠️ Ошибки филиала",
        "btn_to_branches": "⬅️ К филиалам",
        # сводка директора
        "branches_title": "🏢 Сводка по филиалам\n",
        "branches_empty": (
            "Филиалы ещё не заведены.\n\n"
            "Владелец: /branch_add <название> — создать филиал, "
            "/user_add — завести пользователя, /bind — привязать оператора к amoCRM."
        ),
        "branch_line": (
            "🏢 {name} — {operators} оп., {total} зв. (☎️{answered} / 📵{noanswer})\n"
            "   ✅{ok}% ❌{fail}% ❓{doubt}%{avg}"
        ),
        "branch_avg_suffix": " • ср. балл {avg}/10",
        "branch_no_calls": "   пока нет разобранных звонков",
        "branch_best": "🥇 Лучше всех: {name} ({avg}/10)",
        "branch_worst": "🔻 Слабее всех: {name} ({avg}/10)",
        "branch_unassigned": "\n⚠️ Операторов без филиала: {count} (привязать: /bind)",
        "branch_title": "🏢 {name}\n",
        "branch_no_operators": (
            "В этом филиале ещё нет привязанных операторов.\n"
            "Владелец: /user_add <логин> <пароль> operator <id филиала> <id в amoCRM> <ФИО>"
        ),
        "branch_pick_operator": "\n👥 Операторы (нажмите — звонки и разбор):",
        "branch_not_found": "Филиал не найден.",
        "rop_no_branch": (
            "⚠️ К вашей учётке не привязан филиал. Обратитесь к владельцу бота."
        ),
        # экран оператора
        "my_stats_title": "👤 {name} — моя статистика\n",
        "my_no_calls": "Разобранных звонков пока нет.",
        # ошибки
        "errors_title": "⚠️ Звонки с ошибками (❌ неуспешные и ❓ под вопросом)",
        "errors_hint": "Откройте звонок — в разборе AI указано, где именно ошибка.",
        "errors_empty": "✅ Звонков с ошибками не найдено.",
        # отчёт за день по ролям
        "daily_scope_all": "📈 Отчёт за день — весь отдел",
        "daily_scope_branch": "📈 Отчёт за день — филиал «{branch}»",
        "daily_scope_own": "📈 Отчёт за день — {name}",
        "daily_empty_scoped": "За сегодня у вас пока нет разобранных звонков.",
        # --- команды владельца (настройка ролей) ---
        "admin_only": "🚫 Команда доступна только владельцу бота.",
        "admin_usage_branch_add": "Использование: /branch_add <название филиала>",
        "admin_branch_added": "✅ Филиал «{name}» заведён (id={id}).",
        "admin_branches": "🏢 Филиалы (id — название — операторов):",
        "admin_branches_empty": "Филиалов пока нет. Создать: /branch_add <название>",
        "admin_usage_user_add": (
            "Использование:\n"
            "/user_add <логин> <пароль> <роль> <id филиала|-> <amo_id|-> <ФИО>\n\n"
            "Роли: operator, rop, director, owner\n"
            "Примеры:\n"
            "/user_add boss 1234 director - - Директор Topex\n"
            "/user_add rop1 1234 rop 1 - РОП Юнусабада\n"
            "/user_add durdona 1234 operator 1 6284739 Durdona"
        ),
        "admin_user_added": "✅ {login} — {role} {extra} заведён(а).",
        "admin_user_exists": "⚠️ Логин {login} уже занят.",
        "admin_users": "👤 Пользователи (логин — роль — филиал — amo_id):",
        "admin_users_empty": "Пользователей пока нет. Завести: /user_add",
        "admin_user_not_found": "⚠️ Пользователь «{login}» не найден.",
        "admin_bad_role": "⚠️ Роль должна быть одной из: operator, rop, director, owner.",
        "admin_bad_branch": "⚠️ Филиал с id={id} не найден. Список: /branches",
        "admin_usage_bind": "Использование: /bind <логин> <id оператора в amoCRM>",
        "admin_bound": "✅ {login} привязан к оператору amoCRM id={amo_id}.",
        "admin_usage_passwd": "Использование: /passwd <логин> <новый пароль>",
        "admin_passwd_ok": "✅ Пароль для {login} обновлён.",
        "admin_usage_access": "Использование: /user_off <логин> или /user_on <логин>",
        "admin_access_on": "✅ {login}: доступ включён.",
        "admin_access_off": "⛔ {login}: доступ отключён.",
        "admin_amo_ids": "🆔 Сотрудники amoCRM (id — имя — разобранных звонков):",
        "admin_amo_ids_empty": "Сотрудники из amoCRM не получены (CRM не подключена?).",
        "admin_inactive_mark": " (отключён)",
    },
    "uz": {
        # --- menyu va tugmalar ---
        "menu_title": "📋 Asosiy menyu",
        "btn_managers": "👥 Xodimlar",
        "btn_daily": "📈 Kunlik hisobot",
        "btn_stats": "📊 Umumiy statistika",
        "btn_language": "🌐 Til / Язык",
        "btn_menu": "⬅️ Menyu",
        "btn_menu_plain": "📋 Menyu",
        "btn_back": "⬅️ Orqaga",
        "btn_to_managers": "👥 Xodimlarga",
        "btn_to_manager": "⬅️ Xodimga",
        "btn_to_calls": "⬅️ Xodim qo'ng'iroqlariga",
        "btn_pick_date": "📅 Sanani tanlash",
        "btn_other_date": "📅 Boshqa sana",
        "btn_search": "🔍 Ism bo'yicha qidirish",
        "btn_audio_tz": "📋 Audio + TZ (o'zbekcha)",
        "menu_text": (
            "📋 Asosiy menyu\n\n"
            "👥 Xodimlar — menejerni tanlang, uning qo'ng'iroqlari, AI tahlili va "
            "statistikasini ko'ring.\n"
            "📈 Kunlik hisobot — nechta mijozga xizmat ko'rsatildi, kun eng yaxshisi, "
            "tizimli xatolar va har bir xodimga TZ (har kuni 20:00 da avtomatik keladi).\n"
            "📊 Umumiy statistika — butun bo'lim natijalari.\n\n"
            "🎧 Shuningdek, shu yerga qo'ng'iroq yozuvini yoki transkript matnini "
            "yuborsangiz — darhol audit qilaman."
        ),
        # --- kirish huquqi ---
        "owner_set": "✅ Siz bot egasi etib tayinlandingiz.",
        "private_bot": "⛔ Bot shaxsiy va allaqachon boshqa foydalanuvchiga biriktirilgan.",
        "private_hint": "⛔ Bot shaxsiy. Agar egasi bo'lsangiz, /start yuboring.",
        # --- til ---
        "lang_prompt": "🌐 Interfeys tilini tanlang:",
        "lang_changed": "✅ Interfeys tili: O'zbekcha",
        # --- holat ---
        "status_title": "📡 Bot holati",
        "status_amo_ok": "🟢 AmoCRM ulangan: {name} (har {interval} soniyada tekshiriladi)",
        "status_amo_error": "🔴 AmoCRM: ulanish xatosi — {error}",
        "status_amo_off": (
            "⚪ AmoCRM ulanmagan (qo'lda rejim). "
            ".env fayliga AMO_SUBDOMAIN va AMO_ACCESS_TOKEN qo'shing"
        ),
        "status_min_duration": "⏱ Qo'ng'iroqning eng kam davomiyligi: {seconds} soniya",
        "status_db_calls": "💾 Bazadagi qo'ng'iroqlar: {total}",
        # --- xodimlar ---
        "managers_title": "👥 Xodimlar (qavs ichida — tahlil qilingan qo'ng'iroqlar soni):",
        "managers_empty": (
            "Hozircha na xodim, na tahlil qilingan qo'ng'iroq bor.\n\n"
            "Bu yerga qo'ng'iroq yozuvini yuboring — yoki AmoCRM'dan yangi qo'ng'iroqni kuting."
        ),
        "manager_unknown": "Xodim",
        "manager_no_calls": "Hozircha tahlil qilingan qo'ng'iroq yo'q.",
        "manager_pick_call": (
            "Qo'ng'iroqni tanlang (✅❌❓ — tahlil qilingan: audio + PDF, "
            "⬜ — yangi: bosganda tahlil qilaman):"
        ),
        "manager_no_crm_calls": "CRM'da yozuvli qo'ng'iroqlar hozircha ko'rinmayapti.",
        "no_phone": "raqamsiz",
        "dur_min": "d",
        "dur_sec": "s",
        # qo'ng'iroq yo'nalishi bazada ruscha saqlanadi — faqat ko'rsatishda tarjima qilinadi
        "direction_in": "Kiruvchi",
        "direction_out": "Chiquvchi",
        # --- qidiruv ---
        "search_prompt": (
            "🔍 Xodim ismini (yoki bir qismini) yozing — mosini ko'rsataman.\n\n"
            "Bekor qilish: /menu"
        ),
        "search_none": "🔍 «{query}» bo'yicha hech kim topilmadi. Ismning boshqa qismini yozing.",
        "search_results": "🔍 «{query}» bo'yicha topildi ({count}):",
        # --- sanalar ---
        "dates_title": "📅 Sanani tanlang — o'sha kungi barcha suhbatlarni ko'rsataman:",
        "dates_empty": "Hozircha qo'ng'iroqlar yo'q",
        "day_empty": "{day} kuni qo'ng'iroq yo'q",
        "day_title": (
            "👨‍💼 {name} • 📅 {day}\n\n"
            "Shu kungi suhbatlar ({count}):\n"
            "✅❌❓ — tahlil qilingan, ⬜ — bosganda tahlil qilaman"
        ),
        "day_calls_label": "📅 {date} ({weekday}) • {count} qo'ng'.",
        "weekdays": ["Du", "Se", "Cho", "Pay", "Ju", "Sha", "Yak"],
        # --- qo'ng'iroq tahlili ---
        "analyzing": "Qo'ng'iroqni tahlil qilyapman...",
        "analyzing_long": (
            "🎧 Yozuvni yuklab olyapman, transkript qilyapman va PDF tayyorlayapman "
            "(1-2 daqiqa)..."
        ),
        "report_title": "🧠 Qo'ng'iroq tahlili (dialog, xatolar va AI bahosi):",
        "call_not_in_crm": (
            "❌ Qo'ng'iroq CRM'da topilmadi (eskirgan bo'lishi mumkin). "
            "Xodim kartasini qaytadan oching."
        ),
        "call_not_analyzed": (
            "⚠️ Qo'ng'iroqni tahlil qilib bo'lmadi (nutq yo'q yoki yozuvda xato)."
        ),
        "call_not_found": "Qo'ng'iroq topilmadi.",
        "audio_unavailable": "(audio yozuv mavjud emas)",
        "tz_unavailable": "Bu qo'ng'iroq uchun TZ mavjud emas.",
        "report_missing": "Hisobot yo'q.",
        "transcript_missing": "Transkript matni yo'q.",
        "transcript_title": "📃 Suhbatning to'liq matni (so'zma-so'z, yozilganidek):",
        "pdf_failed": "⚠️ PDF hisobotni tayyorlab bo'lmadi: {error}",
        "error": "❌ Xato: {error}",
        # --- PDF ---
        "pdf_title": "Qo'ng'iroq tahlili",
        "pdf_manager": "Xodim: {name}",
        "pdf_date": "Sana: {date} • {direction} • {duration}",
        "pdf_score": "Baho: {score}",
        "pdf_phone": "Mijoz telefoni: {phone}",
        "pdf_card": "CRM kartasi: {url}",
        "pdf_uz_section": "XODIM UCHUN TZ (O'ZBEKCHA)",
        # --- statistika ---
        "stats_title": "📊 Bo'lim umumiy statistikasi\n",
        "stats_by_manager": "\n👥 Xodimlar bo'yicha:",
        "stats_total": "📞 Jami qo'ng'iroqlar: {total}",
        "stats_answered": "☎️ Javob berilgan (suhbat bo'lgan): {answered}",
        "stats_ok": "✅ Muvaffaqiyatli: {count} ({percent}% javob berilgandan)",
        "stats_fail": "❌ Muvaffaqiyatsiz: {count} ({percent}% javob berilgandan)",
        "stats_doubt": "❓ Shubhali: {count} ({percent}% javob berilgandan)",
        "stats_noanswer": "📵 Ko'tarilmagan qo'ng'iroq: {count}",
        "stats_avg": "⭐ O'rtacha ball: {avg}/10",
        "stats_manager_line": "• {name}: {total} qo'ng'. (☎️{answered}/📵{noanswer}), ✅{ok}% ❌{fail}% ❓{doubt}%{avg}",
        "stats_manager_avg": ", o'rt. ball {avg}/10",
        # --- kunlik hisobot ---
        "daily_preparing": "Hisobot tayyorlanyapti...",
        "daily_building": "📈 Kunlik umumiy hisobotni yig'yapman...",
        "daily_empty": (
            "Bugun hali birorta ham tahlil qilingan qo'ng'iroq yo'q — "
            "qo'ng'iroqlar paydo bo'lgach hisobot tayyor bo'ladi."
        ),
        "daily_error": "❌ Hisobot tuzishda xato: {error}",
        "daily_auto": "🌙 Avtomatik kunlik hisobot:",
        # --- qo'lda yuklash ---
        "manual_auditing": "🧠 Qo'ng'iroqni qattiq audit qilyapman...",
        "manual_got_audio": "🎧 Yozuvni oldim. Transkript qilyapman...",
        "manual_transcribed": "🧠 Transkript tayyor. Qo'ng'iroqni qattiq audit qilyapman...",
        "manual_no_speech": "⚠️ Yozuvda deyarli nutq yo'q — tahlil qiladigan narsa yo'q.",
        "manual_send_audio": (
            "Audio fayl (mp3/wav/ogg/m4a), ovozli xabar yoki transkript .txt faylini yuboring."
        ),
        "manual_too_big": (
            "⚠️ Fayl 20 MB dan katta — Telegram botlarga bunday fayllarni yuklab olishga "
            "ruxsat bermaydi. Yozuvni siqing yoki bo'laklab yuboring."
        ),
        "manual_text_short": (
            "Qo'ng'iroq yozuvini (audio/ovozli) yoki transkriptning to'liq matnini "
            "(kamida 100 belgi) yuboring.\n\nMenyu: /menu"
        ),
        # --- qo'ng'iroq holatlari ---
        "call_status_labels": {
            1: "📞 Rejalashtirilmoqda",
            2: "📅 Rejalashtirilgan",
            3: "🔄 Amalga oshirilgan",
            4: "✅ Suhbat",
            5: "📳 O'tkazib yuborilgan",
            6: "❌ Javob bermadi",
            7: "🚫 Aloqa yo'q",
        },
        "call_status_short": {
            1: "reja",
            2: "rejal.",
            3: "amalg.",
            4: "suhb.",
            5: "o'tk.",
            6: "javobs.",
            7: "aloqa yo'q",
        },
        # --- avtorizatsiya va rollar (auth.py main.py'ga ulandi — matn real oqim bilan 2026-08-05 solishtirildi) ---
        "auth_login_prompt": "🔑 Login yuboring:",
        "auth_password_prompt": "🔒 Parolni yuboring (tekshiruvdan keyin xabar o'chiriladi):",
        "auth_failed": "❌ Login yoki parol xato.",
        "auth_inactive": "⛔ Hisobingiz faol emas. Rahbaringizga murojaat qiling.",
        "auth_success": "✅ Xush kelibsiz, {name}! Rol: {role}",
        "auth_logged_out": "👋 Hisobdan chiqdingiz.",
        "auth_not_logged_in": "🔒 Avval kiring: /login",
        "auth_no_access": "🚫 Sizda bu bo'limga ruxsat yo'q.",
        "role_operator": "Operator",
        "role_rop": "ROP",
        "role_director": "Direktor",
        "role_owner": "Egasi",
        "auth_already_logged": "Siz allaqachon {name} ({role}) sifatida kirgansiz. O'zgartirish: /logout",
        "auth_operator_unbound": (
            "⚠️ Hisobingiz amoCRM operatoriga bog'lanmagan — qo'ng'iroqlar ko'rinmaydi.\n"
            "Rahbaringizdan so'rang: /bind <loginingiz> <amoCRM id>"
        ),
        "auth_login_hint": "🔒 Kirish: /login — yoki bitta qatorda /login <login> <parol>.",
        # --- rollar bo'yicha ekranlar (direktor / ROP / operator) ---
        "menu_role_line": "👤 {name} • {role}{branch}",
        "menu_branch_suffix": " • filial: {branch}",
        "menu_text_rop": (
            "📋 ROP menyusi\n\n"
            "👥 Mening operatorlarim — filial operatorlari reytingi, qo'ng'iroqlari va AI tahlili.\n"
            "📊 Filial statistikasi — filialingiz bo'yicha yakun.\n"
            "⚠️ Filial xatolari — operatorlar xato qilgan qo'ng'iroqlar.\n"
            "📈 Kunlik hisobot — filialingiz bo'yicha."
        ),
        "menu_text_operator": (
            "📋 Mening menyum\n\n"
            "📞 Mening qo'ng'iroqlarim — suhbatlaringiz ro'yxati, baho va AI tahlili.\n"
            "📊 Mening statistikam — muvaffaqiyatli / muvaffaqiyatsiz / javobsiz va o'rtacha ball.\n"
            "⚠️ Mening xatolarim — AI xato topgan qo'ng'iroqlar: nima va qanday tuzatish kerak.\n"
            "📈 Kunlik hisobotim — kuningiz yakuni."
        ),
        "btn_branches": "🏢 Filiallar bo'yicha yakun",
        "btn_branch_stats": "📊 Filial statistikasi",
        "btn_branch_team": "👥 Mening operatorlarim",
        "btn_dept_total": "📊 Bo'lim bo'yicha jami",
        "btn_my_calls": "📞 Mening qo'ng'iroqlarim",
        "btn_my_stats": "📊 Mening statistikam",
        "btn_my_errors": "⚠️ Mening xatolarim",
        "btn_errors": "⚠️ Xatolar",
        "btn_branch_errors": "⚠️ Filial xatolari",
        "btn_to_branches": "⬅️ Filiallarga",
        # direktor yakuni
        "branches_title": "🏢 Filiallar bo'yicha yakun\n",
        "branches_empty": (
            "Filiallar hali kiritilmagan.\n\n"
            "Egasi uchun: /branch_add <nomi> — filial yaratish, "
            "/user_add — foydalanuvchi qo'shish, /bind — operatorni amoCRM'ga bog'lash."
        ),
        "branch_line": (
            "🏢 {name} — {operators} operator, {total} qo'ng'iroq (☎️{answered} / 📵{noanswer})\n"
            "   ✅{ok}% ❌{fail}% ❓{doubt}%{avg}"
        ),
        "branch_avg_suffix": " • o'rtacha ball {avg}/10",
        "branch_no_calls": "   hali tahlil qilingan qo'ng'iroq yo'q",
        "branch_best": "🥇 Eng yaxshi: {name} ({avg}/10)",
        "branch_worst": "🔻 Eng past: {name} ({avg}/10)",
        "branch_unassigned": "\n⚠️ Filialsiz operatorlar: {count} (bog'lash: /bind)",
        "branch_title": "🏢 {name}\n",
        "branch_no_operators": (
            "Bu filialda hali bog'langan operatorlar yo'q.\n"
            "Egasi uchun: /user_add <login> <parol> operator <filial id> <amoCRM id> <F.I.Sh>"
        ),
        "branch_pick_operator": "\n👥 Operatorlar (bosing — qo'ng'iroqlar va tahlil):",
        "branch_not_found": "Filial topilmadi.",
        "rop_no_branch": "⚠️ Hisobingizga filial biriktirilmagan. Bot egasiga murojaat qiling.",
        # operator ekrani
        "my_stats_title": "👤 {name} — mening statistikam\n",
        "my_no_calls": "Hali tahlil qilingan qo'ng'iroqlar yo'q.",
        # xatolar
        "errors_title": "⚠️ Xatoli qo'ng'iroqlar (❌ muvaffaqiyatsiz va ❓ shubhali)",
        "errors_hint": "Qo'ng'iroqni oching — AI tahlilida xato aynan qayerdaligi ko'rsatilgan.",
        "errors_empty": "✅ Xatoli qo'ng'iroqlar topilmadi.",
        # rollar bo'yicha kunlik hisobot
        "daily_scope_all": "📈 Kunlik hisobot — butun bo'lim",
        "daily_scope_branch": "📈 Kunlik hisobot — «{branch}» filiali",
        "daily_scope_own": "📈 Kunlik hisobot — {name}",
        "daily_empty_scoped": "Bugun sizda tahlil qilingan qo'ng'iroqlar yo'q.",
        # --- egasi buyruqlari (rollarni sozlash) ---
        "admin_only": "🚫 Buyruq faqat bot egasi uchun.",
        "admin_usage_branch_add": "Foydalanish: /branch_add <filial nomi>",
        "admin_branch_added": "✅ «{name}» filiali qo'shildi (id={id}).",
        "admin_branches": "🏢 Filiallar (id — nomi — operatorlar soni):",
        "admin_branches_empty": "Filiallar yo'q. Yaratish: /branch_add <nomi>",
        "admin_usage_user_add": (
            "Foydalanish:\n"
            "/user_add <login> <parol> <rol> <filial id|-> <amo_id|-> <F.I.Sh>\n\n"
            "Rollar: operator, rop, director, owner\n"
            "Misollar:\n"
            "/user_add boss 1234 director - - Topex direktori\n"
            "/user_add rop1 1234 rop 1 - Yunusobod ROP\n"
            "/user_add durdona 1234 operator 1 6284739 Durdona"
        ),
        "admin_user_added": "✅ {login} — {role} {extra} qo'shildi.",
        "admin_user_exists": "⚠️ {login} logini band.",
        "admin_users": "👤 Foydalanuvchilar (login — rol — filial — amo_id):",
        "admin_users_empty": "Foydalanuvchilar yo'q. Qo'shish: /user_add",
        "admin_user_not_found": "⚠️ «{login}» foydalanuvchisi topilmadi.",
        "admin_bad_role": "⚠️ Rol quyidagilardan biri bo'lishi kerak: operator, rop, director, owner.",
        "admin_bad_branch": "⚠️ id={id} bo'lgan filial topilmadi. Ro'yxat: /branches",
        "admin_usage_bind": "Foydalanish: /bind <login> <amoCRM operator id>",
        "admin_bound": "✅ {login} amoCRM operatori id={amo_id} ga bog'landi.",
        "admin_usage_passwd": "Foydalanish: /passwd <login> <yangi parol>",
        "admin_passwd_ok": "✅ {login} uchun parol yangilandi.",
        "admin_usage_access": "Foydalanish: /user_off <login> yoki /user_on <login>",
        "admin_access_on": "✅ {login}: ruxsat yoqildi.",
        "admin_access_off": "⛔ {login}: ruxsat o'chirildi.",
        "admin_amo_ids": "🆔 amoCRM xodimlari (id — ism — tahlil qilingan qo'ng'iroqlar):",
        "admin_amo_ids_empty": "amoCRM xodimlari olinmadi (CRM ulanmaganmi?).",
        "admin_inactive_mark": " (o'chirilgan)",
    },
    "en": {
        # --- menu and buttons ---
        "menu_title": "📋 Main menu",
        "btn_managers": "👥 Managers",
        "btn_daily": "📈 Daily report",
        "btn_stats": "📊 Overall statistics",
        "btn_language": "🌐 Language / Til",
        "btn_menu": "⬅️ Menu",
        "btn_menu_plain": "📋 Menu",
        "btn_back": "⬅️ Back",
        "btn_to_managers": "👥 To managers",
        "btn_to_manager": "⬅️ To manager",
        "btn_to_calls": "⬅️ To manager's calls",
        "btn_pick_date": "📅 Pick a date",
        "btn_other_date": "📅 Another date",
        "btn_search": "🔍 Search by name",
        "btn_audio_tz": "📋 Audio + brief (Uzbek)",
        "menu_text": (
            "📋 Main menu\n\n"
            "👥 Managers — pick a manager, see their calls, AI breakdown and statistics.\n"
            "📈 Daily report — clients served, top performer of the day, system errors and "
            "a brief for each manager (arrives automatically at 20:00).\n"
            "📊 Overall statistics — results for the whole department.\n\n"
            "🎧 You can also just send a call recording or transcript text here — "
            "I'll audit it right away."
        ),
        # --- access ---
        "owner_set": "✅ You are now the bot owner.",
        "private_bot": "⛔ This bot is private and already linked to another user.",
        "private_hint": "⛔ This bot is private. Send /start if you're the owner.",
        # --- language ---
        "lang_prompt": "🌐 Choose the interface language:",
        "lang_changed": "✅ Interface language: English",
        # --- status ---
        "status_title": "📡 Bot status",
        "status_amo_ok": "🟢 AmoCRM connected: {name} (checked every {interval} sec)",
        "status_amo_error": "🔴 AmoCRM: connection error — {error}",
        "status_amo_off": (
            "⚪ AmoCRM not connected (manual mode). "
            "Add AMO_SUBDOMAIN and AMO_ACCESS_TOKEN to the .env file"
        ),
        "status_min_duration": "⏱ Minimum call duration: {seconds} sec",
        "status_db_calls": "💾 Calls in database: {total}",
        # --- managers ---
        "managers_title": "👥 Managers (in brackets — number of analyzed calls):",
        "managers_empty": (
            "No managers or analyzed calls yet.\n\n"
            "Send a call recording here — or wait for a new call from AmoCRM."
        ),
        "manager_unknown": "Manager",
        "manager_no_calls": "No analyzed calls yet.",
        "manager_pick_call": (
            "Choose a call (✅❌❓ — already analyzed: audio + PDF, "
            "⬜ — new: I'll analyze it on tap):"
        ),
        "manager_no_crm_calls": "No calls with a recording visible in CRM yet.",
        "no_phone": "no number",
        "dur_min": "m",
        "dur_sec": "s",
        # call direction is stored in the DB in Russian — translated only for display
        "direction_in": "Incoming",
        "direction_out": "Outgoing",
        # --- search ---
        "search_prompt": (
            "🔍 Enter a manager's name (or part of it) — I'll show matches.\n\n"
            "Cancel: /menu"
        ),
        "search_none": "🔍 No one found for «{query}». Try a different part of the name.",
        "search_results": "🔍 Found for «{query}» ({count}):",
        # --- dates ---
        "dates_title": "📅 Pick a date — I'll show all conversations for that day:",
        "dates_empty": "No calls yet",
        "day_empty": "No calls on {day}",
        "day_title": (
            "👨‍💼 {name} • 📅 {day}\n\n"
            "Conversations for this day ({count}):\n"
            "✅❌❓ — analyzed, ⬜ — I'll analyze on tap"
        ),
        "day_calls_label": "📅 {date} ({weekday}) • {count} calls",
        "weekdays": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        # --- call analysis ---
        "analyzing": "Analyzing the call...",
        "analyzing_long": "🎧 Downloading the recording, transcribing and preparing PDF (1-2 minutes)...",
        "report_title": "🧠 Call breakdown (dialogue, mistakes and AI score):",
        "call_not_in_crm": (
            "❌ Call not found in CRM (may be outdated). "
            "Reopen the manager's card."
        ),
        "call_not_analyzed": "⚠️ Could not analyze the call (no speech or recording error).",
        "call_not_found": "Call not found.",
        "audio_unavailable": "(audio recording unavailable)",
        "tz_unavailable": "No brief available for this call.",
        "report_missing": "No report available.",
        "transcript_missing": "No transcript text available.",
        "transcript_title": "📃 Full conversation text (verbatim, as recorded):",
        "pdf_failed": "⚠️ Could not build the PDF report: {error}",
        "error": "❌ Error: {error}",
        # --- PDF ---
        "pdf_title": "Call analysis",
        "pdf_manager": "Manager: {name}",
        "pdf_date": "Date: {date} • {direction} • {duration}",
        "pdf_score": "Score: {score}",
        "pdf_phone": "Client phone: {phone}",
        "pdf_card": "CRM card: {url}",
        "pdf_uz_section": "BRIEF FOR THE MANAGER (IN UZBEK)",
        # --- statistics ---
        "stats_title": "📊 Overall department statistics\n",
        "stats_by_manager": "\n👥 By manager:",
        "stats_total": "📞 Total calls: {total}",
        "stats_answered": "☎️ Answered (had a conversation): {answered}",
        "stats_ok": "✅ Successful: {count} ({percent}%)",
        "stats_fail": "❌ Unsuccessful: {count} ({percent}%)",
        "stats_doubt": "❓ Uncertain: {count} ({percent}%)",
        "stats_noanswer": "📵 Unanswered / not picked up: {count}",
        "stats_avg": "⭐ Average score: {avg}/10",
        "stats_manager_line": "• {name}: {total} calls, ✅{ok}% ❌{fail}% ❓{doubt}%{avg}",
        "stats_manager_avg": ", avg score {avg}/10",
        # --- daily report ---
        "daily_preparing": "Preparing the report...",
        "daily_building": "📈 Building the overall daily report...",
        "daily_empty": (
            "No analyzed calls today yet — the report will be ready "
            "once calls come in."
        ),
        "daily_error": "❌ Error building the report: {error}",
        "daily_auto": "🌙 Automatic daily report:",
        # --- manual upload ---
        "manual_auditing": "🧠 Running a strict audit of the call...",
        "manual_got_audio": "🎧 Got the recording. Transcribing...",
        "manual_transcribed": "🧠 Transcribed. Running a strict audit of the call...",
        "manual_no_speech": "⚠️ Almost no speech in the recording — nothing to analyze.",
        "manual_send_audio": (
            "Send an audio file (mp3/wav/ogg/m4a), a voice message, or a .txt transcript."
        ),
        "manual_too_big": (
            "⚠️ File is larger than 20 MB — Telegram doesn't let bots download files that big. "
            "Compress the recording or send it in parts."
        ),
        "manual_text_short": (
            "Send a call recording (audio/voice) or the full transcript text "
            "(at least 100 characters).\n\nMenu: /menu"
        ),
        # --- call statuses ---
        "call_status_labels": {
            1: "📞 Planned",
            2: "📅 Scheduled",
            3: "🔄 Completed",
            4: "✅ Talked",
            5: "📳 Missed",
            6: "❌ No answer",
            7: "🚫 No connection",
        },
        "call_status_short": {
            1: "plan",
            2: "sched.",
            3: "done",
            4: "talk",
            5: "missed",
            6: "no ans.",
            7: "no conn.",
        },
        # --- auth and roles (auth.py wired into main.py — text checked against real flow 2026-08-05) ---
        "auth_login_prompt": "🔑 Enter your login:",
        "auth_password_prompt": "🔒 Enter your password (message will be deleted after checking):",
        "auth_failed": "❌ Wrong login or password.",
        "auth_inactive": "⛔ Your account is disabled. Contact your manager.",
        "auth_success": "✅ Welcome, {name}! Role: {role}",
        "auth_logged_out": "👋 You have been logged out.",
        "auth_not_logged_in": "🔒 Please log in first: /login",
        "auth_no_access": "🚫 You don't have access to this section.",
        "role_operator": "Operator",
        "role_rop": "Sales manager (ROP)",
        "role_director": "Director",
        "role_owner": "Owner",
        "auth_already_logged": "You are already logged in as {name} ({role}). To switch: /logout",
        "auth_operator_unbound": (
            "⚠️ Your account is not linked to an amoCRM operator yet — no calls to show.\n"
            "Ask your manager to run: /bind <your login> <amoCRM id>"
        ),
        "auth_login_hint": "🔒 Log in: /login — or /login <login> <password> in one line.",
        # --- role screens (director / ROP / operator) ---
        "menu_role_line": "👤 {name} • {role}{branch}",
        "menu_branch_suffix": " • branch: {branch}",
        "menu_text_rop": (
            "📋 ROP menu\n\n"
            "👥 My operators — branch operator ranking, their calls and AI review.\n"
            "📊 Branch stats — totals for your branch.\n"
            "⚠️ Branch mistakes — calls where operators made mistakes.\n"
            "📈 Daily report — for your branch."
        ),
        "menu_text_operator": (
            "📋 My menu\n\n"
            "📞 My calls — your conversations with score and AI review.\n"
            "📊 My stats — successful / unsuccessful / no-answer and average score.\n"
            "⚠️ My mistakes — calls where AI found mistakes: what exactly and how to fix.\n"
            "📈 My daily report — your day summary."
        ),
        "btn_branches": "🏢 Branch summary",
        "btn_branch_stats": "📊 Branch stats",
        "btn_branch_team": "👥 My operators",
        "btn_dept_total": "📊 Department total",
        "btn_my_calls": "📞 My calls",
        "btn_my_stats": "📊 My stats",
        "btn_my_errors": "⚠️ My mistakes",
        "btn_errors": "⚠️ Mistakes",
        "btn_branch_errors": "⚠️ Branch mistakes",
        "btn_to_branches": "⬅️ To branches",
        # director summary
        "branches_title": "🏢 Branch summary\n",
        "branches_empty": (
            "No branches yet.\n\n"
            "Owner: /branch_add <name> — create a branch, "
            "/user_add — create a user, /bind — link an operator to amoCRM."
        ),
        "branch_line": (
            "🏢 {name} — {operators} op., {total} calls (☎️{answered} / 📵{noanswer})\n"
            "   ✅{ok}% ❌{fail}% ❓{doubt}%{avg}"
        ),
        "branch_avg_suffix": " • avg score {avg}/10",
        "branch_no_calls": "   no analysed calls yet",
        "branch_best": "🥇 Best: {name} ({avg}/10)",
        "branch_worst": "🔻 Weakest: {name} ({avg}/10)",
        "branch_unassigned": "\n⚠️ Operators without a branch: {count} (link with /bind)",
        "branch_title": "🏢 {name}\n",
        "branch_no_operators": (
            "No operators linked to this branch yet.\n"
            "Owner: /user_add <login> <password> operator <branch id> <amoCRM id> <full name>"
        ),
        "branch_pick_operator": "\n👥 Operators (tap — calls and review):",
        "branch_not_found": "Branch not found.",
        "rop_no_branch": "⚠️ No branch is linked to your account. Contact the bot owner.",
        # operator screen
        "my_stats_title": "👤 {name} — my stats\n",
        "my_no_calls": "No analysed calls yet.",
        # mistakes
        "errors_title": "⚠️ Calls with mistakes (❌ unsuccessful and ❓ questionable)",
        "errors_hint": "Open a call — the AI review shows exactly where the mistake is.",
        "errors_empty": "✅ No calls with mistakes found.",
        # role-aware daily report
        "daily_scope_all": "📈 Daily report — whole department",
        "daily_scope_branch": "📈 Daily report — branch «{branch}»",
        "daily_scope_own": "📈 Daily report — {name}",
        "daily_empty_scoped": "You have no analysed calls today yet.",
        # --- owner commands (role setup) ---
        "admin_only": "🚫 This command is for the bot owner only.",
        "admin_usage_branch_add": "Usage: /branch_add <branch name>",
        "admin_branch_added": "✅ Branch «{name}» created (id={id}).",
        "admin_branches": "🏢 Branches (id — name — operators):",
        "admin_branches_empty": "No branches yet. Create one: /branch_add <name>",
        "admin_usage_user_add": (
            "Usage:\n"
            "/user_add <login> <password> <role> <branch id|-> <amo_id|-> <full name>\n\n"
            "Roles: operator, rop, director, owner\n"
            "Examples:\n"
            "/user_add boss 1234 director - - Topex Director\n"
            "/user_add rop1 1234 rop 1 - Yunusabad ROP\n"
            "/user_add durdona 1234 operator 1 6284739 Durdona"
        ),
        "admin_user_added": "✅ {login} — {role} {extra} created.",
        "admin_user_exists": "⚠️ Login {login} is already taken.",
        "admin_users": "👤 Users (login — role — branch — amo_id):",
        "admin_users_empty": "No users yet. Create one: /user_add",
        "admin_user_not_found": "⚠️ User «{login}» not found.",
        "admin_bad_role": "⚠️ Role must be one of: operator, rop, director, owner.",
        "admin_bad_branch": "⚠️ Branch id={id} not found. List: /branches",
        "admin_usage_bind": "Usage: /bind <login> <amoCRM operator id>",
        "admin_bound": "✅ {login} linked to amoCRM operator id={amo_id}.",
        "admin_usage_passwd": "Usage: /passwd <login> <new password>",
        "admin_passwd_ok": "✅ Password for {login} updated.",
        "admin_usage_access": "Usage: /user_off <login> or /user_on <login>",
        "admin_access_on": "✅ {login}: access enabled.",
        "admin_access_off": "⛔ {login}: access disabled.",
        "admin_amo_ids": "🆔 amoCRM users (id — name — analysed calls):",
        "admin_amo_ids_empty": "Could not fetch amoCRM users (CRM not connected?).",
        "admin_inactive_mark": " (disabled)",
    },
}


def get_lang() -> str:
    lang = state.get_lang()
    return lang if lang in TEXTS else DEFAULT_LANG


def set_lang(lang: str) -> None:
    if lang not in TEXTS:
        raise ValueError(f"Неизвестный язык: {lang}")
    state.set_lang(lang)


def t(key: str, **kwargs) -> str:
    """Строка интерфейса на текущем языке; при пропуске в переводе — русский вариант."""
    text = TEXTS[get_lang()].get(key) or TEXTS[DEFAULT_LANG][key]
    return text.format(**kwargs) if kwargs else text


def raw(key: str):
    """Нестроковые значения: списки и словари (дни недели, статусы звонка)."""
    return TEXTS[get_lang()].get(key) or TEXTS[DEFAULT_LANG][key]


def call_status_label(status: int | None) -> str:
    return raw("call_status_labels").get(status, "") if status else ""


def call_status_short(status: int | None) -> str:
    return raw("call_status_short").get(status, "") if status else ""


def direction(value: str) -> str:
    """Направление звонка из базы ("Входящий"/"Исходящий") на языке интерфейса."""
    if value == TEXTS[DEFAULT_LANG]["direction_in"]:
        return t("direction_in")
    if value == TEXTS[DEFAULT_LANG]["direction_out"]:
        return t("direction_out")
    return value or "—"


def format_stats(stats: dict) -> str:
    c, p = stats["counts"], stats["percent"]
    answered = stats.get("answered", c["ok"] + c["fail"] + c["doubt"])
    lines = [
        t("stats_total", total=stats["total"]),
        t("stats_answered", answered=answered),
        t("stats_ok", count=c["ok"], percent=p["ok"]),
        t("stats_fail", count=c["fail"], percent=p["fail"]),
        t("stats_doubt", count=c["doubt"], percent=p["doubt"]),
        t("stats_noanswer", count=c.get("noanswer", 0)),
    ]
    if stats["avg_score"] is not None:
        lines.append(t("stats_avg", avg=stats["avg_score"]))
    return "\n".join(lines)
