import mimetypes
import json
import secrets
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from datetime import date, datetime
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import F, Q
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .forms import ArtistOnboardingForm, AppointmentForm, ArtistPortfolioForm, AvailabilityWindowForm, ChatMessageForm, CommunityPostForm, OccupiedTimeForm, PostCommentForm, ProfileForm
from .models import Appointment, ArtistPortfolio, AvailabilityWindow, ChatMessage, ChatThread, MessageItem, OccupiedTime, PostComment, UserProfile

LEGACY_SITE_ROOT = Path(__file__).resolve().parents[2]
LOGIN_ROLE_SESSION_KEY = "glow_login_role"


def _thread_display_title(thread, viewer):
    other_user = thread.user_b if thread.user_a == viewer else thread.user_a
    base_name = other_user.profile.display_name or other_user.username
    if thread.kind == ChatThread.THREAD_BOOKING and thread.appointment_id:
        return thread.title or f"Appointment chat with {base_name}"
    return thread.title or f"Private chat with {base_name}"


def _get_or_create_thread(*, user_a, user_b, kind, appointment=None, title=""):
    if appointment:
        thread, created = ChatThread.objects.get_or_create(
            appointment=appointment,
            defaults={
                "kind": kind,
                "user_a": user_a,
                "user_b": user_b,
                "title": title,
            },
        )
        if not created and title and not thread.title:
            thread.title = title
            thread.save(update_fields=["title", "updated_at"])
        return thread

    users = sorted([user_a, user_b], key=lambda item: item.pk)
    thread, created = ChatThread.objects.get_or_create(
        user_a=users[0],
        user_b=users[1],
        kind=kind,
        appointment__isnull=True,
        defaults={"title": title},
    )
    if not created and title and not thread.title:
        thread.title = title
        thread.save(update_fields=["title", "updated_at"])
    return thread


def _create_message_item(*, user, category, title, body, link=""):
    MessageItem.objects.create(
        user=user,
        category=category,
        title=title,
        body=body,
        link=link,
    )


def home(request):
    posts = ArtistPortfolio.objects.select_related("artist", "artist__profile").order_by("-hot_score", "-created_at")[:3]
    return render(request, "core/home.html", {"posts": posts})


def community(request):
    posts = ArtistPortfolio.objects.select_related("artist", "artist__profile")
    return render(request, "core/community.html", {"posts": posts})


@login_required
def community_post_create(request):
    form = CommunityPostForm(request.POST or None, request.FILES or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        post = form.save(commit=False)
        post.artist = request.user
        post.save()
        messages.success(request, "Community post published.")
        return redirect("community")
    return render(
        request,
        "core/community_post_form.html",
        {
            "form": form,
            "is_artist_post": request.user.profile.is_artist,
        },
    )


def login_view(request):
    return render(request, "core/login.html")


def google_login_start(request):
    if not settings.GOOGLE_OAUTH_CLIENT_ID or not settings.GOOGLE_OAUTH_CLIENT_SECRET:
        messages.error(request, "Google login is not configured.")
        return redirect("login")

    login_role = _login_role_from_request(request)
    state = secrets.token_urlsafe(32)
    request.session["google_oauth_state"] = state
    request.session["google_oauth_role"] = login_role
    request.session["google_oauth_next"] = request.GET.get("next") or _login_redirect_for_role(login_role)
    redirect_uri = settings.GOOGLE_OAUTH_REDIRECT_URI
    params = {
        "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }
    return redirect(f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}")


def google_login_callback(request):
    if request.GET.get("state") != request.session.pop("google_oauth_state", None):
        messages.error(request, "Google login session expired. Please try again.")
        return redirect("login")

    if request.GET.get("error"):
        messages.error(request, "Google login was cancelled.")
        return redirect("login")

    code = request.GET.get("code")
    if not code:
        messages.error(request, "Google did not return an authorization code.")
        return redirect("login")

    redirect_uri = settings.GOOGLE_OAUTH_REDIRECT_URI
    try:
        token_data = _google_token_request(code, redirect_uri)
        user_info = _google_userinfo_request(token_data["access_token"])
    except (KeyError, HTTPError, URLError, TimeoutError, ValueError):
        messages.error(request, "Google login failed. Check your OAuth client settings and redirect URI.")
        return redirect("login")

    email = user_info.get("email", "").strip().lower()
    if not email or not user_info.get("email_verified"):
        messages.error(request, "Google account email is not verified.")
        return redirect("login")

    user = _get_or_create_google_user(email, user_info)
    login(request, user)
    _store_login_role(request, request.session.pop("google_oauth_role", UserProfile.ROLE_CLIENT))
    messages.success(request, "Artist registration")
    return redirect(request.session.pop("google_oauth_next", reverse("dashboard")))


def _login_role_from_request(request):
    role = request.GET.get("role", UserProfile.ROLE_CLIENT)
    if role not in {UserProfile.ROLE_CLIENT, UserProfile.ROLE_ARTIST}:
        return UserProfile.ROLE_CLIENT
    return role


def _login_redirect_for_role(role):
    if role == UserProfile.ROLE_ARTIST:
        return reverse("portfolio_create")
    return reverse("dashboard")


def _store_login_role(request, role):
    request.session[LOGIN_ROLE_SESSION_KEY] = role


def _google_token_request(code, redirect_uri):
    body = urlencode(
        {
            "code": code,
            "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
            "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }
    ).encode("utf-8")
    request = Request(
        "https://oauth2.googleapis.com/token",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def _google_userinfo_request(access_token):
    request = Request(
        "https://www.googleapis.com/oauth2/v3/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    with urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def _get_or_create_google_user(email, user_info):
    User = get_user_model()
    user = User.objects.filter(email__iexact=email).first()
    if user is None:
        base_username = email.split("@")[0].replace(".", "_")[:120] or "google_user"
        username = base_username
        suffix = 1
        while User.objects.filter(username=username).exists():
            suffix += 1
            username = f"{base_username}_{suffix}"[:150]
        user = User.objects.create_user(
            username=username,
            email=email,
            first_name=user_info.get("given_name", "")[:150],
            last_name=user_info.get("family_name", "")[:150],
        )
        user.set_unusable_password()
        user.save()

    profile = user.profile
    profile.google_email = email
    if not profile.display_name:
        profile.display_name = user_info.get("name") or user.get_full_name() or user.username
    if not profile.avatar_url and user_info.get("picture"):
        profile.avatar_url = user_info["picture"]
    profile.save()
    return user


def static_profile(request):
    profile_path = LEGACY_SITE_ROOT / "profile.html"
    return HttpResponse(profile_path.read_text(encoding="utf-8"), content_type="text/html")


def legacy_site_file(request, filename):
    if filename in {"index", "index.html"}:
        return redirect("home")

    if filename in {"login", "login.html"}:
        return redirect("login")

    allowed_files = {
        "styles.css": "text/css",
        "script.js": "application/javascript",
    }
    if filename not in allowed_files:
        raise Http404
    return FileResponse(open(LEGACY_SITE_ROOT / filename, "rb"), content_type=allowed_files[filename])


def legacy_asset(request, asset_path):
    asset_root = (LEGACY_SITE_ROOT / "assets").resolve()
    file_path = (asset_root / asset_path).resolve()
    if asset_root not in file_path.parents or not file_path.is_file():
        raise Http404
    content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    return FileResponse(open(file_path, "rb"), content_type=content_type)


def google_login_demo(request):
    """Local functional stand-in for Google OAuth during prototype development."""
    User = get_user_model()
    login_role = _login_role_from_request(request)
    email = request.GET.get("email", "demo.google.user@example.com").strip().lower()
    username = email.split("@")[0].replace(".", "_")[:140]
    user, created = User.objects.get_or_create(
        username=username,
        defaults={"email": email, "first_name": "Demo", "last_name": "User"},
    )
    if created:
        user.set_unusable_password()
        user.save()
    profile = user.profile
    profile.google_email = email
    if not profile.display_name:
        profile.display_name = user.get_full_name() or username
    if login_role == UserProfile.ROLE_CLIENT:
        profile.role = UserProfile.ROLE_CLIENT
    profile.save()
    login(request, user)
    _store_login_role(request, login_role)
    messages.success(request, "Signed in with the local Google login prototype.")
    return redirect(_login_redirect_for_role(login_role))


def logout_view(request):
    logout(request)
    return redirect("home")


@login_required
def dashboard(request):
    profile = request.user.profile
    appointments = Appointment.objects.filter(
        Q(client=request.user) | Q(artist=request.user)
    ).select_related("client", "artist", "portfolio").order_by("appointment_date", "expected_finish_time", "-created_at")[:8]
    user_posts = request.user.portfolios.all()
    selected_date_raw = request.GET.get("date") or date.today().isoformat()
    try:
        selected_date = datetime.strptime(selected_date_raw, "%Y-%m-%d").date()
    except ValueError:
        selected_date = date.today()
        selected_date_raw = selected_date.isoformat()

    artist_schedule_context = {}
    if profile.is_artist:
        availability_windows = list(AvailabilityWindow.objects.filter(artist=request.user))
        occupied_times = list(OccupiedTime.objects.filter(artist=request.user).order_by("date", "start_time")[:30])
        booked_statuses = [
            Appointment.STATUS_ACCEPTED,
            Appointment.STATUS_DEPOSIT_PAID,
            Appointment.STATUS_COMPLETED,
            Appointment.STATUS_FINAL_PAID,
        ]
        artist_day_appointments = Appointment.objects.filter(
            artist=request.user,
            appointment_date=selected_date,
            status__in=booked_statuses,
        ).select_related("client", "portfolio").order_by("expected_finish_time")
        artist_booked_dates = list(
            Appointment.objects.filter(artist=request.user, status__in=booked_statuses)
            .values_list("appointment_date", flat=True)
            .distinct()
        )
        artist_schedule_context = {
            "bookable_posts": user_posts.filter(is_bookable=True),
            "non_bookable_posts": user_posts.filter(is_bookable=False),
            "availability_windows": availability_windows,
            "availability_weekdays_json": json.dumps(sorted({window.weekday for window in availability_windows})),
            "occupied_dates_json": json.dumps(sorted({item.date.isoformat() for item in occupied_times})),
            "booked_dates_json": json.dumps(sorted({item.isoformat() for item in artist_booked_dates})),
            "selected_date": selected_date,
            "selected_date_raw": selected_date_raw,
            "artist_day_appointments": artist_day_appointments,
            "artist_day_occupied": [item for item in occupied_times if item.date == selected_date],
            "can_enable_payments": user_posts.exists() and not profile.payment_enabled,
        }
    return render(
        request,
        "core/dashboard.html",
        {
            "profile": profile,
            "appointments": appointments,
            "user_posts": user_posts,
            **artist_schedule_context,
        },
    )


@login_required
def edit_profile(request):
    form = ProfileForm(request.POST or None, request.FILES or None, instance=request.user.profile)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profile updated.")
        return redirect("dashboard")
    return render(request, "core/profile_edit.html", {"form": form})


@login_required
def portfolio_create(request):
    profile = request.user.profile
    if not profile.is_artist:
        form = ArtistOnboardingForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            profile.role = UserProfile.ROLE_ARTIST
            profile.city = form.cleaned_data.get("location_city") or form.cleaned_data["location"]
            profile.address = form.cleaned_data["location"]
            social_platform = form.cleaned_data.get("social_platform", "").strip()
            social_handle = form.cleaned_data.get("social_handle", "").strip()
            if social_platform and social_handle:
                profile.social_media = f"{social_platform}: {social_handle}"
            elif social_handle:
                profile.social_media = social_handle
            elif social_platform:
                profile.social_media = social_platform
            else:
                profile.social_media = ""
            profile.preferred_styles = form.cleaned_data["style_tags"]
            profile.artist_price_range = f"AUD {form.cleaned_data['price_low']:.2f}-{form.cleaned_data['price_high']:.2f}"
            profile.stripe_onboarding_started = True
            profile.payment_enabled = False
            profile.save()

            messages.success(request, "Artist registration saved. Stripe onboarding can be connected next.")
            return redirect("dashboard")
        return render(
            request,
            "core/portfolio_form.html",
            {
                "form": form,
                "is_onboarding": True,
                "google_maps_api_key": settings.GOOGLE_MAPS_API_KEY,
            },
        )

    form = ArtistPortfolioForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        portfolio = form.save(commit=False)
        portfolio.artist = request.user
        portfolio.save()
        messages.success(request, "Portfolio saved.")
        return redirect("dashboard")
    return render(request, "core/portfolio_form.html", {"form": form, "is_onboarding": False})


@login_required
def portfolio_edit(request, pk):
    portfolio = get_object_or_404(ArtistPortfolio, pk=pk, artist=request.user)
    form = ArtistPortfolioForm(request.POST or None, request.FILES or None, instance=portfolio)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Portfolio updated.")
        return redirect("dashboard")
    return render(request, "core/portfolio_form.html", {"form": form, "is_onboarding": False})


def portfolio_detail(request, pk):
    portfolio = get_object_or_404(ArtistPortfolio.objects.select_related("artist", "artist__profile"), pk=pk)
    if request.method == "GET":
        ArtistPortfolio.objects.filter(pk=portfolio.pk).update(views=F("views") + 1)
        portfolio.views += 1
    comment_form = None
    if request.user.is_authenticated:
        comment_form = PostCommentForm(request.POST or None)
        if request.method == "POST" and comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.post = portfolio
            comment.author = request.user
            comment.save()
            if portfolio.artist != request.user:
                _create_message_item(
                    user=portfolio.artist,
                    category=MessageItem.CATEGORY_REVIEW,
                    title="New post comment",
                    body=f"{request.user.profile} commented on {portfolio.title}: {comment.body}",
                    link=reverse("portfolio_detail", args=[portfolio.pk]),
                )
            messages.success(request, "Comment posted.")
            return redirect("portfolio_detail", pk=portfolio.pk)
    return render(
        request,
        "core/portfolio_detail.html",
        {
            "portfolio": portfolio,
            "comments": portfolio.comments.select_related("author", "author__profile"),
            "comment_form": comment_form,
        },
    )


def artist_profile(request, user_id):
    artist = get_object_or_404(get_user_model(), pk=user_id)
    portfolios = artist.portfolios.all()
    bookable_portfolio = portfolios.filter(is_bookable=True).first()
    can_message = request.user.is_authenticated and request.user != artist
    return render(
        request,
        "core/artist_profile.html",
        {
            "artist": artist,
            "portfolios": portfolios,
            "bookable_portfolio": bookable_portfolio,
            "can_message": can_message,
        },
    )


def post_detail(request, pk):
    post = get_object_or_404(ArtistPortfolio.objects.select_related("artist", "artist__profile"), pk=pk)
    if request.method == "GET":
        ArtistPortfolio.objects.filter(pk=post.pk).update(views=F("views") + 1)
        post.views += 1
    template = "core/portfolio_detail.html" if post.is_bookable else "core/post_detail.html"
    comment_form = None
    if request.user.is_authenticated:
        comment_form = PostCommentForm(request.POST or None)
        if request.method == "POST" and comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.post = post
            comment.author = request.user
            comment.save()
            if post.artist != request.user:
                _create_message_item(
                    user=post.artist,
                    category=MessageItem.CATEGORY_REVIEW,
                    title="New post comment",
                    body=f"{request.user.profile} commented on {post.title}: {comment.body}",
                    link=reverse("post_detail", args=[post.pk]),
                )
            messages.success(request, "Comment posted.")
            return redirect("post_detail", pk=post.pk)
    return render(
        request,
        template,
        {
            "portfolio": post,
            "post": post,
            "comments": post.comments.select_related("author", "author__profile"),
            "comment_form": comment_form,
        },
    )


@login_required
def request_appointment(request, pk):
    portfolio = get_object_or_404(ArtistPortfolio.objects.select_related("artist"), pk=pk, is_bookable=True)
    if portfolio.artist == request.user:
        messages.error(request, "You cannot book your own portfolio.")
        return redirect(portfolio)
    form = AppointmentForm(request.POST or None, initial={"address": request.user.profile.address})
    if request.method == "POST" and form.is_valid():
        appointment = form.save(commit=False)
        appointment.client = request.user
        appointment.artist = portfolio.artist
        appointment.portfolio = portfolio
        appointment.full_price = portfolio.full_price
        appointment.save()
        thread = _get_or_create_thread(
            user_a=request.user,
            user_b=portfolio.artist,
            kind=ChatThread.THREAD_BOOKING,
            appointment=appointment,
            title=f"{portfolio.title} appointment chat",
        )
        ChatMessage.objects.create(
            thread=thread,
            sender=request.user,
            body=(
                f"Booking request for {portfolio.title} on {appointment.appointment_date} "
                f"finish by {appointment.expected_finish_time}. {appointment.notes or 'No extra notes.'}"
            ),
        )
        thread_link = reverse("thread_detail", args=[thread.pk])
        _create_message_item(
            user=portfolio.artist,
            category=MessageItem.CATEGORY_BOOKING,
            title="New booking request",
            body=(
                f"{request.user.profile} requested {portfolio.title} on {appointment.appointment_date}. "
                f"Expected finish: {appointment.expected_finish_time}. Notes: {appointment.notes or 'No notes'}"
            ),
            link=thread_link,
        )
        _create_message_item(
            user=request.user,
            category=MessageItem.CATEGORY_BOOKING,
            title="Booking request sent",
            body=f"Your request for {portfolio.title} is waiting for artist approval.",
            link=thread_link,
        )
        messages.success(request, "Booking request sent to the artist.")
        return redirect("dashboard")
    return render(request, "core/appointment_form.html", {"form": form, "portfolio": portfolio})


@login_required
def messages_box(request):
    items = request.user.message_items.all()
    appointment_items = items.filter(category__in=[MessageItem.CATEGORY_BOOKING, MessageItem.CATEGORY_PAYMENT])
    comment_items = items.filter(category=MessageItem.CATEGORY_REVIEW)
    threads = ChatThread.objects.filter(Q(user_a=request.user) | Q(user_b=request.user)).distinct()
    private_threads = threads.filter(kind=ChatThread.THREAD_PRIVATE, messages__isnull=False).distinct()
    private_thread_links = [reverse("thread_detail", args=[thread.pk]) for thread in private_threads]
    private_items = items.filter(category=MessageItem.CATEGORY_PRIVATE, link__in=private_thread_links)
    active_tab = request.GET.get("tab", "appointments")
    if active_tab not in {"appointments", "private", "comments"}:
        active_tab = "appointments"
    items.update(unread=False)
    return render(
        request,
        "core/messages.html",
        {
            "items": items,
            "appointment_items": appointment_items,
            "private_items": private_items,
            "comment_items": comment_items,
            "threads": threads,
            "private_threads": private_threads,
            "active_tab": active_tab,
        },
    )


@login_required
def schedule(request):
    if not request.user.profile.is_artist:
        messages.error(request, "Upload one bookable portfolio before editing artist schedule.")
        return redirect("portfolio_create")

    availability_form = AvailabilityWindowForm(prefix="availability")
    occupied_form = OccupiedTimeForm(prefix="occupied")

    if request.method == "POST":
        if request.POST.get("form_type") == "availability":
            availability_form = AvailabilityWindowForm(request.POST, prefix="availability")
            if availability_form.is_valid():
                window = availability_form.save(commit=False)
                window.artist = request.user
                window.save()
                messages.success(request, "Availability window added.")
                return redirect("schedule")
        elif request.POST.get("form_type") == "occupied":
            occupied_form = OccupiedTimeForm(request.POST, prefix="occupied")
            if occupied_form.is_valid():
                occupied = occupied_form.save(commit=False)
                occupied.artist = request.user
                occupied.save()
                messages.success(request, "Occupied time added.")
                return redirect("schedule")

    return render(
        request,
        "core/schedule.html",
        {
            "availability_form": availability_form,
            "occupied_form": occupied_form,
            "windows": AvailabilityWindow.objects.filter(artist=request.user),
            "occupied_times": OccupiedTime.objects.filter(artist=request.user)[:20],
        },
    )


@login_required
def work_notes(request):
    if not request.user.profile.is_artist:
        messages.error(request, "Work notes are for makeup artist accounts.")
        return redirect("dashboard")
    selected = request.GET.get("date") or date.today().isoformat()
    jobs = Appointment.objects.filter(
        artist=request.user,
        appointment_date=selected,
        status__in=[Appointment.STATUS_DEPOSIT_PAID, Appointment.STATUS_COMPLETED, Appointment.STATUS_FINAL_PAID],
    ).select_related("client", "portfolio")
    occupied = OccupiedTime.objects.filter(artist=request.user, date=selected)
    return render(request, "core/work_notes.html", {"selected": selected, "jobs": jobs, "occupied": occupied})


@login_required
@require_POST
def start_private_thread(request, user_id):
    other_user = get_object_or_404(get_user_model(), pk=user_id)
    if other_user == request.user:
        messages.error(request, "You cannot open a private chat with yourself.")
        return redirect("artist_profile", user_id=user_id)
    thread = _get_or_create_thread(
        user_a=request.user,
        user_b=other_user,
        kind=ChatThread.THREAD_PRIVATE,
        title=f"Private chat with {other_user.profile.display_name or other_user.username}",
    )
    return redirect("thread_detail", pk=thread.pk)


@login_required
def thread_detail(request, pk):
    thread = get_object_or_404(ChatThread, pk=pk)
    if request.user not in [thread.user_a, thread.user_b]:
        messages.error(request, "You do not have access to this chat.")
        return redirect("messages_box")
    form = ChatMessageForm(request.POST or None)
    other_user = thread.user_b if thread.user_a == request.user else thread.user_a
    if request.method == "POST" and form.is_valid():
        message = form.save(commit=False)
        message.thread = thread
        message.sender = request.user
        message.save()
        thread_link = reverse("thread_detail", args=[thread.pk])
        _create_message_item(
            user=other_user,
            category=MessageItem.CATEGORY_BOOKING if thread.kind == ChatThread.THREAD_BOOKING else MessageItem.CATEGORY_PRIVATE,
            title=_thread_display_title(thread, other_user),
            body=f"{request.user.profile}: {message.body}",
            link=thread_link,
        )
        messages.success(request, "Message sent.")
        return redirect("thread_detail", pk=thread.pk)
    request.user.message_items.filter(link=reverse("thread_detail", args=[thread.pk]), unread=True).update(unread=False)
    return render(
        request,
        "core/thread_detail.html",
        {
            "thread": thread,
            "thread_title": _thread_display_title(thread, request.user),
            "other_user": other_user,
            "messages_in_thread": thread.messages.select_related("sender", "sender__profile"),
            "form": form,
        },
    )


@login_required
@require_POST
def enable_payments(request):
    profile = request.user.profile
    if not profile.is_artist:
        messages.error(request, "Only makeup artist accounts can enable payments.")
        return redirect("dashboard")
    if not request.user.portfolios.exists():
        messages.error(request, "Publish at least one portfolio before enabling payments.")
        return redirect("dashboard")
    profile.stripe_onboarding_started = True
    profile.payment_enabled = True
    profile.save(update_fields=["stripe_onboarding_started", "payment_enabled", "updated_at"])
    messages.success(request, "Payments enabled in the prototype dashboard.")
    return redirect("dashboard")


@login_required
@require_POST
def toggle_portfolio_booking(request, pk):
    portfolio = get_object_or_404(ArtistPortfolio, pk=pk, artist=request.user)
    portfolio.is_bookable = not portfolio.is_bookable
    portfolio.post_type = ArtistPortfolio.POST_BOOKABLE if portfolio.is_bookable else ArtistPortfolio.POST_TIP
    portfolio.card_size = "tall" if portfolio.is_bookable else "wide"
    portfolio.save(update_fields=["is_bookable", "post_type", "card_size"])
    state = "bookable" if portfolio.is_bookable else "non-bookable"
    messages.success(request, f"Portfolio updated to {state}.")
    return redirect("dashboard")


@login_required
@require_POST
def accept_appointment(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk, artist=request.user)
    appointment.status = Appointment.STATUS_ACCEPTED
    appointment.save()
    thread = _get_or_create_thread(
        user_a=appointment.client,
        user_b=appointment.artist,
        kind=ChatThread.THREAD_BOOKING,
        appointment=appointment,
        title=f"{appointment.portfolio.title} appointment chat",
    )
    ChatMessage.objects.create(
        thread=thread,
        sender=request.user,
        body=f"Booking accepted. Deposit due: AUD {appointment.deposit_amount}.",
    )
    _create_message_item(
        user=appointment.client,
        category=MessageItem.CATEGORY_BOOKING,
        title="Booking accepted, deposit due",
        body=(
            f"{appointment.artist.profile} accepted your booking. "
            f"Deposit due: AUD {appointment.deposit_amount}. Platform fee retained from first payment: AUD {appointment.platform_fee}."
        ),
        link=reverse("thread_detail", args=[thread.pk]),
    )
    messages.success(request, "Appointment accepted. Client has been asked to pay deposit.")
    return redirect("dashboard")


@login_required
@require_POST
def cancel_appointment(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk)
    if request.user not in [appointment.client, appointment.artist]:
        messages.error(request, "You cannot cancel this appointment.")
        return redirect("dashboard")
    appointment.status = Appointment.STATUS_CANCELLED
    appointment.save()
    messages.success(request, "Appointment cancelled.")
    return redirect("dashboard")


@login_required
@require_POST
def pay_deposit(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk, client=request.user)
    if appointment.status != Appointment.STATUS_ACCEPTED:
        messages.error(request, "Deposit can only be paid after artist approval.")
        return redirect("dashboard")
    appointment.deposit_paid = True
    appointment.status = Appointment.STATUS_DEPOSIT_PAID
    appointment.save()
    thread = _get_or_create_thread(
        user_a=appointment.client,
        user_b=appointment.artist,
        kind=ChatThread.THREAD_BOOKING,
        appointment=appointment,
        title=f"{appointment.portfolio.title} appointment chat",
    )
    ChatMessage.objects.create(thread=thread, sender=request.user, body=f"Deposit paid: AUD {appointment.deposit_amount}.")
    _create_message_item(
        user=appointment.artist,
        category=MessageItem.CATEGORY_BOOKING,
        title="Deposit paid",
        body=(
            f"{appointment.client.profile} paid AUD {appointment.deposit_amount}. "
            f"Glow AU platform fee: AUD {appointment.platform_fee}. Artist receives AUD {appointment.deposit_artist_receives} from deposit."
        ),
        link=reverse("thread_detail", args=[thread.pk]),
    )
    messages.success(request, "Deposit paid in prototype. Stripe can be connected here later.")
    return redirect("dashboard")


@login_required
@require_POST
def mark_completed(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk, artist=request.user)
    if appointment.status != Appointment.STATUS_DEPOSIT_PAID:
        messages.error(request, "Only deposit-paid bookings can be marked completed.")
        return redirect("dashboard")
    appointment.status = Appointment.STATUS_COMPLETED
    appointment.save()
    thread = _get_or_create_thread(
        user_a=appointment.client,
        user_b=appointment.artist,
        kind=ChatThread.THREAD_BOOKING,
        appointment=appointment,
        title=f"{appointment.portfolio.title} appointment chat",
    )
    ChatMessage.objects.create(thread=thread, sender=request.user, body=f"Work marked completed. Final amount due: AUD {appointment.final_amount}.")
    _create_message_item(
        user=appointment.client,
        category=MessageItem.CATEGORY_BOOKING,
        title="Final payment due",
        body=f"Your makeup appointment is marked complete. Final amount due: AUD {appointment.final_amount}.",
        link=reverse("thread_detail", args=[thread.pk]),
    )
    messages.success(request, "Marked completed. Client has been asked for final payment.")
    return redirect("dashboard")


@login_required
@require_POST
def pay_final(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk, client=request.user)
    if appointment.status != Appointment.STATUS_COMPLETED:
        messages.error(request, "Final payment is available after artist marks the work completed.")
        return redirect("dashboard")
    appointment.final_paid = True
    appointment.status = Appointment.STATUS_FINAL_PAID
    appointment.save()
    thread = _get_or_create_thread(
        user_a=appointment.client,
        user_b=appointment.artist,
        kind=ChatThread.THREAD_BOOKING,
        appointment=appointment,
        title=f"{appointment.portfolio.title} appointment chat",
    )
    ChatMessage.objects.create(thread=thread, sender=request.user, body=f"Final payment paid: AUD {appointment.final_amount}.")
    _create_message_item(
        user=appointment.artist,
        category=MessageItem.CATEGORY_BOOKING,
        title="Final payment paid",
        body=f"{appointment.client.profile} paid final balance AUD {appointment.final_amount}.",
        link=reverse("thread_detail", args=[thread.pk]),
    )
    messages.success(request, "Final payment paid in prototype.")
    return redirect("dashboard")
