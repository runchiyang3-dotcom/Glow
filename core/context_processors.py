from .models import UserProfile


LOGIN_ROLE_SESSION_KEY = "glow_login_role"


def message_badge(request):
    if request.user.is_authenticated:
        login_role = request.session.get(LOGIN_ROLE_SESSION_KEY) or request.user.profile.role
        login_role_label = "Makeup artist" if login_role == UserProfile.ROLE_ARTIST else "Client"
        return {
            "unread_message_count": request.user.message_items.filter(unread=True).count(),
            "active_login_role": login_role,
            "active_login_role_label": login_role_label,
        }
    return {
        "unread_message_count": 0,
        "active_login_role": UserProfile.ROLE_CLIENT,
        "active_login_role_label": "Client",
    }
