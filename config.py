import os
from pathlib import Path

# Windows: заставляем Python доверять сертификатам из системного хранилища,
# иначе SSL-ошибки при подключении к Telegram/OpenAI (антивирусы, корп. сети)
try:
    import truststore

    truststore.inject_into_ssl()
except ImportError:
    import certifi

    os.environ.setdefault("SSL_CERT_FILE", certifi.where())

from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
TMP_DIR = BASE_DIR / "tmp"
AUDIO_DIR = DATA_DIR / "audio"
DATA_DIR.mkdir(exist_ok=True)
TMP_DIR.mkdir(exist_ok=True)
AUDIO_DIR.mkdir(exist_ok=True)

load_dotenv(BASE_DIR / ".env")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
ANALYSIS_MODEL = os.getenv("ANALYSIS_MODEL", "gpt-4o-mini").strip()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5").strip()

# Groq — бесплатный тариф для тестирования (расшифровка + анализ)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_WHISPER_MODEL = os.getenv("GROQ_WHISPER_MODEL", "whisper-large-v3-turbo").strip()
GROQ_ANALYSIS_MODEL = os.getenv("GROQ_ANALYSIS_MODEL", "llama-3.3-70b-versatile").strip()

AMO_SUBDOMAIN = os.getenv("AMO_SUBDOMAIN", "").strip().replace(".amocrm.ru", "")
AMO_ACCESS_TOKEN = os.getenv("AMO_ACCESS_TOKEN", "").strip()

# язык расшифровки аудио (uz/ru/...); пусто — автоопределение
WHISPER_LANGUAGE = os.getenv("WHISPER_LANGUAGE", "").strip()

# белый список операторов: если задан — анализируем только их
MANAGER_WHITELIST = [
    s.strip() for s in os.getenv("MANAGER_WHITELIST", "").split(",") if s.strip()
]

MIN_CALL_DURATION = int(os.getenv("MIN_CALL_DURATION", "20"))
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "120"))

STATE_FILE = DATA_DIR / "state.json"

def amo_enabled() -> bool:
    return bool(AMO_SUBDOMAIN and AMO_ACCESS_TOKEN)
