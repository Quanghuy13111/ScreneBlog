from django.shortcuts import render, get_object_or_404, redirect
from .models import Post, Notification, ContactMessage, Profile, Comment
from django.urls import reverse
from taggit.models import Tag
from django.http import HttpResponseForbidden, JsonResponse
from .forms import CommentForm, PostForm, ContactForm, UserUpdateForm, ProfileUpdateForm
from django.core.mail import send_mail
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.utils.text import slugify
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.db.models import F, Q
from django.utils import timezone
from datetime import timedelta
from django.contrib.admin.views.decorators import staff_member_required
from .forms import SignupForm

def index(request):
    all_posts = Post.objects.select_related('author').filter(created__lte=timezone.now()).order_by('-created')
    
    # Logic mới: Bài viết nổi bật là bài có nhiều likes nhất trong 7 ngày qua
    one_week_ago = timezone.now() - timedelta(days=7)
    featured_post = Post.objects.filter(created__gte=one_week_ago).order_by('-likes', '-created').first()

    # Nếu không có bài nào trong 7 ngày qua, lấy bài mới nhất làm bài nổi bật
    if not featured_post:
        featured_post = all_posts.first()

    # Loại bài viết nổi bật khỏi danh sách bài viết thường
    other_posts_list = all_posts.exclude(pk=featured_post.pk) if featured_post else all_posts

    paginator = Paginator(other_posts_list, 4) # 4 bài viết thường mỗi trang

    page_number = request.GET.get('page')
    posts = paginator.get_page(page_number)

    context = {
        'featured_post': featured_post,
        'posts': posts
    }

    return render(request, 'blog/index.html', context)

def about(request):
    return render(request, 'blog/about.html')

def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            email = form.cleaned_data['email']
            message = form.cleaned_data['message']
            
            # Lưu tin nhắn vào cơ sở dữ liệu
            ContactMessage.objects.create(name=name, email=email, message=message)

            # Kiểm tra xem đây có phải là yêu cầu AJAX không
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'success', 'message': 'Your message has been sent successfully! We will get back to you soon.'})
            else:
                # Fallback cho trường hợp không có JavaScript
                messages.success(request, 'Your message has been sent successfully! We will get back to you soon.')
                return redirect('blog:contact')
        elif request.headers.get('x-requested-with') == 'XMLHttpRequest':
            # Nếu form không hợp lệ và là AJAX, trả về lỗi dạng JSON
            return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
    else:
        form = ContactForm()

    return render(request, 'blog/contact.html', {'form': form})


def post_detail(request, slug):
    post = get_object_or_404(Post, slug=slug)
    
    # Tăng lượt xem mỗi khi có người truy cập
    post.viewer = F('viewer') + 1
    post.save(update_fields=['viewer'])
    post.refresh_from_db() # Lấy lại dữ liệu mới từ DB

    # --- Logic tìm bài viết liên quan ---
    post_tags_ids = post.tags.values_list('id', flat=True)
    related_posts = Post.objects.filter(tags__in=post_tags_ids)\
                                .exclude(id=post.id)
    # Đếm số lượng tag chung và sắp xếp
    from django.db.models import Count
    related_posts = related_posts.annotate(same_tags=Count('tags'))\
                                 .order_by('-same_tags', '-created')[:4] # Lấy 4 bài liên quan nhất

    # --- Logic phân trang và tìm bình luận ---
    # Tối ưu hóa: Lấy sẵn author và profile của author để tránh N+1 query
    top_level_comments = post.comments.filter(active=True, parent__isnull=True)\
                                      .select_related('author__profile').order_by('created')
    comments_per_page = 10 # Số bình luận mỗi trang

    # Kiểm tra xem có hash comment trong URL không
    comment_id_str = request.GET.get('comment_id')
    page_number = request.GET.get('page')

    if comment_id_str:
        try:
            target_comment_id = int(comment_id_str)
            target_comment = get_object_or_404(Comment, id=target_comment_id)

            # Tìm comment gốc (top-level) của comment mục tiêu
            root_comment = target_comment
            while root_comment.parent:
                root_comment = root_comment.parent

            # Tìm vị trí của comment gốc trong danh sách và tính trang
            comment_ids = list(top_level_comments.values_list('id', flat=True))
            if root_comment.id in comment_ids:
                comment_index = comment_ids.index(root_comment.id)
                page_number = (comment_index // comments_per_page) + 1
        except (ValueError, Comment.DoesNotExist):
            pass # Bỏ qua nếu comment_id không hợp lệ

    paginator = Paginator(top_level_comments, comments_per_page)
    comments = paginator.get_page(page_number)
    new_comment = None

    if request.method == 'POST':
        # Xử lý bình luận AJAX
        # Đầu tiên, kiểm tra xem người dùng đã đăng nhập chưa
        if not request.user.is_authenticated:
            return JsonResponse({'status': 'error', 'message': 'Authentication required.'}, status=403)

        comment_form = CommentForm(data=request.POST)
        if comment_form.is_valid():
            # Tạo đối tượng Comment nhưng chưa lưu vào DB
            new_comment = comment_form.save(commit=False)
            # Gán bài viết hiện tại cho bình luận
            new_comment.post = post
            new_comment.author = request.user
            
            # Xử lý bình luận trả lời
            parent_id = request.POST.get('parent_id')
            if parent_id:
                parent_comment = get_object_or_404(post.comments.model, id=parent_id)
                new_comment.parent = parent_comment

                # Tạo thông báo cho người chủ của bình luận cha
                # Đảm bảo không tự thông báo cho chính mình
                if parent_comment.author != request.user:
                    verb = f'replied to your comment on "{post.title}"'
                    Notification.objects.create(recipient=parent_comment.author, sender=request.user, comment=new_comment, verb=verb)

            # Lưu bình luận vào DB
            new_comment.save()
            # Trả về JSON cho AJAX
            return JsonResponse({
                'status': 'success',
                'comment_id': new_comment.id,
                'author': new_comment.author.username,
                'body': new_comment.body,
                'parent_id': parent_id,
                'created': new_comment.created.strftime('%b. %d, %Y, %I:%M %p')
            })
        else:
            return JsonResponse({'status': 'error', 'errors': comment_form.errors}, status=400)
    else:
        comment_form = CommentForm()

    # Kiểm tra xem người dùng hiện tại đã like bài viết này chưa
    user_has_liked = False
    if request.user.is_authenticated:
        user_has_liked = post.liked_by.filter(id=request.user.id).exists()

    # Lấy danh sách ID các bình luận mà người dùng hiện tại đã like
    user_liked_comment_ids = []
    if request.user.is_authenticated:
        user_liked_comment_ids = list(request.user.liked_comments.values_list('id', flat=True))

    return render(request, 'blog/post_detail.html', {'post': post,
                                                     'comments': comments,
                                                     'new_comment': new_comment,
                                                     'related_posts': related_posts,
                                                     'comment_form': comment_form,
                                                     'user_has_liked': user_has_liked,
                                                     'user_liked_comment_ids': user_liked_comment_ids})

@login_required
def post_create(request):
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.slug = slugify(post.title)
            post.author = request.user # Gán tác giả là người dùng đang đăng nhập
            post.save()
            # Lưu các tags sau khi post đã được lưu
            form.save_m2m()
            return redirect('blog:post_detail', slug=post.slug)
    else:
        form = PostForm()
    return render(request, 'blog/post_form.html', {'form': form, 'title': 'Create Post'})

@login_required
def post_edit(request, slug):
    post = get_object_or_404(Post, slug=slug)
    # Chỉ tác giả của bài viết mới có quyền chỉnh sửa
    if post.author != request.user:
        return HttpResponseForbidden("You are not allowed to edit this post.")

    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            post = form.save(commit=False)
            post.slug = slugify(post.title)
            post.save() # Lưu đối tượng post trước
            # Sau đó lưu các quan hệ many-to-many (tags)
            form.save_m2m()
            return redirect('blog:post_detail', slug=post.slug)
    else:
        form = PostForm(instance=post)
    return render(request, 'blog/post_form.html', {'form': form, 'title': 'Edit Post'})

@login_required
def post_delete(request, slug):
    post = get_object_or_404(Post, slug=slug)
    # Chỉ tác giả của bài viết mới có quyền xóa
    if post.author != request.user:
        return HttpResponseForbidden("You are not allowed to delete this post.")

    post.delete()
    return redirect('blog:home')

def signup(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            form.save()
            # Thay vì đăng nhập và chuyển hướng ở server,
            # trả về JSON để client-side JavaScript xử lý.
            # Điều này phù hợp hơn với các form được submit bằng AJAX/Fetch.
            return JsonResponse({'status': 'success', 'redirect_url': reverse('login')})
        else:
            # Nếu form không hợp lệ, trả về lỗi dưới dạng JSON
            return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
    else:
        form = SignupForm()

    return render(request, 'registration/signup.html', {'form': form})

from django.contrib.auth import logout

def logout_view(request):
    logout(request)
    return redirect('blog:home')

@login_required
def user_profile(request):
    # Lấy hoặc tạo profile cho người dùng hiện tại.
    from django.db.models import Sum
    # Điều này sẽ khắc phục lỗi "User has no profile" cho các tài khoản cũ.
    profile, created = Profile.objects.get_or_create(user=request.user)

    # Khởi tạo các form
    password_form = PasswordChangeForm(request.user)
    u_form = UserUpdateForm(instance=request.user)
    p_form = ProfileUpdateForm(instance=profile)

    if request.method == 'POST':
        # Xác định form nào được gửi đi
        if 'change_password' in request.POST:
            password_form = PasswordChangeForm(request.user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)  # Giữ người dùng đăng nhập
                messages.success(request, 'Your password was successfully updated!')
                return redirect('blog:user_profile')
            else:
                messages.error(request, 'Please correct the password errors below.')

        elif 'update_profile' in request.POST:
            u_form = UserUpdateForm(request.POST, instance=request.user)
            p_form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
            if u_form.is_valid() and p_form.is_valid():
                u_form.save()
                p_form.save()
                messages.success(request, 'Your profile has been updated successfully!')
                return redirect('blog:user_profile')
            else:
                messages.error(request, 'Please correct the profile errors below.')
    else:
        # Khởi tạo form với dữ liệu hiện tại cho GET request
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)

    # Lấy danh sách bài viết và tính toán các thống kê
    user_posts = Post.objects.filter(author=request.user).order_by('-created')
    total_posts = user_posts.count()
    total_likes_received = user_posts.aggregate(total_likes=Sum('likes'))['total_likes'] or 0
    # Lưu ý: Giả định 'author' trong model Comment là CharField lưu username.
    total_comments_made = Comment.objects.filter(author=request.user).count()
    
    context = {
        'u_form': u_form,
        'p_form': p_form,
        'user_posts': user_posts,
        'password_form': password_form,
        'total_posts': total_posts,
        'total_likes_received': total_likes_received,
        'total_comments_made': total_comments_made,
    }
    return render(request, 'blog/user_profile.html', context)

def search_view(request):
    query = request.GET.get('q', '')
    results = Post.objects.none() # Mặc định là không có kết quả

    if query:
        # Tìm kiếm không phân biệt chữ hoa/thường trong cả tiêu đề và nội dung
        results = Post.objects.filter(
            Q(title__icontains=query) | Q(content__icontains=query)
        ).select_related('author').order_by('-created').distinct()

    return render(request, 'blog/search_results.html', {
        'query': query,
        'results': results
    })

def tagged_posts(request, tag_slug):
    tag = get_object_or_404(Tag, slug=tag_slug)
    posts = Post.objects.filter(tags__in=[tag]).select_related('author').order_by('-created')
    
    context = {
        'tag': tag,
        'posts': posts
    }
    return render(request, 'blog/tagged_posts.html', context)

def like_post(request, slug):
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'login_required'}, status=401)
        
    post = get_object_or_404(Post, slug=slug)
    user = request.user

    if user in post.liked_by.all():
        # Người dùng đã like, giờ unlike
        post.liked_by.remove(user)
        post.likes = F('likes') - 1
        liked = False
    else:
        # Người dùng chưa like, giờ like
        post.liked_by.add(user)
        post.likes = F('likes') + 1
        liked = True
        
        # Tạo thông báo cho tác giả bài viết
        # Đảm bảo người dùng không tự "like" bài của chính mình và nhận thông báo
        if user != post.author:
            verb = f'liked your post: "{post.title}"'
            Notification.objects.create(recipient=post.author, sender=user, verb=verb, post=post)

    post.save()
    post.refresh_from_db()
    return JsonResponse({'likes': post.likes, 'liked': liked})

@login_required
def like_comment(request, comment_id):
    """
    Xử lý việc like/unlike một bình luận.
    """
    comment = get_object_or_404(Comment, id=comment_id)
    user = request.user

    if user in comment.liked_by.all():
        # Người dùng đã like, giờ unlike
        comment.liked_by.remove(user)
        comment.likes = F('likes') - 1
        liked = False
    else:
        # Người dùng chưa like, giờ like
        comment.liked_by.add(user)
        comment.likes = F('likes') + 1
        liked = True

    comment.save()
    comment.refresh_from_db()
    return JsonResponse({'status': 'success', 'likes': comment.likes, 'liked': liked})

def public_user_profile(request, username):
    user = get_object_or_404(User, username=username)
    # Tối ưu hóa: Lấy trước các tags liên quan để tránh N+1 query
    user_posts = Post.objects.filter(author=user)\
                             .prefetch_related('tags')\
                             .order_by('-created')

    context = {
        'profile_user': user, 
        'user_posts': user_posts
    }
    return render(request, 'blog/public_user_profile.html', context)

@login_required
def delete_comment(request, comment_id):
    # Lấy đối tượng comment hoặc trả về lỗi 404 nếu không tìm thấy
    comment = get_object_or_404(Comment, id=comment_id)

    # Kiểm tra quyền: người dùng phải là tác giả bình luận HOẶC tác giả bài viết
    if request.user != comment.author and request.user != comment.post.author:
        return JsonResponse({'status': 'error', 'message': 'You do not have permission to delete this comment.'}, status=403)

    if request.method == 'POST':
        comment.delete()
        return JsonResponse({'status': 'success'})
    
    # Trả về lỗi nếu không phải là phương thức POST
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)


@login_required
def notification_list(request):
    notifications = Notification.objects.filter(recipient=request.user).select_related('sender', 'comment__post')
    # Đánh dấu tất cả là đã đọc khi người dùng truy cập trang
    notifications.update(read=True)
    return render(request, 'blog/notifications.html', {'notifications': notifications})

# --- Views for Admin Message Management ---

@staff_member_required
def contact_message_list(request):
    """
    Hiển thị danh sách tất cả các tin nhắn liên hệ cho quản trị viên.
    """
    messages_list = ContactMessage.objects.all().order_by('-timestamp')
    return render(request, 'blog/admin_message_list.html', {'messages': messages_list})

@staff_member_required
def toggle_message_read(request, message_id):
    """
    Chuyển đổi trạng thái đã đọc/chưa đọc của một tin nhắn.
    """
    message = get_object_or_404(ContactMessage, id=message_id)
    message.is_read = not message.is_read
    message.save()
    return redirect('blog:contact_messages')

@staff_member_required
def delete_contact_message(request, message_id):
    """
    Xóa một tin nhắn liên hệ.
    """
    message = get_object_or_404(ContactMessage, id=message_id)
    if request.method == 'POST':
        message.delete()
        return redirect('blog:contact_messages')
    # Nếu không phải POST, có thể hiển thị trang xác nhận xóa (tùy chọn)
    return redirect('blog:contact_messages')

def live_search(request):
    """
    Xử lý yêu cầu tìm kiếm AJAX và trả về kết quả dưới dạng JSON.
    """
    query = request.GET.get('q', '')
    results = []
    if query and len(query) > 2: # Chỉ tìm kiếm khi query có hơn 2 ký tự
        posts = Post.objects.filter(
            Q(title__icontains=query) | Q(content__icontains=query)
        ).select_related('author').order_by('-created').distinct()[:5] # Giới hạn 5 kết quả

        for post in posts:
            results.append({
                'title': post.title,
                'url': post.get_absolute_url(),
            })
    return JsonResponse({'results': results})
