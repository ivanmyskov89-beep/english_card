"""
EnglishCard - Приложение для изучения английского языка
Исправленная версия: квиз с повторной попыткой при ошибке
"""

import streamlit as st
import psycopg2
import random
from datetime import datetime

# ============================================================
# НАСТРОЙКА СТРАНИЦЫ
# ============================================================
st.set_page_config(
    page_title="EnglishCard - Изучение английского",
    page_icon="📚",
    layout="wide"
)

st.markdown("""
    <style>
    .stButton button { width: 100%; border-radius: 10px; font-size: 16px; }
    .correct { background-color: #28a745; color: white; padding: 10px; border-radius: 5px; }
    .incorrect { background-color: #dc3545; color: white; padding: 10px; border-radius: 5px; }
    .warning { background-color: #ffc107; color: black; padding: 10px; border-radius: 5px; }
    </style>
""", unsafe_allow_html=True)


# ============================================================
# РАБОТА С БАЗОЙ ДАННЫХ
# ============================================================

def get_db_connection():
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="english_card",
            user="postgres",
            password="postgres"
        )
        return conn
    except Exception as e:
        st.error(f"Ошибка подключения к БД: {e}")
        return None


def init_database():
    conn = get_db_connection()
    if not conn:
        return False
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(100) UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS common_words (
                    id SERIAL PRIMARY KEY,
                    russian_word VARCHAR(200) NOT NULL,
                    english_word VARCHAR(200) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_words (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    russian_word VARCHAR(200) NOT NULL,
                    english_word VARCHAR(200) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, russian_word, english_word)
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS learning_stats (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    word_id INTEGER NOT NULL,
                    word_type VARCHAR(20) NOT NULL,
                    correct_answers INTEGER DEFAULT 0,
                    total_attempts INTEGER DEFAULT 0,
                    last_reviewed TIMESTAMP,
                    CHECK (word_type IN ('common', 'personal'))
                )
            """)
            cur.execute("SELECT COUNT(*) FROM common_words")
            if cur.fetchone()[0] == 0:
                common_words = [
                    ('Привет', 'Hello'), ('Пока', 'Goodbye'), ('Спасибо', 'Thank you'),
                    ('Пожалуйста', 'Please'), ('Да', 'Yes'), ('Нет', 'No'),
                    ('Красный', 'Red'), ('Синий', 'Blue'), ('Зеленый', 'Green'),
                    ('Желтый', 'Yellow'), ('Большой', 'Big'), ('Маленький', 'Small')
                ]
                for ru, en in common_words:
                    cur.execute("INSERT INTO common_words (russian_word, english_word) VALUES (%s, %s)", (ru, en))
            conn.commit()
            return True
    except Exception as e:
        st.error(f"Ошибка инициализации БД: {e}")
        return False
    finally:
        conn.close()


def login_user(username):
    if not username or username.strip() == "":
        return None
    conn = get_db_connection()
    if not conn:
        return None
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE username = %s", (username,))
            user = cur.fetchone()
            if user:
                user_id = user[0]
            else:
                cur.execute("INSERT INTO users (username) VALUES (%s) RETURNING id", (username,))
                user_id = cur.fetchone()[0]
            conn.commit()
            return user_id
    except Exception as e:
        st.error(f"Ошибка авторизации: {e}")
        return None
    finally:
        conn.close()


def get_user_words(user_id):
    conn = get_db_connection()
    if not conn:
        return []
    words = []
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, russian_word, english_word, 'common' FROM common_words")
            for row in cur.fetchall():
                words.append({'id': row[0], 'russian_word': row[1], 'english_word': row[2], 'word_type': row[3]})
            cur.execute("SELECT id, russian_word, english_word, 'personal' FROM user_words WHERE user_id = %s", (user_id,))
            for row in cur.fetchall():
                words.append({'id': row[0], 'russian_word': row[1], 'english_word': row[2], 'word_type': row[3]})
        return words
    except Exception as e:
        st.error(f"Ошибка получения слов: {e}")
        return []
    finally:
        conn.close()


def add_personal_word(user_id, russian_word, english_word):
    if not russian_word or not english_word:
        return False
    conn = get_db_connection()
    if not conn:
        return False
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM user_words WHERE user_id = %s AND russian_word = %s AND english_word = %s",
                       (user_id, russian_word, english_word))
            if cur.fetchone():
                return False
            cur.execute("INSERT INTO user_words (user_id, russian_word, english_word) VALUES (%s, %s, %s)",
                       (user_id, russian_word, english_word))
            conn.commit()
            return True
    except Exception as e:
        st.error(f"Ошибка добавления слова: {e}")
        return False
    finally:
        conn.close()


def delete_personal_word(user_id, word_id):
    conn = get_db_connection()
    if not conn:
        return False
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM user_words WHERE id = %s AND user_id = %s", (word_id, user_id))
            conn.commit()
            return cur.rowcount > 0
    except Exception as e:
        st.error(f"Ошибка удаления слова: {e}")
        return False
    finally:
        conn.close()


def update_stats(user_id, word_id, word_type, is_correct):
    conn = get_db_connection()
    if not conn:
        return
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, correct_answers, total_attempts FROM learning_stats WHERE user_id = %s AND word_id = %s AND word_type = %s",
                       (user_id, word_id, word_type))
            stats = cur.fetchone()
            if stats:
                new_correct = stats[1] + (1 if is_correct else 0)
                new_total = stats[2] + 1
                cur.execute("UPDATE learning_stats SET correct_answers = %s, total_attempts = %s, last_reviewed = %s WHERE id = %s",
                           (new_correct, new_total, datetime.now(), stats[0]))
            else:
                cur.execute("INSERT INTO learning_stats (user_id, word_id, word_type, correct_answers, total_attempts, last_reviewed) VALUES (%s, %s, %s, %s, %s, %s)",
                           (user_id, word_id, word_type, 1 if is_correct else 0, 1, datetime.now()))
            conn.commit()
    except Exception as e:
        st.error(f"Ошибка обновления статистики: {e}")
    finally:
        conn.close()


def get_statistics(user_id):
    conn = get_db_connection()
    if not conn:
        return {}
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(DISTINCT word_id), SUM(correct_answers), SUM(total_attempts) FROM learning_stats WHERE user_id = %s", (user_id,))
            stats = cur.fetchone()
            total_words = stats[0] or 0
            total_correct = stats[1] or 0
            total_attempts = stats[2] or 0
            accuracy = (total_correct / total_attempts * 100) if total_attempts > 0 else 0
            cur.execute("SELECT word_type, correct_answers, total_attempts, last_reviewed FROM learning_stats WHERE user_id = %s ORDER BY last_reviewed DESC LIMIT 10", (user_id,))
            recent = cur.fetchall()
            return {'total_words': total_words, 'total_correct': total_correct, 'total_attempts': total_attempts, 'accuracy': round(accuracy, 2), 'recent': recent}
    except Exception as e:
        st.error(f"Ошибка получения статистики: {e}")
        return {}
    finally:
        conn.close()


def get_word_count(user_id):
    return len(get_user_words(user_id))


def generate_options(correct_word, all_words):
    correct_translation = correct_word['english_word']
    other_translations = list(set([w['english_word'] for w in all_words if w['english_word'] != correct_translation]))
    if len(other_translations) < 3:
        return None
    random.shuffle(other_translations)
    options = [correct_translation] + other_translations[:3]
    random.shuffle(options)
    return options


def render_sidebar():
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/2232/2232688.png", width=80)
        st.title("EnglishCard")
        if 'user_id' not in st.session_state or st.session_state.user_id is None:
            st.subheader("АВТОРИЗАЦИЯ")
            username = st.text_input("Введите ваше имя:")
            if st.button("Войти", use_container_width=True):
                if username:
                    user_id = login_user(username)
                    if user_id:
                        st.session_state.user_id = user_id
                        st.session_state.username = username
                        st.session_state.quiz_attempts = {}
                        st.rerun()
        else:
            st.success(f"ПРИВЕТ, {st.session_state.username}!")
            st.metric("СЛОВ В СЛОВАРЕ", get_word_count(st.session_state.user_id))
            if st.button("ВЫЙТИ", use_container_width=True):
                for key in ['user_id', 'username', 'quiz_attempts', 'current_word_id', 'quiz_feedback', 'quiz_disabled']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()


def render_study_tab(words):
    st.subheader("ИЗУЧЕНИЕ СЛОВ")
    if not words:
        st.warning("Словарь пуст. Добавьте слова во вкладке 'Добавить слово'")
        return
    if 'current_word_id' not in st.session_state:
        random.shuffle(words)
        st.session_state.current_word_id = 0
        st.session_state.quiz_feedback = None
        st.session_state.quiz_disabled = False
        if 'quiz_attempts' not in st.session_state:
            st.session_state.quiz_attempts = {}
    if st.session_state.current_word_id >= len(words):
        st.session_state.current_word_id = 0
    current_word = words[st.session_state.current_word_id]
    word_key = f"{current_word['id']}_{current_word['word_type']}"
    options = generate_options(current_word, words)
    if options is None:
        st.markdown('<div class="warning">НЕДОСТАТОЧНО СЛОВ В СЛОВАРЕ ДЛЯ ГЕНЕРАЦИИ ВАРИАНТОВ. ДОБАВЬТЕ ЕЩЁ СЛОВ!</div>', unsafe_allow_html=True)
        return
    st.markdown(f"### Переведите слово на английский:")
    st.markdown(f"## {current_word['russian_word']}")
    attempts = st.session_state.quiz_attempts.get(word_key, 0)
    if attempts > 0:
        st.caption(f"ПОПЫТОК: {attempts}. ПОПРОБУЙТЕ ЕЩЁ РАЗ!")
    cols = st.columns(2)
    for i, opt in enumerate(options):
        disabled = st.session_state.quiz_disabled
        if cols[i % 2].button(opt, key=f"quiz_{i}", use_container_width=True, disabled=disabled):
            if opt == current_word['english_word']:
                update_stats(st.session_state.user_id, current_word['id'], current_word['word_type'], True)
                st.session_state.quiz_feedback = "correct"
                st.session_state.quiz_disabled = True
                st.session_state.quiz_attempts[word_key] = 0
                st.balloons()
            else:
                update_stats(st.session_state.user_id, current_word['id'], current_word['word_type'], False)
                st.session_state.quiz_attempts[word_key] = attempts + 1
                st.session_state.quiz_feedback = "incorrect"
                st.rerun()
    if st.session_state.quiz_feedback == "correct":
        st.markdown('<div class="correct">ПРАВИЛЬНО! ОТЛИЧНАЯ РАБОТА!</div>', unsafe_allow_html=True)
        if st.button("СЛЕДУЮЩЕЕ СЛОВО", use_container_width=True):
            st.session_state.current_word_id = (st.session_state.current_word_id + 1) % len(words)
            st.session_state.quiz_feedback = None
            st.session_state.quiz_disabled = False
            st.rerun()
    elif st.session_state.quiz_feedback == "incorrect":
        st.markdown('<div class="incorrect">НЕПРАВИЛЬНО! ПОПРОБУЙТЕ ЕЩЁ РАЗ.</div>', unsafe_allow_html=True)
        if st.button("ПОПРОБОВАТЬ СНОВА", use_container_width=True):
            st.session_state.quiz_feedback = None
            st.rerun()


def render_add_word_tab():
    st.subheader("ДОБАВИТЬ СЛОВО")
    with st.form("add_word_form"):
        russian_word = st.text_input("Слово на русском:")
        english_word = st.text_input("Перевод на английский:")
        submitted = st.form_submit_button("ДОБАВИТЬ", use_container_width=True)
        if submitted:
            if russian_word and english_word:
                if add_personal_word(st.session_state.user_id, russian_word.lower().strip(), english_word.lower().strip()):
                    st.success(f"СЛОВО '{russian_word} -> {english_word}' ДОБАВЛЕНО!")
                    st.rerun()
                else:
                    st.warning("Такое слово уже есть в вашем словаре")
            else:
                st.warning("Заполните оба поля")


def render_delete_word_tab(words):
    st.subheader("УДАЛИТЬ СЛОВО")
    personal_words = [w for w in words if w['word_type'] == 'personal']
    if not personal_words:
        st.info("У вас нет персональных слов для удаления")
        return
    word_options = {f"{w['russian_word']} -> {w['english_word']}": w['id'] for w in personal_words}
    selected_word = st.selectbox("Выберите слово для удаления:", list(word_options.keys()))
    if st.button("УДАЛИТЬ", use_container_width=True):
        if delete_personal_word(st.session_state.user_id, word_options[selected_word]):
            st.success("СЛОВО УДАЛЕНО!")
            st.rerun()
        else:
            st.error("Ошибка удаления")


def render_statistics_tab():
    st.subheader("СТАТИСТИКА ИЗУЧЕНИЯ")
    stats = get_statistics(st.session_state.user_id)
    if not stats or stats['total_attempts'] == 0:
        st.info("Пока нет данных. Пройдите викторину, чтобы увидеть статистику")
        return
    col1, col2, col3 = st.columns(3)
    col1.metric("ИЗУЧЕНО СЛОВ", stats['total_words'])
    col2.metric("ТОЧНОСТЬ", f"{stats['accuracy']}%")
    col3.metric("ВСЕГО ПОПЫТОК", stats['total_attempts'])
    st.divider()
    st.subheader("ПОСЛЕДНИЕ ПОПЫТКИ")
    for attempt in stats['recent']:
        word_type = "ОБЩЕЕ" if attempt[0] == 'common' else "ЛИЧНОЕ"
        accuracy = (attempt[1] / attempt[2] * 100) if attempt[2] > 0 else 0
        st.text(f"{word_type} | Правильно: {attempt[1]}/{attempt[2]} ({accuracy:.0f}%) | {attempt[3]}")


def render_schema():
    st.subheader("СХЕМА БАЗЫ ДАННЫХ")
    st.code("""
    users (id, username, created_at)
    common_words (id, russian_word, english_word)
    user_words (id, user_id, russian_word, english_word)
    learning_stats (id, user_id, word_id, word_type, correct_answers, total_attempts, last_reviewed)
    """, language='text')


def main():
    st.title("EnglishCard - Изучай английский с удовольствием!")
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    init_database()
    render_sidebar()
    if st.session_state.user_id:
        words = get_user_words(st.session_state.user_id)
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["ИЗУЧЕНИЕ", "ДОБАВИТЬ", "УДАЛИТЬ", "СТАТИСТИКА", "СХЕМА БД"])
        with tab1:
            render_study_tab(words)
        with tab2:
            render_add_word_tab()
        with tab3:
            render_delete_word_tab(words)
        with tab4:
            render_statistics_tab()
        with tab5:
            render_schema()
    else:
        st.info("Введите ваше имя в боковой панели, чтобы начать изучение")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**ИЗУЧЕНИЕ**\n- Слова с переводом\n- 4 варианта ответа\n- При ошибке - новая попытка")
        with col2:
            st.markdown("**ДОБАВЛЕНИЕ**\n- Личные слова\n- Свой словарь\n- Удобное управление")
        with col3:
            st.markdown("**СТАТИСТИКА**\n- Прогресс изучения\n- Точность ответов\n- История попыток")


if __name__ == "__main__":
    main()