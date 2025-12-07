import math
from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()

@register.filter(name='reading_time')
@stringfilter
def reading_time(value):
    """
    Ước tính thời gian đọc cho một đoạn văn bản.
    Giả định tốc độ đọc trung bình là 180 từ mỗi phút.
    """
    if not value:
        return 1

    word_count = len(value.split())
    words_per_minute = 180 # Giảm tốc độ đọc để ước tính sát hơn
    minutes = word_count / words_per_minute
    read_time = math.ceil(minutes) # Làm tròn lên số nguyên gần nhất

    return read_time if read_time > 0 else 1