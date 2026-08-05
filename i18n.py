"""Тексты интерфейса на двух языках. Язык владельца хранится в state.json."""

import state

DEFAULT_LANG = "ru"

LANGUAGES = {"ru": "🇷🇺 Русский", "uz": "🇺🇿 O'zbekcha"}

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
        # --- роли и вход ---
        "need_login": "🔐 Нужно войти. Отправьте: /login логин пароль\n(логин и пароль выдаёт руководитель).",
        "login_usage": "Использование: /login логин пароль",
        "login_ok": "✅ Вход выполнен. Ваша роль: {role}.",
        "login_fail": "⛔ Неверный логин или пароль.",
        "logout_ok": "👋 Вы вышли. Чтобы войти снова: /login логин пароль",
        "access_denied": "⛔ Нет доступа к этим данным.",
        "whoami": "Вы вошли как {name} • роль: {role}.",
        "whoami_owner": "Вы — владелец бота (полный доступ).",
        "whoami_none": "Вы не вошли. Отправьте: /login логин пароль",
        "role_operator": "оператор",
        "role_rop": "РОП (руководитель отдела)",
        "role_director": "директор",
        "role_owner": "владелец",
        # --- команды владельца (настройка ролей) ---
        "owner_only": "⛔ Команда доступна только владельцу.",
        "addbranch_usage": "Использование: /addbranch название филиала",
        "branch_added": "✅ Филиал добавлен: {name} (id {id}).",
        "branches_title": "🏢 Филиалы:",
        "branches_empty": "Филиалов пока нет. Добавить: /addbranch название",
        "adduser_usage": (
            "Использование: /adduser логин пароль роль [id_филиала] [amo_id_оператора]\n"
            "роли: operator (оператор) / rop (РОП) / director (директор)\n"
            "Пример оператора: /adduser durdona 1234 operator 1 7621234"
        ),
        "adduser_bad_role": "⛔ Роль должна быть: operator, rop или director.",
        "user_added": "✅ Пользователь создан: {login} • роль {role}{extra}.",
        "user_exists": "⛔ Логин «{login}» уже занят.",
        "users_title": "👤 Пользователи:",
        "users_empty": "Пользователей пока нет. Добавить: /adduser ...",
        "daily_denied": "⛔ Отчёт за день доступен директору и владельцу.",
        # --- статистика по филиалам (директор) ---
        "stats_by_branch": "\n🏢 По филиалам:",
        "stats_branch_line": "• {name}: {total} зв. (☎️{answered}/📵{noanswer}), ✅{ok}% ❌{fail}% ❓{doubt}%{avg}",
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
        # --- rollar va kirish ---
        "need_login": "🔐 Kirish kerak. Yuboring: /login login parol\n(login va parolni rahbaringiz beradi).",
        "login_usage": "Foydalanish: /login login parol",
        "login_ok": "✅ Kirdingiz. Rolingiz: {role}.",
        "login_fail": "⛔ Login yoki parol noto'g'ri.",
        "logout_ok": "👋 Chiqdingiz. Qayta kirish: /login login parol",
        "access_denied": "⛔ Bu ma'lumotlarga ruxsat yo'q.",
        "whoami": "Siz {name} sifatida kirgansiz • rol: {role}.",
        "whoami_owner": "Siz bot egasisiz (to'liq ruxsat).",
        "whoami_none": "Siz kirmagansiz. Yuboring: /login login parol",
        "role_operator": "operator",
        "role_rop": "ROP (savdo bo'limi rahbari)",
        "role_director": "direktor",
        "role_owner": "ega",
        # --- ega buyruqlari (rollarni sozlash) ---
        "owner_only": "⛔ Buyruq faqat ega uchun.",
        "addbranch_usage": "Foydalanish: /addbranch filial nomi",
        "branch_added": "✅ Filial qo'shildi: {name} (id {id}).",
        "branches_title": "🏢 Filiallar:",
        "branches_empty": "Hozircha filial yo'q. Qo'shish: /addbranch nomi",
        "adduser_usage": (
            "Foydalanish: /adduser login parol rol [filial_id] [operator_amo_id]\n"
            "rollar: operator / rop / director\n"
            "Operator misoli: /adduser durdona 1234 operator 1 7621234"
        ),
        "adduser_bad_role": "⛔ Rol: operator, rop yoki director bo'lishi kerak.",
        "user_added": "✅ Foydalanuvchi yaratildi: {login} • rol {role}{extra}.",
        "user_exists": "⛔ «{login}» login band.",
        "users_title": "👤 Foydalanuvchilar:",
        "users_empty": "Hozircha foydalanuvchi yo'q. Qo'shish: /adduser ...",
        "daily_denied": "⛔ Kunlik hisobot direktor va ega uchun.",
        # --- filiallar bo'yicha statistika (direktor) ---
        "stats_by_branch": "\n🏢 Filiallar bo'yicha:",
        "stats_branch_line": "• {name}: {total} qo'ng'. (☎️{answered}/📵{noanswer}), ✅{ok}% ❌{fail}% ❓{doubt}%{avg}",
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
