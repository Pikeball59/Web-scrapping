import requests
from bs4 import BeautifulSoup
import re
import time
from urllib.parse import urljoin

# Определяем список ключевых слов:
KEYWORDS = ['дизайн', 'фото', 'web', 'python']


def get_article_full_text(article_url):
    """Получает полный текст статьи по URL"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    try:
        response = requests.get(article_url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'lxml')

        # Ищем основной текст статьи
        article_body = soup.find('div', class_='tm-article-body')
        if article_body:
            # Получаем весь текст статьи, убираем HTML теги
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


def main():
    # URL страницы со свежими статьями
    url = 'https://habr.com/ru/articles/'

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    try:
        print("🔄 Получаем список свежих статей...")
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'lxml')

        # Находим все статьи
        articles = soup.find_all('article', class_='tm-articles-list__item')

        results = []
        processed_count = 0

        print(f"📊 Найдено {len(articles)} статей для анализа")

        for article in articles:
            try:
                # Заголовок и ссылка
                title_elem = article.find('h2', class_='tm-title')
                if not title_elem:
                    continue

                link_elem = title_elem.find('a', class_='tm-title__link')
                if not link_elem:
                    continue

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

                # Сначала проверяем preview
                preview_search_text = (title + ' ' + preview_text).lower()
                preview_match = False

                for keyword in KEYWORDS:
                    if re.search(r'\b' + re.escape(keyword.lower()) + r'\b', preview_search_text):
                        preview_match = True
                        break

                # Если в preview нет ключевых слов, проверяем полный текст статьи
                if not preview_match:
                    print(f"🔍 Анализируем полный текст: {title}")
                    full_text = get_article_full_text(article_url)

                    if full_text:
                        full_text_match = False
                        for keyword in KEYWORDS:
                            if re.search(r'\b' + re.escape(keyword.lower()) + r'\b', full_text):
                                full_text_match = True
                                break

                        if full_text_match:
                            results.append({
                                'date': date_only,
                                'title': title,
                                'link': article_url,
                                'found_in': 'full_text'
                            })
                    else:
                        print(f"❌ Не удалось получить текст статьи: {title}")

                    # Задержка между запросами чтобы не нагружать сервер
                    time.sleep(1)
                else:
                    # Статья найдена по preview
                    results.append({
                        'date': date_only,
                        'title': title,
                        'link': article_url,
                        'found_in': 'preview'
                    })

                processed_count += 1
                print(f"✅ Обработано: {processed_count}/{len(articles)} статей")

            except Exception as e:
                print(f"❌ Ошибка при обработке статьи: {e}")
                continue

        # Вывод результатов
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
        else:
            print("❌ Статьи с указанными ключевыми словами не найдены.")

        print(f"\n✅ Анализ завершен. Обработано статей: {processed_count}")

    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")


if __name__ == "__main__":
    main()