from .models import Notification, Announcement

def notifications(request):
    if request.user.is_authenticated:
        unread_count = Notification.objects.filter(recipient=request.user, read=False).count()
        return {'unread_notifications_count': unread_count}
    return {}

def active_announcement(request):
    """
    Cung cấp thông báo đang hoạt động mới nhất cho tất cả các template.
    """
    announcement = Announcement.objects.filter(is_active=True).order_by('-created_at').first()
    return {'active_announcement': announcement}