# 📚 EnglishCard — приложение для изучения английского языка

## Описание

EnglishCard — это веб-приложение для изучения английских слов в формате викторины. Приложение позволяет:

- Изучать слова с выбором перевода из 4 вариантов
- Добавлять персональные слова
- Удалять персональные слова
- Отслеживать статистику изучения
- Просматривать схему базы данных

## Скриншоты приложения

![Скриншот приложения](screenshot.png)

## Требования к системе

- Python 3.12 или выше
- PostgreSQL 14 или выше

## Установка и запуск

## Схема базы данных

База данных состоит из 4 таблиц:

### Таблица `users` — пользователи

| Поле | Тип | Описание |
|:---|:---|:---|
| `id` | SERIAL (PK) | Уникальный идентификатор пользователя |
| `username` | VARCHAR(100) | Имя пользователя |
| `created_at` | TIMESTAMP | Дата регистрации |

### Таблица `common_words` — общие слова

| Поле | Тип | Описание |
|:---|:---|:---|
| `id` | SERIAL (PK) | Уникальный идентификатор слова |
| `russian_word` | VARCHAR(200) | Слово на русском |
| `english_word` | VARCHAR(200) | Перевод на английский |
| `created_at` | TIMESTAMP | Дата добавления |

### Таблица `user_words` — персональные слова пользователей

| Поле | Тип | Описание |
|:---|:---|:---|
| `id` | SERIAL (PK) | Уникальный идентификатор |
| `user_id` | INTEGER (FK → users.id) | Владелец слова |
| `russian_word` | VARCHAR(200) | Слово на русском |
| `english_word` | VARCHAR(200) | Перевод на английский |
| `created_at` | TIMESTAMP | Дата добавления |

### Таблица `learning_stats` — статистика изучения

| Поле | Тип | Описание |
|:---|:---|:---|
| `id` | SERIAL (PK) | Уникальный идентификатор |
| `user_id` | INTEGER (FK → users.id) | Пользователь |
| `word_id` | INTEGER | ID слова (из common_words или user_words) |
| `word_type` | VARCHAR(20) | Тип слова: 'common' или 'personal' |
| `correct_answers` | INTEGER | Количество правильных ответов |
| `total_attempts` | INTEGER | Общее количество попыток |
| `last_reviewed` | TIMESTAMP | Дата последнего повторения |

### Связи между таблицами
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ users │ │ user_words │ │ learning_stats │
├─────────────────┤ ├─────────────────┤ ├─────────────────┤
│ id (PK) │────<│ user_id (FK) │ │ id (PK) │
│ username │ │ id (PK) │ │ user_id (FK) │
│ created_at │ │ russian_word │ │ word_id │
└─────────────────┘ │ english_word │ │ word_type │
│ created_at │ │ correct_answers │
┌─────────────────┐ └─────────────────┘ │ total_attempts │
│ common_words │ │ last_reviewed │
├─────────────────┤ └─────────────────┘
│ id (PK) │
│ russian_word │
│ english_word │
│ created_at │
└─────────────────┘
### 1. Клонирование репозитория

```bash
git clone https://github.com/ivanmyskov89-beep/english_card.git
cd english_card
