from .models import Notification, Announcement

def notifications(request):
    if request.user.is_authenticated:
        unread_count = Notification.objects.filter(recipient=request.user, read=False).count()
        return {'unread_notifications_count': unread_count}
    return {}

def active_announcement(request):
    announcement = Announcement.objects.filter(is_active=True).first()
    if announcement:
        # Sử dụng session để kiểm tra xem người dùng đã đóng thông báo này chưa
        dismissed_key = f'dismissed_announcement_{announcement.id}'
        if not request.session.get(dismissed_key, False):
            return {'active_announcement': announcement}
    return {}