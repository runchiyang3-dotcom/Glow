from django.contrib import admin

from .models import Appointment, ArtistPortfolio, AvailabilityWindow, ChatMessage, ChatThread, MessageItem, OccupiedTime, PostComment, UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "display_name", "role", "city", "artist_price_range", "payment_enabled", "stripe_onboarding_started", "updated_at")
    list_filter = ("role", "payment_enabled", "stripe_onboarding_started")
    search_fields = ("user__username", "display_name", "city", "social_media", "artist_price_range")


@admin.register(ArtistPortfolio)
class ArtistPortfolioAdmin(admin.ModelAdmin):
    list_display = ("title", "artist", "style", "city", "price_range", "full_price", "is_bookable")
    list_filter = ("is_bookable", "city", "style")
    search_fields = ("title", "artist__username", "style", "style_tags")


@admin.register(AvailabilityWindow)
class AvailabilityWindowAdmin(admin.ModelAdmin):
    list_display = ("artist", "weekday", "start_time", "pause_start", "pause_end", "end_time")
    list_filter = ("weekday",)


@admin.register(OccupiedTime)
class OccupiedTimeAdmin(admin.ModelAdmin):
    list_display = ("artist", "date", "start_time", "end_time", "note")
    list_filter = ("date",)


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("client", "artist", "portfolio", "appointment_date", "status", "full_price")
    list_filter = ("status", "appointment_date")
    search_fields = ("client__username", "artist__username", "notes", "address")


@admin.register(MessageItem)
class MessageItemAdmin(admin.ModelAdmin):
    list_display = ("user", "category", "title", "unread", "created_at")
    list_filter = ("category", "unread")


@admin.register(ChatThread)
class ChatThreadAdmin(admin.ModelAdmin):
    list_display = ("title", "kind", "user_a", "user_b", "updated_at")
    list_filter = ("kind",)


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("thread", "sender", "created_at")


@admin.register(PostComment)
class PostCommentAdmin(admin.ModelAdmin):
    list_display = ("post", "author", "created_at")

# Register your models here.
