from django.contrib import admin
from .models import Post
from .models import Post, ContactMessage, Announcement
# admin kaka13111
@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'created', 'slug')
    prepopulated_fields = {'slug': ('title',)}
    show_facets = admin.ShowFacets.ALWAYS
    

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'timestamp', 'is_read')
    list_filter = ('is_read', 'timestamp')
    search_fields = ('name', 'email', 'message')
    # Các trường này chỉ để đọc, không cho admin sửa đổi nội dung người dùng gửi
    readonly_fields = ('name', 'email', 'message', 'timestamp')

@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('content', 'level', 'is_active', 'created_at', 'link')
    list_filter = ('is_active', 'level', 'created_at')
    search_fields = ('content',)
    actions = ['activate_announcements', 'deactivate_announcements']

    def activate_announcements(self, request, queryset):
        queryset.update(is_active=True)
    activate_announcements.short_description = "Mark selected announcements as active"

    def deactivate_announcements(self, request, queryset):
        queryset.update(is_active=False)
    deactivate_announcements.short_description = "Mark selected announcements as inactive"
