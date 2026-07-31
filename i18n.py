"""Строки интерфейса на двух языках: русский и узбекский (латиница).

Владелец переключает язык кнопкой в меню (см. state.get_lang / set_lang).
Ключи одинаковые для обоих языков; t(lang, key) достаёт строку с фолбэком на RU.
"""

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
        # кнопка показывает язык, НА который переключит
        "btn_lang": "🌐 Til: o‘zbekcha",
        "btn_back_menu": "⬅️ Меню",
        "btn_back_calls": "⬅️ К звонкам сотрудника",
        "btn_back_employees": "👥 К сотрудникам",
        "employees_title": "👥 Сотрудники (в скобках — количество разобранных звонков):",
        "employees_empty": (
            "Пока нет ни сотрудников, ни разобранных звонков.\n\n"
            "Пришлите запись звонка сюда — или дождитесь нового звонка из AmoCRM."
        ),
        "search_prompt": "🔍 Введите имя сотрудника (или часть имени):",
        "search_none": "Никого не нашёл по запросу: ",
        "search_title": "🔍 Найдено по запросу «{q}»:",
        "lang_switched": "🌐 Язык переключён на русский.",
        "pdf_caption": "📄 Полный разбор звонка (PDF)",
        "doc_unavailable": "Разбор для этого звонка недоступен.",
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
        "btn_lang": "🌐 Язык: русский",
        "btn_back_menu": "⬅️ Menyu",
        "btn_back_calls": "⬅️ Xodim qo‘ng‘iroqlariga",
        "btn_back_employees": "👥 Xodimlarga",
        "employees_title": "👥 Xodimlar (qavs ichida — tahlil qilingan qo‘ng‘iroqlar soni):",
        "employees_empty": (
            "Hozircha na xodim, na tahlil qilingan qo‘ng‘iroq bor.\n\n"
            "Shu yerga qo‘ng‘iroq yozuvini yuboring — yoki AmoCRM’dan yangi qo‘ng‘iroqni kuting."
        ),
        "search_prompt": "🔍 Xodim ismini (yoki bir qismini) kiriting:",
        "search_none": "So‘rov bo‘yicha hech kim topilmadi: ",
        "search_title": "🔍 «{q}» bo‘yicha topildi:",
        "lang_switched": "🌐 Til o‘zbekchaga o‘tkazildi.",
        "pdf_caption": "📄 Qo‘ng‘iroqning to‘liq tahlili (PDF)",
        "doc_unavailable": "Bu qo‘ng‘iroq uchun tahlil mavjud emas.",
    },
}


def t(lang: str, key: str, **fmt) -> str:
    """Строка для языка lang; фолбэк на RU, затем на сам ключ. fmt — для .format()."""
    ru = I18N["ru"]
    s = I18N.get(lang, ru).get(key) or ru.get(key) or key
    return s.format(**fmt) if fmt else s
