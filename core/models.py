from decimal import Decimal

from django.conf import settings
from django.db import models
from django.urls import reverse


class UserProfile(models.Model):
    ROLE_CLIENT = "client"
    ROLE_ARTIST = "artist"
    ROLE_CHOICES = [
        (ROLE_CLIENT, "Client"),
        (ROLE_ARTIST, "Makeup artist"),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_CLIENT)
    display_name = models.CharField(max_length=120, blank=True)
    city = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    address = models.CharField(max_length=240, blank=True)
    bio = models.TextField(blank=True)
    preferred_styles = models.CharField(max_length=240, blank=True)
    social_media = models.CharField(max_length=240, blank=True)
    artist_price_range = models.CharField(max_length=80, blank=True)
    payment_enabled = models.BooleanField(default=False)
    stripe_onboarding_started = models.BooleanField(default=False)
    google_email = models.EmailField(blank=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True)
    avatar_url = models.URLField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.display_name or self.user.get_username()

    @property
    def is_artist(self):
        return self.role == self.ROLE_ARTIST


class ArtistPortfolio(models.Model):
    POST_BOOKABLE = "bookable"
    POST_REQUEST = "request"
    POST_TIP = "tip"
    POST_CHOICES = [
        (POST_BOOKABLE, "Bookable"),
        (POST_REQUEST, "Request"),
        (POST_TIP, "Tip"),
    ]
    CARD_CHOICES = [
        ("tall", "Tall"),
        ("wide", "Wide"),
    ]

    artist = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="portfolios")
    title = models.CharField(max_length=140)
    style = models.CharField(max_length=120)
    city = models.CharField(max_length=120)
    address = models.CharField(max_length=240, blank=True)
    description = models.TextField()
    image_url = models.URLField(blank=True)
    image = models.ImageField(upload_to="community_posts/", blank=True)
    full_price = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0.00"))
    price_range = models.CharField(max_length=80, blank=True)
    style_tags = models.CharField(max_length=180, blank=True)
    is_bookable = models.BooleanField(default=True)
    post_type = models.CharField(max_length=20, choices=POST_CHOICES, default=POST_BOOKABLE)
    card_size = models.CharField(max_length=10, choices=CARD_CHOICES, default="tall")
    price_label = models.CharField(max_length=80, blank=True)
    availability_label = models.CharField(max_length=120, default="Available Sat-Sun")
    latest_score = models.PositiveIntegerField(default=80)
    hot_score = models.PositiveIntegerField(default=80)
    views = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} by {self.artist}"

    def get_absolute_url(self):
        return reverse("portfolio_detail", args=[self.pk])

    @property
    def display_image_url(self):
        if self.image:
            return self.image.url
        return self.image_url

    @property
    def display_address(self):
        return self.address or self.artist.profile.address

    @property
    def display_price_text(self):
        if self.is_bookable:
            return f"AUD {self.full_price}"
        return self.price_label or self.price_range or ""

    @property
    def deposit_amount(self):
        return (self.full_price / Decimal("4")).quantize(Decimal("0.01"))

    @property
    def final_amount(self):
        return (self.full_price - self.deposit_amount).quantize(Decimal("0.01"))


class AvailabilityWindow(models.Model):
    WEEKDAYS = [
        (0, "Monday"),
        (1, "Tuesday"),
        (2, "Wednesday"),
        (3, "Thursday"),
        (4, "Friday"),
        (5, "Saturday"),
        (6, "Sunday"),
    ]

    artist = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="availability_windows")
    weekday = models.PositiveSmallIntegerField(choices=WEEKDAYS)
    start_time = models.TimeField()
    pause_start = models.TimeField(blank=True, null=True)
    pause_end = models.TimeField(blank=True, null=True)
    end_time = models.TimeField()

    class Meta:
        ordering = ["weekday", "start_time"]
        unique_together = [("artist", "weekday", "start_time", "end_time")]

    def __str__(self):
        pause = ""
        if self.pause_start and self.pause_end:
            pause = f", pause {self.pause_start}-{self.pause_end}"
        return f"{self.get_weekday_display()} {self.start_time}-{self.end_time}{pause}"


class OccupiedTime(models.Model):
    artist = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="occupied_times")
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    note = models.CharField(max_length=240, blank=True)

    class Meta:
        ordering = ["date", "start_time"]

    def __str__(self):
        return f"{self.date} {self.start_time}-{self.end_time}"


class Appointment(models.Model):
    STATUS_PENDING = "pending"
    STATUS_ACCEPTED = "accepted"
    STATUS_DEPOSIT_PAID = "deposit_paid"
    STATUS_COMPLETED = "completed"
    STATUS_FINAL_PAID = "final_paid"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending artist approval"),
        (STATUS_ACCEPTED, "Accepted, deposit due"),
        (STATUS_DEPOSIT_PAID, "Deposit paid"),
        (STATUS_COMPLETED, "Work completed, final payment due"),
        (STATUS_FINAL_PAID, "Final paid"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="client_appointments")
    artist = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="artist_appointments")
    portfolio = models.ForeignKey(ArtistPortfolio, on_delete=models.PROTECT, related_name="appointments")
    appointment_date = models.DateField()
    expected_finish_time = models.TimeField()
    address = models.CharField(max_length=240)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=24, choices=STATUS_CHOICES, default=STATUS_PENDING)
    full_price = models.DecimalField(max_digits=8, decimal_places=2)
    deposit_paid = models.BooleanField(default=False)
    final_paid = models.BooleanField(default=False)
    platform_fee = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("2.00"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-appointment_date", "-created_at"]

    def __str__(self):
        return f"{self.client} -> {self.artist} on {self.appointment_date}"

    @property
    def deposit_amount(self):
        return (self.full_price / Decimal("4")).quantize(Decimal("0.01"))

    @property
    def deposit_artist_receives(self):
        value = self.deposit_amount - self.platform_fee
        return max(value, Decimal("0.00")).quantize(Decimal("0.01"))

    @property
    def final_amount(self):
        return (self.full_price - self.deposit_amount).quantize(Decimal("0.01"))


class MessageItem(models.Model):
    CATEGORY_BOOKING = "booking"
    CATEGORY_REVIEW = "review"
    CATEGORY_PRIVATE = "private"
    CATEGORY_PAYMENT = "payment"
    CATEGORY_CHOICES = [
        (CATEGORY_BOOKING, "Appointment"),
        (CATEGORY_REVIEW, "Post comment"),
        (CATEGORY_PRIVATE, "Private message"),
        (CATEGORY_PAYMENT, "Payment"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="message_items")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    title = models.CharField(max_length=160)
    body = models.TextField()
    link = models.CharField(max_length=240, blank=True)
    unread = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class ChatThread(models.Model):
    THREAD_BOOKING = "booking"
    THREAD_PRIVATE = "private"
    THREAD_CHOICES = [
        (THREAD_BOOKING, "Appointment chat"),
        (THREAD_PRIVATE, "Private chat"),
    ]

    kind = models.CharField(max_length=20, choices=THREAD_CHOICES, default=THREAD_PRIVATE)
    user_a = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chat_threads_started")
    user_b = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chat_threads_received")
    appointment = models.OneToOneField(Appointment, on_delete=models.CASCADE, related_name="chat_thread", blank=True, null=True)
    title = models.CharField(max_length=160, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-updated_at", "-created_at"]

    def __str__(self):
        return self.title or f"{self.user_a} / {self.user_b}"


class ChatMessage(models.Model):
    thread = models.ForeignKey(ChatThread, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_chat_messages")
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.sender} -> {self.thread_id}"


class PostComment(models.Model):
    post = models.ForeignKey(ArtistPortfolio, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="post_comments")
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.author} on {self.post}"

# Create your models here.
