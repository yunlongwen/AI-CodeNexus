import json
from datetime import datetime, timedelta

# 读取JSON文件
with open('data/articles/ai_news.json', 'r', encoding='utf-8') as f:
    ai_news = json.load(f)

with open('data/articles/programming.json', 'r', encoding='utf-8') as f:
    programming = json.load(f)

all_articles = ai_news + programming

# 按archived_at排序
archived_articles = [a for a in all_articles if a.get('archived_at')]
archived_articles.sort(key=lambda x: x.get('archived_at', ''), reverse=True)

print('最近10篇归档文章:')
for i, article in enumerate(archived_articles[:10]):
    archived_at = article.get('archived_at', '无')
    title = article.get('title', '无标题')[:60]
    category = article.get('category', '未知')
    print('{}. {} - {} - {}'.format(i+1, archived_at, category, title))

print('\n最近7天的归档情况:')
today = datetime.now()
for i in range(7):
    check_date = today - timedelta(days=i)
    date_str = check_date.strftime('%Y-%m-%d')

    day_articles = [a for a in archived_articles if a.get('archived_at', '').startswith(date_str)]
    print('{}: {} 篇文章'.format(date_str, len(day_articles)))
