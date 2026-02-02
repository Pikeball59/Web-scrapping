import requests
from bs4 import BeautifulSoup
import re
import time
from urllib.parse import urljoin
from datetime import datetime
import os

# ЛОГГЕР
def logger(path):
    def __logger(old_function):
        def new_function(*args, **kwargs):
            result = old_function(*args, **kwargs)

            # Формат аргументов для читаемости
            args_str = ', '.join([str(arg)[:100] + '...' if len(str(arg)) > 100 else str(arg) for arg in args])
            kwargs_str = ', '.join([f'{k}={v}' for k, v in kwargs.items()])

            # Формат результатов для читаемости
            if isinstance(result, (list, dict)) and len(str(result)) > 100:
                result_str = f"{type(result).__name__} с {len(result)} элементами"
            else:
                result_str = str(result)[:200] + '...' if len(str(result)) > 200 else str(result)

            with open(path, 'a', encoding='utf-8') as f:
                f.write(f"\n{'=' * 80}\n")
                f.write(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"🔧 Функция: {old_function.__name__}\n")
                if args_str:
                    f.write(f"📋 Аргументы: {args_str}\n")
                if kwargs_str:
                    f.write(f"⚙️  Параметры: {kwargs_str}\n")
                f.write(f"✅ Результат: {result_str}\n")
                f.write(f"{'=' * 80}\n")

            return result

        return new_function

    return __logger

# хедерсы
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

KEYWORDS = ['дизайн', 'фото', 'web', 'python']
LOG_FILE = 'habr_parser.log'


@logger(LOG_FILE)
def get_articles_from_main_page():
    """Получаю список статей с главной страницы"""
    url = 'https://habr.com/ru/articles/'

    print("🔄 Получаю список свежих статей...")
    response = requests.get(url, headers=HEADERS, timeout=10)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'lxml')
    articles = soup.find_all('article', class_='tm-articles-list__item')

    print(f"📊 Найдено {len(articles)} статей для анализа")
    return articles


@logger(LOG_FILE)
def parse_article_preview(article):
    """Парсим превью информации из статьи"""
    # Заголовок и ссылка
    title_elem = article.find('h2', class_='tm-title')
    if not title_elem:
        return None

    link_elem = title_elem.find('a', class_='tm-title__link')
    if not link_elem:
        return None

    title = link_elem.text.strip()
    relative_link = link_elem.get('href')
    article_url = urljoin('https://habr.com', relative_link)

    # Дата
    time_elem = article.find('time')
    if time_elem:
        datetime_str = time_elem.get('datetime', '')
        date_only = datetime_str.split('T')[0] if datetime_str else 'Неизвестная дата'
    else:
        date_only = 'Неизвестная дата'

    # Preview-информация
    preview_text = ''
    preview_elem = article.find('div', class_='article-formatted-body')
    if preview_elem:
        preview_text = ' '.join(preview_elem.stripped_strings).lower()

    return {
        'title': title,
        'url': article_url,
        'date': date_only,
        'preview_text': preview_text
    }

@logger(LOG_FILE)
def get_article_full_text(article_url):
    """Получаю полный текст статьи по URL"""
    try:
        response = requests.get(article_url, headers=HEADERS, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'lxml')

        # Ищем основной текст статьи
        article_body = soup.find('div', class_='tm-article-body')
        if article_body:
            full_text = ' '.join(article_body.stripped_strings).lower()
            return full_text
        else:
            # Альтернативный поиск текста
            article_content = soup.find('article')
            if article_content:
                full_text = ' '.join(article_content.stripped_strings).lower()
                return full_text

        return ""

    except Exception as e:
        print(f"Ошибка при получении статьи {article_url}: {e}")
        return ""

@logger(LOG_FILE)
def analyze_article_text(text, keywords):
    """Анализирую текст на наличие ключевых слов"""
    if not text:
        return False

    for keyword in keywords:
        if re.search(r'\b' + re.escape(keyword.lower()) + r'\b', text):
            return True
    return False

@logger(LOG_FILE)
def print_results(results):
    """Вывожу результаты поиска"""
    print("\n" + "=" * 100)
    print("🎯 РЕЗУЛЬТАТЫ ПОИСКА С АНАЛИЗОМ ПОЛНОГО ТЕКСТА СТАТЕЙ")
    print("=" * 100)

    if results:
        preview_count = len([r for r in results if r['found_in'] == 'preview'])
        full_text_count = len([r for r in results if r['found_in'] == 'full_text'])

        print(f"📊 Найдено статей: {len(results)}")
        print(f"   • В preview: {preview_count}")
        print(f"   • В полном тексте: {full_text_count}")
        print("-" * 100)

        for article in results:
            source = "(preview)" if article['found_in'] == 'preview' else "(полный текст)"
            print(f"{article['date']} – {article['title']} {source} – {article['link']}")

        # Возвращаем понятный результат для лога
        return f"Найдено {len(results)} статей ({preview_count} в preview, {full_text_count} в полном тексте)"
    else:
        print("❌ Статьи с указанными ключевыми словами не найдены.")
        return "Статьи не найдены"


@logger(LOG_FILE)
def main():
    """Основная функция парсера"""
    try:
        # Очищает лог файл при каждом запуске
        if os.path.exists(LOG_FILE):
            os.remove(LOG_FILE)

        articles = get_articles_from_main_page()
        results = []
        processed_count = 0

        for article in articles:
            try:
                article_data = parse_article_preview(article)
                if not article_data:
                    continue

                # Проверяет preview
                preview_search_text = (article_data['title'] + ' ' + article_data['preview_text']).lower()
                preview_match = analyze_article_text(preview_search_text, KEYWORDS)

                if not preview_match:
                    print(f"🔍 Анализирую полный текст: {article_data['title']}")
                    full_text = get_article_full_text(article_data['url'])

                    if full_text:
                        full_text_match = analyze_article_text(full_text, KEYWORDS)
                        if full_text_match:
                            results.append({
                                'date': article_data['date'],
                                'title': article_data['title'],
                                'link': article_data['url'],
                                'found_in': 'full_text'
                            })
                    else:
                        print(f"❌ Не удалось получить текст статьи: {article_data['title']}")

                    time.sleep(1)
                else:
                    # Статья найдена по preview
                    results.append({
                        'date': article_data['date'],
                        'title': article_data['title'],
                        'link': article_data['url'],
                        'found_in': 'preview'
                    })

                processed_count += 1
                print(f"✅ Обработано: {processed_count}/{len(articles)} статей")

            except Exception as e:
                print(f"❌ Ошибка при обработке статьи: {e}")
                continue

        print_results(results)
        print(f"\n✅ Анализ завершен. Обработано статей: {processed_count}")
        return f"Парсинг завершен успешно. Обработано: {processed_count} статей"

    except Exception as e:
        error_msg = f"Критическая ошибка: {e}"
        print(f"❌ {error_msg}")
        return error_msg


if __name__ == "__main__":
    main()