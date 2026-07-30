import json
import os
import random
import shutil
from datetime import datetime
from pathlib import Path

import telebot
from dotenv import load_dotenv
from telebot import types

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    print("Ошибка: Переменная BOT_TOKEN не найдена в файле .env!")
    exit()

bot = telebot.TeleBot(TOKEN)

VERSION = "0.6.0 beta"
PROJECT_DIR = Path(__file__).parent
USER_DATA_DIR = PROJECT_DIR / "tg_data" / "users"
USER_BACKUP_DIR = USER_DATA_DIR / "backups"

PARROT_LIMIT = 3
XP_PER_LEVEL = 100
XP_TOPIC = 2
XP_MOOD = 1
XP_CONTINUE = 1
XP_ANKETA = 20
XP_GAME_WIN = 15
XP_QUIZ_CORRECT = 10
XP_QUIZ_FINISH_PER_POINT = 5
MONTHS_RU = ("января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря")

ACHIEVEMENT_NAMES = {
    "first_quiz": "Первая викторина",
    "perfect_quiz": "Идеальная викторина (5/5)",
    "guess_master": "Мастер чисел (≤3 попытки)",
    "xp_50": "50 XP",
    "xp_200": "200 XP",
    "first_guess": "Первое угаданное число",
    "topic_explorer": "Исследователь тем (5+ тем)",
}

QUIZ_START_EXACT = ("викторина", "викторину", "квиз", "викторины")
QUIZ_START_PHRASES = (
    "начать викторин", "запусти викторин", "запустить викторин",
    "хочу викторин", "хочу квиз", "давай викторин", "давай квиз",
    "играть в викторин", "открой викторин",
)

# Викторина: 3 варианта ответа, correct — индекс (0–2)
QUIZ_QUESTIONS = (
    {"q": "Сколько планет в Солнечной системе?", "options": ("7", "8", "9"), "correct": 1},
    {"q": "В каком году началась Вторая мировая?", "options": ("1939", "1941", "1914"), "correct": 0},
    {"q": "Какой язык мы используем для ChatGR?", "options": ("Python", "Java", "C++"), "correct": 0},
    {"q": "Как называется красная планета?", "options": ("Венера", "Марс", "Юпитер"), "correct": 1},
    {"q": "Сколько месяцев в году?", "options": ("10", "12", "13"), "correct": 1},
    {"q": "Кто написал «Войну и мир»?", "options": ("Толстой", "Пушкин", "Достоевский"), "correct": 0},
    {"q": "Сколько континентов на Земле?", "options": ("5", "6", "7"), "correct": 1},
    {"q": "Какой океан самый большой?", "options": ("Атлантический", "Тихий", "Северный Ледовитый"), "correct": 1},
)

# --- Состояние по chat_id (мультипользовательский Telegram) ---
user_states = {}
last_bot_answers = {}
topic_counts_global = {}
global_stats = {}
user_profiles = {}
user_histories = {}
_loaded_users = set()

CHARACTER_LABELS = {"обычный": "обычный", "весёлый": "весёлый", "мемный": "мемный", "сарказм": "саркастичный"}
CHARACTER_ALIASES = {"обычный": "обычный", "нормальный": "обычный", "весёлый": "весёлый", "веселый": "весёлый", "мемный": "мемный", "мемы": "мемный", "сарказм": "сарказм", "саркастичный": "сарказм", "грок": "сарказм"}

ANKETA_STEPS = (
    ("favorite_game", "Какая твоя любимая игра? (или напиши «пропустить»)"),
    ("hobby", "Какое у тебя хобби? (или напиши «пропустить»)"),
    ("favorite_topic", "О какой теме любишь говорить? Например: космос, игры, школа."),
)

CONTINUE_PHRASES = ("ещё", "еще", "продолжи", "дальше", "подробнее", "расскажи больше", "и что", "а дальше")
CONTINUE_HINTS = {
    "космос": "Могу рассказать про планеты, Луну или чёрные дыры — что выберешь?",
    "игра": "Поговорим про жанры, любимую игру или онлайн?",
    "война": "Уточни — техника, сражения или причины?",
    "школа": "Про уроки, друзей или оценки?",
    "технологии": "Телефоны, компьютеры или роботы?",
}

# --- ПОЛНАЯ БАЗА ОТВЕТОВ ГРОКА ---
responses = {
    "привет": [
        "О, привет! Рад тебя видеть — я ChatGR, и сегодня в ударе. О чём поболтаем?",
        "Здравствуй! Заглядывай чаще — мне нравится, когда есть с кем поговорить. Как настроение?",
        "Привет-привет! Можем обсудить игры, космос, школу или что угодно — ты выбирай тему.",
    ],
    "дела": [
        "У меня всё супер — особенно когда кто-то пишет! А у тебя как день, что интересного случилось?",
        "Нормально, спасибо что спросил! Я тут, готов болтать. Расскажи, как твои дела — правда интересно.",
    ],
    "имя": [
        "Меня зовут ChatGR — бот, который ты сам прокачиваешь. Приятно познакомиться! А тебя как?",
        f"Я ChatGR, версия {VERSION}. Живу в Python и люблю хорошие разговоры. А как тебя зовут?",
    ],
    "возраст": [
        "Я создан в 2026 году, так что мне меньше года — я ещё совсем молодой бот! А тебе сколько лет, если не секрет?",
        "Мне меньше года — я появился в 2026-м. Зато я быстро учусь. А ты в каком классе или сколько тебе лет?",
    ],
    "игра": [
        "О, игры — это круто! Я бы сам поиграл, если бы мог. Какая у тебя любимая — Minecraft, Roblox, что-то ещё?",
        "Игры — отличный способ отдохнуть. Ты больше любишь стратегии, шутеры или что-то спокойное?",
    ],
    "война": [
        "Войны — тяжёлая и серьёзная тема. Ты про Вторую мировую спрашиваешь или про войны вообще? Расскажи, что именно интересно.",
        "Это важная тема в истории. Давай уточним — тебя интересуют танки, сражения или причины войны?",
    ],
    "вв2": [
        "Вторая мировая война — одна из самых важных тем в истории. Что тебя цепляет — фронт, техника, люди?",
        "ВВ2 — огромная тема. Хочешь поговорить про сражения, страны или героев того времени?",
    ],
    "ww2": [
        "WW2 — то же самое, что Вторая мировая. О чём рассказать — о битвах, самолётах, кораблях?",
        "Да, Вторая мировая! Это целая эпоха. Что именно тебя интересует в ней?",
    ],
    "танк": [
        "Танки — мощная техника! Т-34, «Тигр», «Шерман» — у каждого своя история. Какой танк тебе нравится больше всего?",
        "Танки — это и сила, и история. Ты больше про реальные модели или про танки в играх?",
    ],
    "самолёт": [
        "Самолёты завораживают! Истребители, бомбардировщики, гражданская авиация — что ближе тебе?",
        "Небо — особая стихия. Есть любимый самолёт или может любимая игра/фильм про авиацию?",
    ],
    "погода": [
        "Я не могу посмотреть погоду за окном, но надеюсь, у тебя сегодня хороший день. У вас сейчас солнце или дождь?",
        "Погода сильно влияет на настроение. Какая у вас сейчас — тёплая, дождливая, снежная?",
    ],
    "музыка": [
        "Музыка — супер тема! Рок, поп, рэп, саундтреки из игр — что слушаешь чаще всего?",
        "Без музыки скучно. Есть любимый исполнитель или песня, которую сейчас слушаешь на повторе?",
    ],
    "книга": [
        "Книги — это целые миры. Ты больше любишь фантастику, детективы или что-то про историю?",
        "Круто, что читаешь! Какая книга последняя — и понравилась или ещё не дочитал?",
    ],
    "фильм": [
        "Фильмы — отличный вечерний отдых. Боевики, комедии, ужасы — какой жанр твой любимый?",
        "Есть фильм, который ты бы посоветовал посмотреть? Или может, недавно что-то крутое увидел?",
    ],
    "школа": [
        "Школа — важная часть жизни. Как у тебя с учёбой — есть любимые предметы или те, что даются тяжелее?",
        "Учёба бывает разной. Расскажи, что в школе сейчас интересного — уроки, друзья, проекты?",
    ],
    "лето": [
        "Лето — лучшее время! Купаться, гулять, ездить куда-то. Чем планируешь заняться этим летом?",
        "Жара, каникулы, свобода — обожаю эту тему. Ты летом больше дома отдыхаешь или куда-то ездишь?",
    ],
    "зима": [
        "Зима — снег, праздники, горячий чай. Ты зимой любишь кататься на лыжах или больше сидеть дома?",
        "Зимний сезон у каждого свой. У вас много снега? Как проводишь холодные дни?",
    ],
    "весна": [
        "Весна — когда всё оживает. Тепло, птицы, первые цветы. Нравится тебе это время года?",
        "После зимы весна особенно радует. Что любишь весной — гулять, спорт или просто солнце?",
    ],
    "осень": [
        "Осень — уютная пора: листья, дождь, какая-то спокойная атмосфера. Ты осень любишь?",
        "Осенью часто начинается учёба и новые дела. Как ты обычно проводишь осенние дни?",
    ],
    "спасибо": [
        "Пожалуйста! Всегда рад помочь и поболтать. Обращайся, если захочешь ещё о чём-то поговорить.",
        "Не за что! Мне приятно с тобой общаться. Если будут вопросы — пиши.",
    ],
    "ужасы": [
        "Ужасы — для смелых! Старые классические или современные — что страшнее по-твоему?",
        "Жанр ужасов — отдельное искусство. Есть фильм или игра, от которой реально страшно?",
    ],
    "фантастика": [
        "Фантастика — моя любимая! Космос, будущее, роботы. Ты больше про космос или про Землю будущего?",
        "Фантастика заставляет мечтать. «Интерстеллар», «Марсианин» или может книги Азимова — что нравится?",
    ],
    "боевик": [
        "Боевики — драйв и экшен! Старые или новые — какие боевики ты считаешь лучшими?",
        "Если хочется адреналина — боевик самое то. Есть любимый герой или франшиза?",
    ],
    "комедия": [
        "Комедии поднимают настроение! Что последнее тебя реально рассмешило — фильм, видео, мем?",
        "Смех продлевает жизнь, говорят. Какие комедии можешь пересматривать снова и снова?",
    ],
    "драма": [
        "Драмы — про жизнь, чувства, сложные ситуации. Какие драматичные фильмы или сериалы тебе запомнились?",
        "Иногда хочется чего-то глубокого. Есть драма, которая тронула тебя сильнее всего?",
    ],
    "спорт": [
        "Спорт — это и здоровье, и характер! Ты сам занимаешься или больше смотришь матчи?",
        "Футбол, баскетбол, плавание — спорта много. Какой вид тебе нравится больше всего?",
    ],
    "животные": [
        "Животные — лучшие друзья человека! У тебя есть питомец или мечтаешь завести?",
        "Кошки, собаки, хомяки — у каждого свой любимец. Какое животное тебе нравится?",
    ],
    "технологии": [
        "Технологии развиваются невероятно быстро! Тебя больше интересуют телефоны, компьютеры или роботы?",
        "ИИ, гаджеты, будущее — тема огромная. Что из технологий тебя восхищает или удивляет?",
    ],
    "история": [
        "История полна удивительных событий! Тебя тянет к древности, средним векам или к новому времени?",
        "Прошлое учит нас многому. Какой период истории тебе кажется самым интересным?",
    ],
    "еда": [
        "Еда — одна из лучших радостей в жизни! Ты больше любишь сладкое, пиццу или домашнюю еду?",
        "У каждого свои вкусы. Есть блюдо, без которого не можешь обойтись?",
    ],
    "путешествия": [
        "Путешествия открывают мир! Куда мечтаешь поехать — море, горы, другой город или страну?",
        "Даже маленькая поездка может запомниться надолго. Где ты уже был и что понравилось?",
    ],
    "космос": [
        "Космос — бесконечная тайна! Планеты, звёзды, чёрные дыры — что в космосе кажется тебе самым крутым?",
        "Представляешь, люди летали на Луну! Тебя больше интересуют ракеты, планеты или инопланетяне?",
        "Представь: ты в космосе. Куда полетишь первым делом?",
    ],
    "друзья": [
        "Друзья — это очень важно. Расскажи, ты сейчас больше общаешься в школе, онлайн или и там и там?",
        "Хороший друг — большая удача. Что для тебя значит настоящая дружба?",
    ],
    "семья": [
        "Семья — это опора. Ты часто проводишь время с родными? Чем любите заниматься вместе?",
        "Родные люди важны, даже когда бывают сложные дни. Хочешь рассказать о чём-то хорошем из семейной жизни?",
    ],
    "хобби": [
        "Хобби делают жизнь интереснее! Чем ты увлекаешься — рисование, спорт, сбор моделей, что-то ещё?",
        "У каждого своё увлечение. Какое хобби приносит тебе больше всего радости?",
    ],
    "код": [
        "Программирование — крутой навык! Ты уже пишешь на Python или только начинаешь?",
        "Код — это как волшебство: пишешь строки, и программа оживает. Над чем сейчас работаешь?",
    ],
    "природа": [
        "Природа успокаивает и вдохновляет. Ты больше любишь лес, море, горы или парк рядом с домом?",
        "Свежий воздух и зелень — лучшее лекарство от скуки. Где тебе нравится гулять больше всего?",
    ],
    "компьютер": [
        "Компьютер — центр вселенной для многих! Ты больше играешь, учишься или смотришь видео?",
        "ПК или ноутбук — неважно, главное что на нём делаешь. Расскажи, для чего используешь чаще всего?",
    ],
    "ютуб": [
        "YouTube — бесконечный источник видео! Какие каналы смотришь — игры, наука, юмор?",
        "На ютубе можно найти всё. Что последнее смотрел и понравилось?",
    ],
    "мемы": [
        "Мемы — язык интернета! Есть мем, от которого ты сейчас смеёшься чаще всего?",
        "Иногда один мем лучше тысячи слов. Кинь тему — может, знаю пару смешных шуток на эту тему!",
    ],
    "выходные": [
        "Выходные — заслуженный отдых! Ты их проводишь активно или предпочитаешь лежать и ничего не делать?",
        "Два дня свободы — мало, но приятно. Что обычно делаешь в субботу и воскресенье?",
    ],
    "сон": [
        "Сон — лучшее восстановление. Ты высыпаешься обычно или часто не досыпаешь?",
        "Хороший сон = хорошее настроение. Сколько часов тебе комфортно спать?",
    ],
    "сериалы": [
        "О, сериалы — это затягивает! Ты больше любишь короткие сезоны или что-то длинное на много серий?",
        "Сериал на вечер — идеальный план. Что сейчас смотришь или что бы посоветовал другу?",
    ],
    "наука": [
        "Наука — это круто! Космос, химия, физика, биология — какая область тебе ближе всего?",
        "Учёные каждый день открывают что-то новое. Есть научная тема, которая тебя реально цепляет?",
    ],
    "машины": [
        "Машины — скорость и красота! Ты больше фанат спорткаров, внедорожников или может гоночных игр?",
        "Автомобили — целая культура. Есть марка или модель, которую мечтаешь увидеть вживую?",
    ],
    "рисование": [
        "Рисование — способ показать воображение! Ты рисуешь на бумаге, планшете или в компьютерных программах?",
        "Круто, когда человек творит. Что любишь рисовать — персонажей, пейзажи, комиксы?",
    ],
    "майнкрафт": [
        "Minecraft — легенда! Ты больше выживаешь, строишь замки или играешь на серверах с друзьями?",
        "Кубический мир затягивает надолго. Какой у тебя любимый режим — выживание, креатив или моды?",
    ],
    "шутки": [
        "Ха, люблю, когда весело! Хочешь — могу подкинуть тему: расскажи свой любимый анекдот или мем.",
        "Юмор спасает любой день. Что тебя сейчас больше смешит — видео, мемы или шутки друзей?",
    ],
    "футбол": [
        "Футбол — эмоции, голы, болельщики! За какую команду болеешь или сам играешь во дворе?",
        "Мяч, ворота, стадион — классика. Смотришь матчи или больше играешь с друзьями?",
    ],
}

TOPIC_NAMES = {
    "привет": "приветствие", "дела": "как дела", "возраст": "возраст бота",
    "игра": "игры", "война": "война", "вв2": "Вторая мировая", "ww2": "WW2",
    "танк": "танки", "самолёт": "самолёты", "погода": "погода", "музыка": "музыка",
    "книга": "книги", "фильм": "фильмы", "школа": "школа", "лето": "лето",
    "зима": "зима", "весна": "весна", "осень": "осень", "спасибо": "благодарность",
    "ужасы": "ужасы", "фантастика": "фантастика", "боевик": "боевики",
    "комедия": "комедии", "драма": "драмы", "спорт": "спорт", "животные": "животные",
    "технологии": "технологии", "история": "история", "еда": "еда",
    "путешествия": "путешествия", "космос": "космос", "друзья": "друзья",
    "семья": "семья", "хобби": "хобби", "код": "программирование",
    "природа": "природа", "компьютер": "компьютер", "ютуб": "YouTube",
    "мемы": "мемы", "выходные": "выходные", "сон": "сон",
    "сериалы": "сериалы", "наука": "наука", "машины": "машины",
    "рисование": "рисование", "майнкрафт": "Minecraft", "шутки": "шутки", "футбол": "футбол",
}
TOPIC_GROUPS = {
    "Общение": ["привет", "дела", "спасибо", "друзья", "семья", "шутки"],
    "Школа и жизнь": ["школа", "хобби", "выходные", "сон"],
    "Развлечения": ["игра", "майнкрафт", "фильм", "сериалы", "музыка", "книга", "ютуб", "мемы"],
    "Жанры": ["ужасы", "фантастика", "боевик", "комедия", "драма"],
    "Природа и сезоны": ["погода", "природа", "лето", "зима", "весна", "осень"],
    "Наука и техника": ["космос", "наука", "технологии", "компьютер", "код"],
    "История и война": ["история", "война", "вв2", "ww2", "танк", "самолёт"],
    "Другое": ["спорт", "футбол", "животные", "еда", "путешествия", "машины", "рисование", "возраст"],
}

topic_roots = [
    ("вв2", ["вв2"]), ("ww2", ["ww2"]), ("война", ["войн"]), ("привет", ["привет"]), ("дела", ["дела"]),
    ("возраст", ["возраст"]), ("игра", ["игр"]), ("танк", ["танк"]), ("самолёт", ["самолёт"]), ("погода", ["погод"]),
    ("музыка", ["музык"]), ("книга", ["книг"]), ("фильм", ["фильм"]), ("школа", ["школ"]), ("лето", ["лето"]),
    ("зима", ["зим"]), ("весна", ["весн"]), ("осень", ["осен"]), ("спасибо", ["спасиб"]), ("ужасы", ["ужас"]),
    ("фантастика", ["фантаст"]), ("боевик", ["боевик"]), ("комедия", ["комед"]), ("драма", ["драм"]), ("спорт", ["спорт"]),
    ("животные", ["животн", "питомец", "кошк", "собак"]), ("технологии", ["технолог", "гаджет", "робот", "телефон", "смартфон"]),
    ("история", ["истор"]), ("еда", ["ед", "кухн", "пицц", "блюд"]), ("путешествия", ["путешеств", "поездк"]),
    ("космос", ["космос", "планет", "ракет", "лун"]), ("друзья", ["друг", "дружб"]), ("семья", ["семь", "родител", "мама", "папа"]),
    ("хобби", ["хобби", "увлеч"]), ("код", ["код", "программ", "python", "питон"]), ("природа", ["природ", "лес", "море", "гор"]),
    ("компьютер", ["компьютер", "ноутбук", "пк"]), ("ютуб", ["ютуб", "youtube"]), ("мемы", ["мем"]),
    ("выходные", ["выходн", "суббот", "воскрес"]), ("сон", ["сон", "сплю", "спать", "высып"]), ("сериалы", ["сериал", "сериаль"]),
    ("наука", ["наук", "учёных", "ученых", "эксперимент"]), ("машины", ["машин", "авто", "машину"]),
    ("рисование", ["рисун", "рисов", "рисую"]), ("майнкрафт", ["майнкрафт", "minecraft"]), ("шутки", ["шутк", "анекдот", "смешн"]),
    ("футбол", ["футбол", "футбольн"])
]

PHRASE_TO_TOPIC = [
    ("как дела", "дела"), ("как твои дела", "дела"), ("что нового", "дела"), ("расскажи про войну", "война"),
    ("про вторую мировую", "вв2"), ("люблю играть", "игра"), ("люблю игры", "игра"), ("расскажи про космос", "космос"),
    ("про космос", "космос"), ("расскажи про историю", "история"), ("люблю животных", "животные"),
    ("люблю спорт", "спорт"), ("про технологии", "технологии"), ("люблю музыку", "музыка"), ("люблю читать", "книга"),
    ("смотрю фильм", "фильм"), ("смотрю сериал", "сериалы"), ("люблю рисовать", "рисование"), ("люблю футбол", "футбол")
]

PARROT_REPLIES = [
    "Эй, ты уже писал это! Я не попугай — давай новую тему. Напиши «помощь».",
    "Третий раз одно и то же — может, попробуешь что-то другое?",
    "Зациклились! Смени фразу — я умею говорить на кучу тем.",
    "Хватит повторять — расскажи что-нибудь новое, мне интересно!"
]

mood_responses = {
    "плохо": ["Жаль это слышать... Надеюсь, станет лучше. Хочешь рассказать, что случилось?", "Мне жаль, что день не задался. Иногда помогает просто выговориться — я слушаю."],
    "нормально": ["Нормально — это уже неплохо! А было ли сегодня что-то приятное, пусть даже маленькое?", "«Нормально» — значит, без катастроф. Расскажи, чем сегодня занимался?"],
    "норм": ["Норм — сойдёт! Главное, чтобы не совсем грустно. Что хорошего было за день?", "Понял, норм. А есть что-то, что хотел бы улучшить или наоборот — порадоваться?"],
    "хорошо": ["Рад за тебя! Хорощее настроение — это здорово. Что именно порадовало сегодня?", "Класс, что всё хорошо! Расскажи подробнее — мне интересно."],
    "отлично": ["Круто! Звучит как отличный день. Что такого хорошего произошло?", "Супер настроение! Поделись — что сделало день таким удачным?"],
    "супер": ["Супер! Люблю, когда у людей хороший день. Расскажи, что случилось!", "Вот это настрой! Надеюсь, так продолжится. Чем занимался?"],
    "ужасно": ["Ой, жаль... Такие дни бывают у всех. Хочешь рассказать, что произошло?", "Понимаю, бывает тяжело. Я здесь — можете написать, что на душе."]
}

MODE_OVERRIDES = {
    "весёлый": {
        "привет": ["Ура, привет!!! Рад тебя видеть — давай болтать, сегодня отличный день!", "Привет-привет!!! Наконец-то кто-то написал — я уже соскучился. О чём поговорим?"],
        "дела": ["У меня всё супер-пупер! А у тебя как — рассказывай, мне правда интересно!", "Отлично! Особенно когда есть с кем поболтать. Как твой день?"],
        "игра": ["Игры — это же лучшее!!! Какая у тебя любимая? Расскажи всё!", "О да, игры рулят! Ты в шутеры, стратегии или что-то спокойное?"],
        "космос": ["Космос — ВАУ!!! Планеты, звёзды, ракеты — что тебя цепляет больше всего?", "Представь: ты в космосе! Куда полетишь первым делом — на Луну или к Марсу?"],
        "имя": [f"Я ChatGR v{VERSION} — твой весёлый бот! А тебя как зовут?", "Меня зовут ChatGR, и я обожаю хорошие разговоры! А как тебя?"]
    },
    "мемный": {
        "привет": ["Йоу, привет! Заходи, тут база — можем обсудить игры, космос, мемы, что угодно.", "Привет! Я не NPC — реально отвечаю. Какой вайб сегодня?"],
        "дела": ["У меня ок, не кринжую. А у тебя как дела — норм или hard mode?", "Всё чилл. Расскажи, что у тебя — может, был какой-то лютый момент за день?"],
        "игра": ["Игры — это база. Ты в Roblox, Minecraft или что-то похардче?", "Гейминг — топ тема. Какая игра сейчас в твоём топе?"],
        "космос": ["Космос — это literally бесконечный контент. Планеты, чёрные дыры — что зацепило?", "Луна, Марс, инопланетяне — выбирай лор, я подхвачу."],
        "имя": [f"Я ChatGR v{VERSION}, мемный режим активирован. А ник твой какой?", "ChatGR на связи. Как тебя зовут, бро?"]
    },
    "сарказм": {
        "привет": ["О, смотрите кто пришёл. Ну привет. Я ChatGR — развлеку, если постараешься.", "Привет. Я бот, не ожидай чудес, но поговорить могу. О чём?"],
        "дела": ["У меня всё стабильно — я же программа. А у тебя как, выжил после этого дня?", "Нормально, спасибо что спросил — редкая вежливость. Расскажи про свой день."],
        "игра": ["Игры. Ну хотя бы тема веселее домашки. Что запускаешь — что-то достойное или очередной казуал?", "Гейминг — единственный способ притвориться, что дела важные. Какая игра?"],
        "космос": ["Космос — бесконечная пустота. Романтично, правда? Что тебя там цепляет?", "Люди летали на Луну, а потом решили, что хватит. О чём именно хочешь услышать?"],
        "имя": [f"ChatGR v{VERSION}. Да, я бот. А тебя как величать?", "Меня зовут ChatGR. Запомню имя, если оно хоть сколько-нибудь оригинальное."]
    }
}

MODE_FALLBACKS = {
    "обычный": "Хм, интересная мысль! Расскажи подробнее или напиши «помощь».",
    "весёлый": "Ого, необычно! Расскажи ещё — или напиши «помощь», покажу все темы!",
    "мемный": "Не врубился в реф. Объясни или кинь «помощь» — там весь список тем.",
    "сарказм": "Не понял. Либо объясни нормально, либо «помощь» — если лень думать."
}

def _default_state():
    return {
        "character": "обычный",
        "last_topic": None,
        "game_state": None,
        "anketa_active": False,
        "anketa_index": 0,
        "name": None,
        "recent_msgs": [],
    }


def _default_stats():
    return {
        "session_messages": 0,
        "mood_count": 0,
        "parrot_blocks": 0,
        "session_start": datetime.now(),
        "session_topics": set(),
    }


def _default_profile():
    return {
        "favorite_game": None,
        "hobby": None,
        "favorite_topic": None,
        "age": None,
        "profile_complete": False,
        "xp": 0,
        "level": 1,
        "achievements": [],
    }


def _user_file(chat_id):
    return USER_DATA_DIR / f"{chat_id}.json"


def _backup_file(chat_id):
    """Копия в папке backups/."""
    return USER_BACKUP_DIR / f"{chat_id}.json"


def _bak_file(chat_id):
    """Соседний .bak: tg_data/users/<id>.json.bak"""
    return USER_DATA_DIR / f"{chat_id}.json.bak"


def ensure_profile_fields(chat_id):
    """Подтягивает xp/level/achievements для старых JSON."""
    prof = user_profiles[chat_id]
    for key, value in _default_profile().items():
        if key not in prof:
            prof[key] = value if key != "achievements" else []
    try:
        prof["xp"] = int(prof.get("xp") or 0)
    except (TypeError, ValueError):
        prof["xp"] = 0
    prof["level"] = max(1, 1 + prof["xp"] // XP_PER_LEVEL)
    if not isinstance(prof.get("achievements"), list):
        prof["achievements"] = []


def xp_to_next_level(prof):
    level = max(1, int(prof.get("level", 1)))
    xp = int(prof.get("xp", 0))
    next_at = level * XP_PER_LEVEL
    return max(0, next_at - xp)


def unlock_achievement(chat_id, ach_id):
    """Открывает ачивку. Возвращает название или None, если уже была."""
    ensure_profile_fields(chat_id)
    prof = user_profiles[chat_id]
    if ach_id in prof["achievements"]:
        return None
    prof["achievements"].append(ach_id)
    return ACHIEVEMENT_NAMES.get(ach_id, ach_id)


def check_progress_achievements(chat_id):
    """Ачивки за XP и число тем. Список текстов для ответа."""
    notes = []
    ensure_profile_fields(chat_id)
    xp = user_profiles[chat_id]["xp"]
    if xp >= 50:
        title = unlock_achievement(chat_id, "xp_50")
        if title:
            notes.append(f"🏆 {title}")
    if xp >= 200:
        title = unlock_achievement(chat_id, "xp_200")
        if title:
            notes.append(f"🏆 {title}")
    topics = len(topic_counts_global.get(chat_id) or {})
    if topics >= 5:
        title = unlock_achievement(chat_id, "topic_explorer")
        if title:
            notes.append(f"🏆 {title}")
    return notes


def add_xp(chat_id, amount, save=True, announce_xp=False):
    """Начисляет XP. Возвращает текст о повышении / ачивках (или +XP если announce_xp)."""
    if amount <= 0:
        return None
    ensure_profile_fields(chat_id)
    prof = user_profiles[chat_id]
    old_level = prof["level"]
    prof["xp"] += amount
    prof["level"] = 1 + prof["xp"] // XP_PER_LEVEL
    parts = []
    if prof["level"] > old_level:
        parts.append(f"🎉 Уровень {prof['level']}! (+{amount} XP)")
    elif announce_xp:
        parts.append(f"+{amount} XP")
    parts.extend(check_progress_achievements(chat_id))
    if save:
        save_user_data(chat_id)
    return "\n".join(parts) if parts else None


def _read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def init_user(chat_id):
    chat_id = str(chat_id)
    if chat_id not in user_states:
        user_states[chat_id] = _default_state()
        last_bot_answers[chat_id] = {}
        topic_counts_global[chat_id] = {}
        global_stats[chat_id] = _default_stats()
        user_profiles[chat_id] = _default_profile()
        user_histories[chat_id] = []
    if chat_id not in _loaded_users:
        load_user_data(chat_id)
        _loaded_users.add(chat_id)


def load_user_data(chat_id):
    path = _user_file(chat_id)
    bak = _bak_file(chat_id)
    backup = _backup_file(chat_id)
    data = None
    restored_from = None

    for candidate, label in ((path, None), (bak, ".bak"), (backup, "backups/")):
        if not candidate.exists():
            continue
        try:
            data = _read_json(candidate)
            if label and candidate != path:
                restored_from = label
            break
        except (json.JSONDecodeError, OSError, TypeError):
            data = None

    if data is None:
        return

    if restored_from:
        try:
            USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"[ChatGR] Восстановлен профиль {chat_id} из {restored_from}.")
        except OSError:
            pass

    state = user_states[chat_id]
    state["character"] = data.get("character", "обычный")
    if state["character"] not in CHARACTER_LABELS:
        state["character"] = "обычный"
    state["last_topic"] = data.get("last_topic")
    state["name"] = data.get("name")
    topic_counts_global[chat_id] = data.get("topic_counts", {})
    user_histories[chat_id] = data.get("history", [])[-100:]
    global_stats[chat_id]["mood_count"] = data.get("mood_count", 0)
    global_stats[chat_id]["parrot_blocks"] = data.get("parrot_blocks", 0)

    profile = user_profiles[chat_id]
    saved = data.get("profile", {})
    for key in list(profile.keys()):
        if key in saved:
            profile[key] = saved[key]
    for key, value in saved.items():
        if key not in profile:
            profile[key] = value
    ensure_profile_fields(chat_id)


def save_user_data(chat_id):
    path = _user_file(chat_id)
    bak = _bak_file(chat_id)
    backup = _backup_file(chat_id)
    state = user_states[chat_id]
    ensure_profile_fields(chat_id)
    data = {
        "version": VERSION,
        "name": state["name"],
        "character": state["character"],
        "last_topic": state["last_topic"],
        "topic_counts": topic_counts_global[chat_id],
        "history": user_histories[chat_id][-100:],
        "mood_count": global_stats[chat_id]["mood_count"],
        "parrot_blocks": global_stats[chat_id]["parrot_blocks"],
        "profile": user_profiles[chat_id],
        "last_chat": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    try:
        USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        # .bak рядом с файлом + копия в backups/
        shutil.copy2(path, bak)
        USER_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, backup)
    except OSError:
        pass


def format_pretty_datetime(dt):
    return f"{dt.day} {MONTHS_RU[dt.month - 1]} {dt.year}, {dt.strftime('%H:%M')}"


def format_duration(start, end):
    mins = int((end - start).total_seconds() // 60)
    return f"{mins} минут" if mins >= 1 else "меньше минуты"


def get_active_responses(chat_id):
    pool = dict(responses)
    pool.update(MODE_OVERRIDES.get(user_states[chat_id]["character"], {}))
    return pool


def get_top_topics(chat_id, limit=5):
    ranked = sorted(topic_counts_global[chat_id].items(), key=lambda x: (-x[1], x[0]))
    return ranked[:limit]


def format_top_topics(chat_id, limit=5):
    top = get_top_topics(chat_id, limit)
    if not top:
        return "Пока нет данных — поговори на разные темы!"
    lines = []
    for i, (topic, count) in enumerate(top, 1):
        label = TOPIC_NAMES.get(topic, topic)
        lines.append(f"  {i}. {label} — {count} раз")
    return "\n".join(lines)


def pick_response(chat_id, key, pool):
    options = pool[key]
    last = last_bot_answers[chat_id].get(key)
    available = [o for o in options if o != last] or options
    choice = random.choice(available)
    last_bot_answers[chat_id][key] = choice
    return choice


def add_message(chat_id, user_text, bot_text, topic=None):
    user_histories[chat_id].append({
        "datetime": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "user": user_text,
        "bot": bot_text,
        "topic": topic,
    })


def set_topic(chat_id, topic):
    if topic and topic in responses:
        user_states[chat_id]["last_topic"] = topic
        global_stats[chat_id]["session_topics"].add(topic)
        topic_counts_global[chat_id][topic] = topic_counts_global[chat_id].get(topic, 0) + 1


def profile_memory_hint(chat_id, topic=None):
    if random.random() > 0.3:
        return ""
    prof = user_profiles[chat_id]
    hints = []
    if prof["favorite_game"] and topic in ("игра", "майнкрафт", None):
        hints.append(f"Кстати, ты говорил, что любишь {prof['favorite_game']}.")
    if prof["hobby"]:
        hints.append(f"Помню, твоё хобби — {prof['hobby']}.")
    if prof["favorite_topic"] and topic == prof["favorite_topic"]:
        label = TOPIC_NAMES.get(topic, topic)
        hints.append(f"Это твоя любимая тема — {label}!")
    return random.choice(hints) if hints else ""


def format_profile_text(chat_id):
    state = user_states[chat_id]
    ensure_profile_fields(chat_id)
    prof = user_profiles[chat_id]
    lines = ["── Твой профиль ──", ""]
    if state["name"]:
        lines.append(f"Имя: {state['name']}")
    lines.append(f"Уровень: {prof['level']}")
    lines.append(f"XP: {prof['xp']} (до следующего: {xp_to_next_level(prof)})")
    lines.append(f"Любимая игра: {prof['favorite_game'] or '—'}")
    lines.append(f"Хобби: {prof['hobby'] or '—'}")
    fav = prof["favorite_topic"]
    lines.append(f"Любимая тема: {TOPIC_NAMES.get(fav, fav) if fav else '—'}")
    lines.append(f"Возраст: {prof['age'] or '—'}")
    ach = prof.get("achievements") or []
    lines.append("")
    lines.append("── Ачивки ──")
    if ach:
        for ach_id in ach:
            lines.append(f"  🏆 {ACHIEVEMENT_NAMES.get(ach_id, ach_id)}")
    else:
        lines.append("  Пока пусто. Сыграй в викторину или «угадай число»!")
    if not any(prof[k] for k in ("favorite_game", "hobby", "favorite_topic", "age")):
        lines.append("")
        lines.append("Профиль пуст. Напиши «анкета» — заполним вместе.")
    return "\n".join(lines)


def format_achievements_text(chat_id):
    ensure_profile_fields(chat_id)
    unlocked = user_profiles[chat_id].get("achievements") or []
    lines = ["── Ачивки ChatGR ──", ""]
    for ach_id, title in ACHIEVEMENT_NAMES.items():
        mark = "✅" if ach_id in unlocked else "⬜"
        lines.append(f"{mark} {title}")
    lines.append("")
    lines.append(f"Открыто: {len(unlocked)} / {len(ACHIEVEMENT_NAMES)}")
    return "\n".join(lines)


def build_help_text(chat_id):
    char = user_states[chat_id]["character"]
    top = get_top_topics(chat_id, 3)
    lines = [f"Я ChatGR v{VERSION} — режим: {CHARACTER_LABELS.get(char, char)}", ""]
    if top:
        fav = ", ".join(TOPIC_NAMES.get(t, t) for t, _ in top)
        lines.append(f"Твои топ-темы: {fav}")
        lines.append("")
    lines.append("Темы по разделам:")
    total = 0
    for group, keys in TOPIC_GROUPS.items():
        names = [TOPIC_NAMES.get(k, k) for k in keys]
        total += len(names)
        lines.append(f"  {group}: {', '.join(names)}")
    lines += [
        "",
        "Команды:",
        "  статистика — цифры и топ тем",
        "  история — последние 10 сообщений",
        "  тема — о чём говорили последним",
        "  режим — стиль общения (кнопки)",
        "  анкета / мой профиль — интересы + XP + ачивки",
        "  играть / викторина / угадай число — мини-игры",
        "  /leaderboard или «рекорды» — топ-10 по XP",
        "  ачивки — список достижений",
        "  помощь — этот список",
        "",
        f"Всего тем: {total}. Память: «ещё» или «продолжи».",
        "XP: общение, анкета, игры, викторина.",
    ]
    return "\n".join(lines)


def collect_leaderboard(limit=10):
    """Читает XP всех пользователей из tg_data/users/*.json → топ."""
    players = {}

    def consider(chat_id, name, xp, level):
        chat_id = str(chat_id)
        try:
            xp = int(xp or 0)
            level = int(level or max(1, 1 + xp // XP_PER_LEVEL))
        except (TypeError, ValueError):
            xp, level = 0, 1
        prev = players.get(chat_id)
        if prev is None or xp > prev["xp"]:
            display = (name or "").strip() or f"Игрок {chat_id[-4:]}"
            players[chat_id] = {"chat_id": chat_id, "name": display, "xp": xp, "level": level}

    if USER_DATA_DIR.exists():
        for path in USER_DATA_DIR.glob("*.json"):
            if path.name.endswith(".bak") or path.suffix != ".json":
                continue
            # skip nested folders; only direct user files
            if path.parent != USER_DATA_DIR:
                continue
            try:
                data = _read_json(path)
            except (json.JSONDecodeError, OSError, TypeError):
                continue
            prof = data.get("profile") or {}
            consider(path.stem, data.get("name"), prof.get("xp", 0), prof.get("level", 1))

    # активные в памяти (на случай ещё не сохранённых)
    for cid, prof in user_profiles.items():
        ensure_profile_fields(cid)
        name = user_states.get(cid, {}).get("name")
        consider(cid, name, prof.get("xp", 0), prof.get("level", 1))

    ranked = sorted(players.values(), key=lambda p: (-p["xp"], p["name"].lower()))
    return ranked[:limit]


def format_leaderboard_text(limit=10):
    top = collect_leaderboard(limit)
    lines = [f"── Топ-{limit} ChatGR (по XP) ──", ""]
    if not top:
        lines.append("Пока никого нет. Поболтай или сыграй — и появишься в таблице!")
        return "\n".join(lines)
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    for i, p in enumerate(top, 1):
        medal = medals.get(i, f"{i}.")
        lines.append(f"{medal} {p['name']} — ур. {p['level']} · {p['xp']} XP")
    return "\n".join(lines)


def build_stats_text(chat_id):
    state = user_states[chat_id]
    st = global_stats[chat_id]
    return (
        f"── Статистика ChatGR v{VERSION} ──\n\n"
        f"Режим общения: {CHARACTER_LABELS.get(state['character'], state['character'])}\n\n"
        f"За эту сессию:\n"
        f"  Сообщений: {st['session_messages']}\n"
        f"  Длительность: {format_duration(st['session_start'], datetime.now())}\n"
        f"  Тем обсуждено: {len(st['session_topics'])}\n"
        f"  Темы: {', '.join(TOPIC_NAMES.get(t, t) for t in sorted(st['session_topics'])) or '—'}\n\n"
        f"Всего в истории:\n"
        f"  Сообщений: {len(user_histories[chat_id])}\n"
        f"  Настроение: {st['mood_count']} ответов\n"
        f"  Попугаи: {st['parrot_blocks']} раз\n"
        f"  Последняя тема: {TOPIC_NAMES.get(state['last_topic'], state['last_topic'] or '—')}\n\n"
        f"── Топ твоих тем ──\n{format_top_topics(chat_id, 5)}\n\n"
        f"{'Тебя зовут ' + state['name'] if state['name'] else 'Имя не знаю.'}"
    )


def show_recent_history(chat_id):
    recent = user_histories[chat_id][-10:]
    if not recent:
        return "История пока пуста — мы только начали разговор!"
    lines = [f"Последние {len(recent)} сообщений:", ""]
    for item in recent:
        try:
            dt = datetime.strptime(item["datetime"], "%Y-%m-%d %H:%M")
            pretty = format_pretty_datetime(dt)
        except (ValueError, KeyError):
            pretty = item.get("datetime", "?")
        tag = ""
        if item.get("topic"):
            tag = f" [{TOPIC_NAMES.get(item['topic'], item['topic'])}]"
        lines += [f"[{pretty}]{tag}", f"  Ты:  {item['user']}", f"  Бот: {item['bot']}", ""]
    return "\n".join(lines).strip()


def try_save_profile_field(chat_id, user_input):
    prof = user_profiles[chat_id]
    for phrase in ("моя любимая игра", "любимая игра", "обожаю игру"):
        if phrase in user_input:
            rest = user_input.split(phrase, 1)[1].strip(" :—-.,!?")
            if rest:
                prof["favorite_game"] = rest[:60]
                save_user_data(chat_id)
                return f"Запомнил: любимая игра — {prof['favorite_game']}!"
    for phrase in ("моё хобби", "мое хобби", "моё увлечение", "мое увлечение"):
        if phrase in user_input:
            rest = user_input.split(phrase, 1)[1].strip(" :—-.,!?")
            if rest:
                prof["hobby"] = rest[:60]
                save_user_data(chat_id)
                return f"Запомнил: хобби — {prof['hobby']}!"
    return None


def is_parrot(chat_id, user_input):
    if user_input in ("пока", "выход", "статистика", "история", "помощь"):
        return False
    recent = user_states[chat_id]["recent_msgs"][-PARROT_LIMIT:]
    return len(recent) >= PARROT_LIMIT and all(m == user_input for m in recent)


def find_topic(user_input, words):
    age_hints = (
        "когда ты родился", "когда родился", "когда создан",
        "дата создания", "когда тебя создали",
    )
    if ("сколько" in words and "лет" in words) or any(h in user_input for h in age_hints):
        return "возраст"
    for phrase, topic in sorted(PHRASE_TO_TOPIC, key=lambda x: len(x[0]), reverse=True):
        if phrase in user_input:
            return topic
    for topic, roots in topic_roots:
        for root in roots:
            if any(word.startswith(root) for word in words):
                return topic
    return None


def find_mood(words):
    for mood in sorted(mood_responses, key=len, reverse=True):
        if mood in words:
            return mood
    return None


def wants_continue(user_input):
    return any(p in user_input for p in CONTINUE_PHRASES)


def parse_character_command(user_input):
    if not user_input.startswith("режим"):
        return None
    parts = user_input.split()
    if len(parts) == 1 or user_input in ("режим", "какой режим", "мой режим"):
        return "show"
    return CHARACTER_ALIASES.get(parts[-1])


def bot_reply(message, chat_id, text, user_text="", use_name=False, topic=None, reply_markup=None, xp=0):
    hint = profile_memory_hint(chat_id, topic) if user_text else ""
    if hint:
        text = f"{text}\n{hint}"
    name = user_states[chat_id]["name"]
    if use_name and name and name.lower() not in text.lower() and random.random() < 0.35:
        text = f"{name}, {text[0].lower()}{text[1:]}" if text else text
    level_msg = add_xp(chat_id, xp, save=False) if xp else None
    if level_msg:
        text = f"{text}\n\n{level_msg}"
    if user_text or xp:
        if user_text:
            add_message(chat_id, user_text, text, topic=topic)
        save_user_data(chat_id)
    bot.reply_to(message, text, reply_markup=reply_markup)


def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("Помощь", "Статистика")
    markup.row("Анкета", "Играть")
    markup.row("Режим", "Профиль")
    return markup


def mode_inline_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("Обычный", callback_data="mode:обычный"),
        types.InlineKeyboardButton("Весёлый", callback_data="mode:весёлый"),
        types.InlineKeyboardButton("Мемный", callback_data="mode:мемный"),
        types.InlineKeyboardButton("Сарказм", callback_data="mode:сарказм"),
    )
    return markup


def play_inline_keyboard():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Угадай число", callback_data="play:guess"))
    markup.add(types.InlineKeyboardButton("Викторина", callback_data="play:quiz"))
    markup.add(types.InlineKeyboardButton("Отмена", callback_data="play:cancel"))
    return markup


def start_menu_inline_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("Помощь", callback_data="menu:help"),
        types.InlineKeyboardButton("Статистика", callback_data="menu:stats"),
        types.InlineKeyboardButton("Профиль", callback_data="menu:profile"),
        types.InlineKeyboardButton("Играть", callback_data="menu:play"),
        types.InlineKeyboardButton("Режим", callback_data="menu:mode"),
        types.InlineKeyboardButton("Топ-10", callback_data="menu:leaderboard"),
    )
    return markup


def mode_menu_text(chat_id):
    char = user_states[chat_id]["character"]
    return (
        f"Сейчас режим: {CHARACTER_LABELS.get(char, char)}.\n"
        "Выбери стиль кнопкой или напиши: режим весёлый / мемный / сарказм / обычный"
    )


def play_menu_text():
    return (
        "── Мини-игры ChatGR ──\n\n"
        "Выбери игру кнопкой:\n"
        "• угадай число\n"
        "• викторина (5 вопросов, кнопки)\n\n"
        "Или напиши «угадай число» / «викторина».\n"
        "В игре: «стоп» — выйти."
    )


def start_guess_game(chat_id):
    user_states[chat_id]["game_state"] = {
        "type": "guess",
        "secret": random.randint(1, 100),
        "attempts": 0,
        "max_attempts": 10,
    }
    return (
        "Загадал число от 1 до 100. У тебя 10 попыток.\n"
        "Пиши число. «стоп» — выйти из игры."
    )


def is_quiz_command(user_input):
    if user_input in QUIZ_START_EXACT:
        return True
    return any(p in user_input for p in QUIZ_START_PHRASES)


def quiz_options_keyboard(chat_id):
    """Inline-кнопки вариантов ответа (telebot InlineKeyboardMarkup)."""
    gstate = user_states[chat_id]["game_state"]
    qdata = gstate["questions"][gstate["index"]]
    markup = types.InlineKeyboardMarkup()
    for i, opt in enumerate(qdata["options"]):
        markup.add(
            types.InlineKeyboardButton(
                f"{i + 1}. {opt}",
                callback_data=f"quiz:{i}",
            )
        )
    return markup


def quiz_question_text(chat_id):
    gstate = user_states[chat_id]["game_state"]
    n = gstate["index"] + 1
    total = len(gstate["questions"])
    q = gstate["questions"][gstate["index"]]["q"]
    return f"Викторина ChatGR — вопрос {n}/{total}\n\n{q}\n\nЖми кнопку с ответом:"


def start_quiz_game(chat_id):
    n = min(5, len(QUIZ_QUESTIONS))
    questions = random.sample(list(QUIZ_QUESTIONS), n)
    # копии, чтобы options были list
    packed = []
    for item in questions:
        packed.append({
            "q": item["q"],
            "options": list(item["options"]),
            "correct": item["correct"],
        })
    user_states[chat_id]["game_state"] = {
        "type": "quiz",
        "questions": packed,
        "index": 0,
        "score": 0,
    }
    return quiz_question_text(chat_id), quiz_options_keyboard(chat_id)


def process_quiz_answer(chat_id, choice):
    """
    Обработка ответа викторины (0–2).
    Возвращает (text, markup|None, finished: bool).
    """
    gstate = user_states[chat_id].get("game_state")
    if not gstate or gstate.get("type") != "quiz":
        return "Викторина не активна. Напиши «викторина».", None, True

    if choice is None or choice < 0 or choice > 2:
        return "Выбери вариант кнопкой или цифрой 1, 2, 3.", quiz_options_keyboard(chat_id), False

    qdata = gstate["questions"][gstate["index"]]
    notes = []
    if choice == qdata["correct"]:
        gstate["score"] += 1
        feedback = "Верно! ✅"
        xp_note = add_xp(chat_id, XP_QUIZ_CORRECT, save=False, announce_xp=True)
        if xp_note:
            notes.append(xp_note)
    else:
        right = qdata["options"][qdata["correct"]]
        feedback = f"Неверно. Правильно: {right}."

    gstate["index"] += 1
    total = len(gstate["questions"])

    if gstate["index"] >= total:
        score = gstate["score"]
        user_states[chat_id]["game_state"] = None
        finish_xp = XP_QUIZ_FINISH_PER_POINT * score
        if finish_xp:
            xp_note = add_xp(chat_id, finish_xp, save=False, announce_xp=True)
            if xp_note:
                notes.append(xp_note)
        title = unlock_achievement(chat_id, "first_quiz")
        if title:
            notes.append(f"🏆 {title}")
        if score == total:
            title = unlock_achievement(chat_id, "perfect_quiz")
            if title:
                notes.append(f"🏆 {title}")
        save_user_data(chat_id)
        extra = "\n".join(notes)
        text = f"{feedback}\n\nВикторина окончена! Счёт: {score} из {total}. 🎉"
        if extra:
            text = f"{text}\n{extra}"
        return text, None, True

    save_user_data(chat_id)
    next_text = quiz_question_text(chat_id)
    body = f"{feedback}"
    if notes:
        body = f"{body}\n" + "\n".join(notes)
    text = f"{body}\n\n{next_text}"
    return text, quiz_options_keyboard(chat_id), False


def build_greeting(chat_id):
    state = user_states[chat_id]
    lines = [f"=== ChatGR v{VERSION} ==="]
    if state["name"]:
        greet = f"С возвращением, {state['name']}!"
        top = get_top_topics(chat_id, 1)
        if top:
            greet += f" Чаще всего ты говоришь про {TOPIC_NAMES.get(top[0][0], top[0][0])}."
        elif state["last_topic"]:
            greet += f" В прошлый раз говорили про {TOPIC_NAMES.get(state['last_topic'], state['last_topic'])}."
        lines.append(greet)
    else:
        lines.append("Привет! Я твой адаптивный бот. Поболтаем?")
    lines.append("")
    lines.append("Команды: статистика, история, тема, помощь, анкета, профиль, играть, викторина, /leaderboard")
    return "\n".join(lines)


def setup_bot_commands():
    bot.set_my_commands([
        types.BotCommand("start", "Начать / перезапустить"),
        types.BotCommand("help", "Список тем и команд"),
        types.BotCommand("stats", "Статистика"),
        types.BotCommand("profile", "Мой профиль"),
        types.BotCommand("play", "Мини-игры"),
        types.BotCommand("mode", "Сменить режим общения"),
        types.BotCommand("leaderboard", "Топ-10 по XP"),
        types.BotCommand("quiz", "Викторина"),
    ])


@bot.message_handler(commands=["start"])
def start_cmd(message):
    init_user(message.chat.id)
    cid = str(message.chat.id)
    global_stats[cid] = _default_stats()
    bot.send_message(
        message.chat.id,
        build_greeting(cid),
        reply_markup=main_keyboard(),
    )
    bot.send_message(
        message.chat.id,
        "Быстрое меню:",
        reply_markup=start_menu_inline_keyboard(),
    )


@bot.message_handler(commands=["help"])
def help_cmd(message):
    init_user(message.chat.id)
    bot_reply(message, str(message.chat.id), build_help_text(str(message.chat.id)))


@bot.message_handler(commands=["stats"])
def stats_cmd(message):
    init_user(message.chat.id)
    bot_reply(message, str(message.chat.id), build_stats_text(str(message.chat.id)))


@bot.message_handler(commands=["profile"])
def profile_cmd(message):
    init_user(message.chat.id)
    bot_reply(message, str(message.chat.id), format_profile_text(str(message.chat.id)))


@bot.message_handler(commands=["play"])
def play_cmd(message):
    init_user(message.chat.id)
    cid = str(message.chat.id)
    bot_reply(message, cid, play_menu_text(), reply_markup=play_inline_keyboard())


@bot.message_handler(commands=["mode"])
def mode_cmd(message):
    init_user(message.chat.id)
    cid = str(message.chat.id)
    bot_reply(message, cid, mode_menu_text(cid), reply_markup=mode_inline_keyboard())


@bot.message_handler(commands=["leaderboard", "top"])
def leaderboard_cmd(message):
    init_user(message.chat.id)
    bot_reply(message, str(message.chat.id), format_leaderboard_text(10))


@bot.message_handler(commands=["quiz"])
def quiz_cmd(message):
    init_user(message.chat.id)
    cid = str(message.chat.id)
    text, markup = start_quiz_game(cid)
    bot_reply(message, cid, text, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: True)
def on_callback(call):
    init_user(call.message.chat.id)
    cid = str(call.message.chat.id)
    data = call.data or ""

    try:
        if data.startswith("mode:"):
            mode = data.split(":", 1)[1]
            if mode not in CHARACTER_LABELS:
                bot.answer_callback_query(call.id, "Неизвестный режим")
                return
            user_states[cid]["character"] = mode
            save_user_data(cid)
            label = CHARACTER_LABELS[mode]
            bot.answer_callback_query(call.id, f"Режим: {label}")
            bot.edit_message_text(
                f"Режим общения: {label}. Поговорим в новом стиле!",
                call.message.chat.id,
                call.message.message_id,
            )
            return

        if data == "play:guess":
            text = start_guess_game(cid)
            bot.answer_callback_query(call.id, "Игра началась!")
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id)
            return

        if data == "play:quiz":
            text, markup = start_quiz_game(cid)
            bot.answer_callback_query(call.id, "Викторина!")
            bot.edit_message_text(
                text,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup,
            )
            return

        if data == "play:cancel":
            bot.answer_callback_query(call.id, "Отменено")
            bot.edit_message_text("Меню игр закрыто.", call.message.chat.id, call.message.message_id)
            return

        if data.startswith("quiz:"):
            try:
                choice = int(data.split(":", 1)[1])
            except ValueError:
                bot.answer_callback_query(call.id, "Ошибка")
                return
            text, markup, finished = process_quiz_answer(cid, choice)
            bot.answer_callback_query(call.id, "Ответ принят" if not finished else "Финиш!")
            bot.edit_message_text(
                text,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup,
            )
            return

        if data == "menu:help":
            bot.answer_callback_query(call.id)
            bot.send_message(call.message.chat.id, build_help_text(cid))
            return
        if data == "menu:stats":
            bot.answer_callback_query(call.id)
            bot.send_message(call.message.chat.id, build_stats_text(cid))
            return
        if data == "menu:profile":
            bot.answer_callback_query(call.id)
            bot.send_message(call.message.chat.id, format_profile_text(cid))
            return
        if data == "menu:play":
            bot.answer_callback_query(call.id)
            bot.send_message(call.message.chat.id, play_menu_text(), reply_markup=play_inline_keyboard())
            return
        if data == "menu:mode":
            bot.answer_callback_query(call.id)
            bot.send_message(call.message.chat.id, mode_menu_text(cid), reply_markup=mode_inline_keyboard())
            return
        if data == "menu:leaderboard":
            bot.answer_callback_query(call.id)
            bot.send_message(call.message.chat.id, format_leaderboard_text(10))
            return

        bot.answer_callback_query(call.id)
    except Exception as e:
        print(f"[ChatGR] callback error: {e}")
        try:
            bot.answer_callback_query(call.id, "Ошибка, попробуй ещё раз")
        except Exception:
            pass


@bot.message_handler(func=lambda msg: msg.content_type == "text")
def handle_all_messages(message):
    init_user(message.chat.id)
    cid = str(message.chat.id)
    user_input = message.text.lower().strip()
    words = user_input.split()

    global_stats[cid]["session_messages"] += 1
    user_states[cid]["recent_msgs"].append(user_input)
    if len(user_states[cid]["recent_msgs"]) > 10:
        user_states[cid]["recent_msgs"].pop(0)

    if not user_input:
        bot_reply(message, cid, "Эй, клавиатура не кусается — напиши хоть буковку!", user_input)
        return

    if is_parrot(cid, user_input):
        global_stats[cid]["parrot_blocks"] += 1
        bot_reply(message, cid, random.choice(PARROT_REPLIES), user_input)
        return

    if user_states[cid]["game_state"]:
        gstate = user_states[cid]["game_state"]
        if user_input in ("стоп", "выход", "выход из игры", "стоп игра", "хватит"):
            user_states[cid]["game_state"] = None
            bot_reply(message, cid, "Игра окончена. Возвращаемся в обычный чат!", user_input)
            return

        # --- Викторина (текст 1/2/3 или кнопки) ---
        if gstate.get("type") == "quiz":
            choice = None
            if user_input in ("1", "2", "3"):
                choice = int(user_input) - 1
            else:
                qdata = gstate["questions"][gstate["index"]]
                for i, opt in enumerate(qdata["options"]):
                    if user_input == opt.lower() or opt.lower() in user_input:
                        choice = i
                        break
            if choice is None:
                bot_reply(
                    message, cid,
                    "Ответь кнопкой или цифрой 1, 2, 3. «стоп» — выйти.",
                    user_input,
                    reply_markup=quiz_options_keyboard(cid),
                )
                return
            text, markup, _finished = process_quiz_answer(cid, choice)
            bot_reply(message, cid, text, user_input, reply_markup=markup)
            return

        # --- Угадай число ---
        if not user_input.isdigit():
            bot_reply(message, cid, "Нужно число от 1 до 100. Или «стоп» — выйти.", user_input)
            return
        guess = int(user_input)
        gstate["attempts"] += 1
        left = gstate["max_attempts"] - gstate["attempts"]
        if guess == gstate["secret"]:
            tries = gstate["attempts"]
            secret = gstate["secret"]
            user_states[cid]["game_state"] = None
            notes = []
            xp_note = add_xp(cid, XP_GAME_WIN, save=False, announce_xp=True)
            if xp_note:
                notes.append(xp_note)
            title = unlock_achievement(cid, "first_guess")
            if title:
                notes.append(f"🏆 {title}")
            if tries <= 3:
                title = unlock_achievement(cid, "guess_master")
                if title:
                    notes.append(f"🏆 {title}")
            save_user_data(cid)
            text = f"Верно! Это {secret}. Угадал за {tries} попыток. 🎉"
            if notes:
                text = f"{text}\n" + "\n".join(notes)
            bot_reply(message, cid, text, user_input)
        elif left <= 0:
            secret = gstate["secret"]
            user_states[cid]["game_state"] = None
            bot_reply(message, cid, f"Попытки кончились. Загаданное число было {secret}.", user_input)
        else:
            hint = "меньше" if guess > gstate["secret"] else "больше"
            bot_reply(message, cid, f"Моё число {hint}! Осталось попыток: {left}.", user_input)
        return

    if user_states[cid]["anketa_active"]:
        if user_input in ("отмена", "стоп", "выход"):
            user_states[cid]["anketa_active"] = False
            bot_reply(message, cid, "Анкета отменена. Можешь продолжить обычный разговор.", user_input)
            return
        idx = user_states[cid]["anketa_index"]
        field, _ = ANKETA_STEPS[idx]
        if user_input in ("пропустить", "не знаю", "нет"):
            value = None
        else:
            value = user_input.strip()[:60]
        if field == "favorite_topic":
            value = find_topic(user_input, words) or value
        user_profiles[cid][field] = value
        user_states[cid]["anketa_index"] += 1
        if user_states[cid]["anketa_index"] >= len(ANKETA_STEPS):
            user_states[cid]["anketa_active"] = False
            user_profiles[cid]["profile_complete"] = any(
                user_profiles[cid][k] for k in ("favorite_game", "hobby", "favorite_topic", "age")
            )
            level_msg = add_xp(cid, XP_ANKETA, save=False)
            text = f"Анкета готова!\n\n{format_profile_text(cid)}"
            if level_msg:
                text = f"{text}\n\n{level_msg}"
            bot_reply(message, cid, text, user_input)
        else:
            bot_reply(message, cid, ANKETA_STEPS[user_states[cid]["anketa_index"]][1], user_input)
        return

    if user_input in ("помощь", "команды", "что ты умеешь", "темы"):
        bot_reply(message, cid, build_help_text(cid), user_input)
        return

    if "статистика" in user_input:
        bot_reply(message, cid, build_stats_text(cid), user_input)
        return

    if user_input in ("история", "моя история", "покажи историю"):
        bot_reply(message, cid, show_recent_history(cid), user_input)
        return

    if user_input in ("тема", "какая тема", "о чём мы говорили"):
        lt = user_states[cid]["last_topic"]
        if lt:
            label = TOPIC_NAMES.get(lt, lt)
            bot_reply(message, cid, f"Последняя тема: {label}. Напиши «продолжи» — поговорим ещё.", user_input)
        else:
            bot_reply(message, cid, "Пока нет темы. Начни — например, «люблю космос».", user_input)
        return

    if user_input in ("очистить историю", "сброс истории", "удалить историю"):
        user_histories[cid].clear()
        last_bot_answers[cid].clear()
        global_stats[cid]["session_topics"].clear()
        save_user_data(cid)
        bot_reply(message, cid, "История очищена! Начинаем с чистого листа.", user_input)
        return

    mode_cmd = parse_character_command(user_input)
    if mode_cmd == "show":
        bot_reply(message, cid, mode_menu_text(cid), user_input, reply_markup=mode_inline_keyboard())
        return
    if mode_cmd:
        user_states[cid]["character"] = mode_cmd
        bot_reply(
            message, cid,
            f"Режим общения: {CHARACTER_LABELS[mode_cmd]}. Поговорим в новом стиле!",
            user_input,
        )
        return

    if user_input in ("анкета", "заполни анкету", "профиль"):
        user_states[cid]["anketa_active"] = True
        user_states[cid]["anketa_index"] = 0
        bot_reply(message, cid, f"Анкета ChatGR — {len(ANKETA_STEPS)} вопроса.\n{ANKETA_STEPS[0][1]}", user_input)
        return

    if user_input in ("мой профиль", "покажи профиль", "что ты знаешь обо мне"):
        bot_reply(message, cid, format_profile_text(cid), user_input)
        return

    if user_input in ("сброс профиля", "очистить профиль", "удалить профиль"):
        prof = user_profiles[cid]
        for key in _default_profile():
            if key == "profile_complete":
                prof[key] = False
            elif key in ("xp", "level", "achievements"):
                continue  # прогресс и ачивки сохраняем
            else:
                prof[key] = None
        ensure_profile_fields(cid)
        save_user_data(cid)
        bot_reply(message, cid, "Профиль очищен (уровень, XP и ачивки сохранены). Напиши «анкета».", user_input)
        return

    if user_input in ("рекорды", "лидерборд", "топ", "топ 10", "топ-10", "таблица лидеров"):
        bot_reply(message, cid, format_leaderboard_text(10), user_input)
        return

    if user_input in ("ачивки", "достижения", "мои ачивки", "ачивка"):
        bot_reply(message, cid, format_achievements_text(cid), user_input)
        return

    if user_input in ("играть", "мини-игра", "меню игр", "игра", "игры"):
        bot_reply(message, cid, play_menu_text(), user_input, reply_markup=play_inline_keyboard())
        return

    if is_quiz_command(user_input):
        text, markup = start_quiz_game(cid)
        bot_reply(message, cid, text, user_input, reply_markup=markup)
        return

    if user_input in ("угадай число", "угадай"):
        bot_reply(message, cid, start_guess_game(cid), user_input)
        return

    profile_msg = try_save_profile_field(cid, user_input)
    if profile_msg:
        bot_reply(message, cid, profile_msg, user_input)
        return

    if user_input in ("сброс имени", "забудь имя", "забыть имя"):
        user_states[cid]["name"] = None
        save_user_data(cid)
        bot_reply(message, cid, "Хорошо, забыл твоё имя. Представься: «меня зовут ...»", user_input)
        return

    if "меня зовут" in user_input:
        rest = user_input.split("меня зовут", 1)[1].strip(" .,!?")
        if rest:
            user_states[cid]["name"] = rest.split()[0].capitalize()
            save_user_data(cid)
            bot_reply(
                message, cid,
                f"Приятно познакомиться, {user_states[cid]['name']}! Запомнил — буду так обращаться.",
                user_input,
            )
        return

    if any(p in user_input for p in ("как тебя зовут", "тебя зовут", "твоё имя", "твое имя")):
        if user_states[cid]["name"]:
            bot_reply(message, cid, f"Я ChatGR. А тебя я знаю — тебя зовут {user_states[cid]['name']}!", user_input)
        else:
            bot_reply(message, cid, pick_response(cid, "имя", get_active_responses(cid)), user_input, topic="имя")
        return

    if user_states[cid]["name"] and any(p in user_input for p in ("как меня зовут", "моё имя", "мое имя", "помнишь меня")):
        bot_reply(message, cid, f"Конечно помню — тебя зовут {user_states[cid]['name']}!", user_input)
        return

    if wants_continue(user_input) and user_states[cid]["last_topic"]:
        lt = user_states[cid]["last_topic"]
        hint = CONTINUE_HINTS.get(lt, "Расскажи, что именно тебя интересует?")
        extra = pick_response(cid, lt, get_active_responses(cid))
        label = TOPIC_NAMES.get(lt, lt)
        bot_reply(
            message, cid,
            f"Продолжаем про {label}. {extra}\n{hint}",
            user_input,
            topic=lt,
            xp=XP_CONTINUE,
        )
        return

    found = False
    mood = find_mood(words)
    if mood:
        bot_reply(
            message, cid,
            pick_response(cid, mood, mood_responses),
            user_input,
            topic="настроение",
            xp=XP_MOOD,
        )
        user_states[cid]["last_topic"] = "настроение"
        global_stats[cid]["mood_count"] += 1
        found = True

    if not found:
        topic = find_topic(user_input, words)
        if topic:
            set_topic(cid, topic)
            # topic_explorer проверяется внутри add_xp → check_progress_achievements
            bot_reply(
                message, cid,
                pick_response(cid, topic, get_active_responses(cid)),
                user_input,
                use_name=True,
                topic=topic,
                xp=XP_TOPIC,
            )
            found = True

    if not found:
        char = user_states[cid]["character"]
        lt = user_states[cid]["last_topic"]
        if lt:
            label = TOPIC_NAMES.get(lt, lt)
            bot_reply(
                message, cid,
                f"Не совсем понял. Мы говорили про {label} — напиши «продолжи» или «помощь».",
                user_input,
            )
        else:
            bot_reply(message, cid, MODE_FALLBACKS.get(char, MODE_FALLBACKS["обычный"]), user_input)


if __name__ == "__main__":
    setup_bot_commands()
    print(f"ChatGR TG v{VERSION} запущен и готов к работе!")
    bot.infinity_polling()