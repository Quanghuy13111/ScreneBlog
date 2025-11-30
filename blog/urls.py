from django.urls import path
from . import views

app_name = 'blog'

urlpatterns = [
    path('', views.index, name='home'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('post/new/', views.post_create, name='post_create'),
    path('post/<slug:slug>/', views.post_detail, name='post_detail'),
    path('post/<slug:slug>/edit/', views.post_edit, name='post_edit'),
    path('post/<slug:slug>/delete/', views.post_delete, name='post_delete'),
    path('profile/', views.user_profile, name='user_profile'),
    path('user/<str:username>/', views.public_user_profile, name='public_user_profile'), # Đảm bảo dòng này tồn tại
    path('search/', views.search_view, name='search'),
    path('live-search/', views.live_search, name='live_search'), # Thêm URL cho tìm kiếm trực tiếp
    path('tag/<slug:tag_slug>/', views.tagged_posts, name='tagged_posts'),
    path('like/<slug:slug>/', views.like_post, name='like_post'),
    path('post/<int:post_id>/like/', views.like_post, name='like_post'),
    path('notifications/', views.notification_list, name='notification_list'),
    path('comment/<int:comment_id>/like/', views.like_comment, name='like_comment'),
    path('comment/<int:comment_id>/delete/', views.delete_comment, name='delete_comment'),

    # --- Password Reset URLs ---
    path('password_reset/', auth_views.PasswordResetView.as_view(
        template_name='registration/password_reset_form.html',
        email_template_name='registration/password_reset_email.html',
        subject_template_name='registration/password_reset_subject.txt',
        success_url=reverse_lazy('blog:password_reset_done')
    ), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='registration/password_reset_done.html'
    ), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='registration/password_reset_confirm.html',
        success_url=reverse_lazy('blog:password_reset_complete')
    ), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='registration/password_reset_complete.html'
    ), name='password_reset_complete'),

    # Admin-only URLs for message management
    path('admin/messages/', views.contact_message_list, name='contact_messages'),
    path('admin/messages/<int:message_id>/toggle-read/', views.toggle_message_read, name='toggle_message_read'),
    path('admin/messages/<int:message_id>/delete/', views.delete_contact_message, name='delete_contact_message'),
]
