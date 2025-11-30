from django import template
from django.utils.html import strip_tags
import math

register = template.Library()

@register.filter(name='calculate_reading_time')
def calculate_reading_time(html_content):
    """
    Ước tính thời gian đọc (phút) từ nội dung HTML.
    Tốc độ đọc trung bình: 200 từ/phút.
    """
    try:
        # Loại bỏ các thẻ HTML và đếm số từ
        text_content = strip_tags(html_content)
        word_count = len(text_content.split())
        
        minutes = math.ceil(word_count / 200)
        return int(minutes) if minutes > 0 else 1 # Trả về ít nhất 1 phút
    except (ValueError, TypeError):
        return 1 # Trả về 1 nếu có lỗi