import json
from datetime import datetime, timedelta

# 读取JSON文件
with open('data/articles/ai_news.json', 'r', encoding='utf-8') as f:
    ai_news = json.load(f)

with open('data/articles/programming.json', 'r', encoding='utf-8') as f:
    programming = json.load(f)

# 计算本周的开始时间
today = datetime.now()
days_since_monday = today.weekday()
week_start = today - timedelta(days=days_since_monday)
week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)

print('本周时间范围:', week_start, '到', week_end)

# 检查本周的文章
def is_this_week(archived_at):
    if not archived_at:
        return False
    try:
        if archived_at.endswith('Z'):
            archived_at = archived_at[:-1]
        article_time = datetime.fromisoformat(archived_at)
        if article_time.tzinfo:
            article_time = article_time.replace(tzinfo=None)
        return week_start <= article_time <= week_end
    except:
        return False

ai_this_week = [a for a in ai_news if is_this_week(a.get('archived_at'))]
prog_this_week = [p for p in programming if is_this_week(p.get('archived_at'))]

print('本周AI资讯:', len(ai_this_week), '篇')
print('本周编程资讯:', len(prog_this_week), '篇')
print('总计:', len(ai_this_week) + len(prog_this_week), '篇')

if ai_this_week:
    print('\n最近的AI资讯:')
    for article in ai_this_week[:3]:
        print('  {}... - {}'.format(article['title'][:50], article.get('archived_at')))