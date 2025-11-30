from django.db import models
from imagekit.models import ImageSpecField
from django.urls import reverse
from django.conf import settings
from taggit.managers import TaggableManager
from imagekit.processors import ResizeToFill, Transpose, SmartResize
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

'''
File model.py
1. Được tự động tạo ra khi chạy câu lệnh startapp
2. Quản lý, định nghĩa các dữ liệu trong hệ thống
3. Được chia thành các class - một đối tượng
4. Trong các class cần định nghĩa các thuộc tính của đối tượng đó
5. Khi thực hiện sửa models => chạy lại migrations

'''
# Create your models here.
class Post(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='blog_posts')
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=250)
    attachment = models.FileField(upload_to='attachments/%Y/%m/%d/', blank=True, null=True, verbose_name="Attachment/Image")
    content = models.TextField()
    thumbnail = ImageSpecField(source='attachment',
                               processors=[ResizeToFill(400, 250)],
                               format='JPEG',
                               options={'quality': 80})

    created = models.DateTimeField(auto_now_add=True)
    viewer = models.IntegerField(default=0)
    likes = models.PositiveIntegerField(default=0, verbose_name="Likes")
    liked_by = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='liked_posts', blank=True)
    tags = TaggableManager()
    
    def __str__(self):
        return self.title # nhìn đc rõ hon
    
    def get_absolute_url(self):
        return reverse('blog:post_detail', args=[self.slug])

    def estimate_reading_time(self):
        word_count = len(self.content.split())
        reading_time = round(word_count / 200) # Giả sử tốc độ đọc trung bình là 200 từ/phút
        return max(1, reading_time) # Trả về ít nhất 1 phút
    
    @property
    def is_image(self):
        """Kiểm tra xem tệp đính kèm có phải là ảnh không."""
        if not self.attachment:
            return False
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']
        return any(self.attachment.name.lower().endswith(ext) for ext in image_extensions)

class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments_made')
    body = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies')
    likes = models.PositiveIntegerField(default=0)
    liked_by = models.ManyToManyField(User, related_name='liked_comments', blank=True)


    class Meta:
        ordering = ('created',)

    def __str__(self):
        return f'Comment by {self.author.username} on {self.post}'

class Notification(models.Model):
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_notifications')
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name='+') # Bình luận trả lời
    verb = models.CharField(max_length=255)
    read = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-timestamp',)

    def __str__(self):
        return f'Notification for {self.recipient.username}: {self.verb}'

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(max_length=500, blank=True)
    avatar = models.ImageField(default='profile_pics/default.jpg', upload_to='profile_pics')
    avatar_thumbnail = ImageSpecField(source='avatar',
                                      processors=[ResizeToFill(150, 150)],
                                      format='JPEG',
                                      options={'quality': 90})

    def __str__(self):
        return f'{self.user.username} Profile'

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created and not hasattr(instance, 'profile'):
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()

class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False, verbose_name="Mark as Read")

    class Meta:
        ordering = ('-timestamp',)
        verbose_name = "Contact Message"
        verbose_name_plural = "Contact Messages"

    def __str__(self):
        return f'Message from {self.name} ({self.email})'

class Announcement(models.Model):
    """
    Model để lưu trữ các thông báo trên toàn trang web.
    Chỉ có thông báo mới nhất được đánh dấu 'is_active' mới được hiển thị.
    """
    LEVEL_CHOICES = [
        ('info', 'Info'),
        ('success', 'Success'),
        ('warning', 'Warning'),
        ('danger', 'Danger'),
    ]

    content = models.TextField(help_text="Nội dung của thông báo. Có thể sử dụng HTML.")
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, default='info', help_text="Kiểu thông báo (ảnh hưởng đến màu sắc).")
    link = models.URLField(blank=True, null=True, help_text="(Tùy chọn) Một liên kết mà người dùng có thể nhấp vào.")
    is_active = models.BooleanField(default=True, help_text="Chỉ những thông báo được kích hoạt mới được hiển thị.")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Announcement from {self.created_at.strftime('%Y-%m-%d')}"

    class Meta:
        ordering = ['-created_at']