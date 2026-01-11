from .models import Notification, Announcement

def notifications(request):
    if request.user.is_authenticated:
        # Lấy tất cả thông báo của người dùng, sắp xếp từ mới nhất đến cũ nhất
        all_notifications = Notification.objects.filter(recipient=request.user)\
                                                .select_related('sender', 'post', 'comment__post')\
                                                .order_by('-timestamp')
        # Đếm số thông báo chưa đọc
        unread_count = all_notifications.filter(read=False).count()
        # Lấy 5 thông báo gần nhất để hiển thị trong dropdown
        latest_notifications_list = all_notifications[:5]
        return {
            'unread_notifications_count': unread_count,
            'latest_notifications': latest_notifications_list,
        }
    return {}

def active_announcement(request):
    announcement = Announcement.objects.filter(is_active=True).first()
    if announcement:
        # Sử dụng session để kiểm tra xem người dùng đã đóng thông báo này chưa
        dismissed_key = f'dismissed_announcement_{announcement.id}'
        if not request.session.get(dismissed_key, False):
            return {'active_announcement': announcement}
    return {}