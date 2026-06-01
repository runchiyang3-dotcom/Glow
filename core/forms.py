import io
from decimal import Decimal

from django import forms
from django.core.files.base import ContentFile
from PIL import Image

from .models import Appointment, ArtistPortfolio, AvailabilityWindow, ChatMessage, OccupiedTime, PostComment, UserProfile


ARTIST_REGISTRATION_STYLE_TAGS = [
    ("clean beauty", "Clean beauty"),
    ("bridal glow", "Bridal glow"),
    ("soft glam", "Soft glam"),
    ("glass skin", "Glass skin"),
    ("editorial", "Editorial"),
    ("douyin", "Douyin"),
    ("k-beauty", "K-beauty"),
    ("coquette", "Coquette"),
    ("y2k", "Y2K"),
    ("latte makeup", "Latte makeup"),
]

ARTIST_REGISTRATION_SOCIAL_PLATFORMS = [
    ("", "Optional"),
    ("Instagram", "Instagram"),
    ("TikTok", "TikTok"),
    ("REDnote", "REDnote"),
]


class ProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ["display_name", "city", "phone", "address", "bio", "preferred_styles", "social_media", "avatar"]
        widgets = {
            "bio": forms.Textarea(attrs={"rows": 4}),
            "preferred_styles": forms.TextInput(attrs={"placeholder": "Clean beauty, bridal glow, soft glam"}),
            "social_media": forms.TextInput(attrs={"placeholder": "Instagram, TikTok, website, or portfolio link"}),
        }


class ArtistPortfolioForm(forms.ModelForm):
    class Meta:
        model = ArtistPortfolio
        fields = [
            "title",
            "style",
            "city",
            "address",
            "description",
            "image_url",
            "image",
            "full_price",
            "price_range",
            "style_tags",
            "is_bookable",
            "availability_label",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "full_price": forms.NumberInput(attrs={"min": "0", "step": "0.01"}),
        }


class CommunityPostForm(forms.ModelForm):
    is_bookable = forms.BooleanField(required=False)
    image = forms.ImageField(required=True)
    address = forms.CharField(required=False, max_length=240)
    derived_city = forms.CharField(required=False, max_length=120)
    crop_left = forms.FloatField(required=False, widget=forms.HiddenInput())
    crop_top = forms.FloatField(required=False, widget=forms.HiddenInput())
    crop_width = forms.FloatField(required=False, widget=forms.HiddenInput())
    crop_height = forms.FloatField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = ArtistPortfolio
        fields = [
            "title",
            "description",
            "full_price",
            "style_tags",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4, "placeholder": "Share your look, request, idea, or booking note"}),
            "full_price": forms.NumberInput(attrs={"min": "0", "step": "0.01"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.fields["title"].widget.attrs.update({"placeholder": "Name the look, request, or booking post"})
        self.fields["style_tags"].widget = forms.HiddenInput()
        self.fields["is_bookable"].widget = forms.HiddenInput()
        self.fields["full_price"].required = False
        if not (user and user.profile.is_artist):
            self.fields["is_bookable"].required = False

    def clean(self):
        cleaned = super().clean()
        user = self.user
        is_bookable = cleaned.get("is_bookable")
        full_price = cleaned.get("full_price")
        address = (cleaned.get("address") or "").strip()
        image = cleaned.get("image")
        tags = [tag.strip() for tag in (cleaned.get("style_tags") or "").split(",") if tag.strip()]

        if not user:
            raise forms.ValidationError("Login required.")

        if not image:
            self.add_error("image", "Add an image by upload or paste before publishing.")

        if not tags:
            self.add_error("style_tags", "Add at least one style tag.")
        elif len(tags) > 12:
            self.add_error("style_tags", "Keep style tags to 12 or fewer.")

        if user.profile.is_artist:
            if is_bookable and not user.profile.payment_enabled:
                raise forms.ValidationError("Enable payments before publishing bookable community posts.")
        else:
            if is_bookable:
                raise forms.ValidationError("Client accounts cannot publish bookable posts.")

        if is_bookable and not full_price:
            self.add_error("full_price", "Bookable posts require a full price.")

        if is_bookable and not address:
            self.add_error("address", "Choose or type the booking address.")

        cleaned["style_tags"] = ", ".join(tags)
        cleaned["address"] = address
        cleaned["derived_city"] = (cleaned.get("derived_city") or "").strip()

        return cleaned

    def save(self, commit=True):
        post = super().save(commit=False)
        tags = [tag.strip() for tag in self.cleaned_data["style_tags"].split(",") if tag.strip()]
        derived_city = self.cleaned_data.get("derived_city") or ""
        profile = self.user.profile

        post.is_bookable = bool(self.cleaned_data.get("is_bookable"))
        post.post_type = ArtistPortfolio.POST_BOOKABLE if post.is_bookable else ArtistPortfolio.POST_TIP
        post.full_price = self.cleaned_data.get("full_price") or Decimal("0.00")
        post.price_range = ""
        post.price_label = "" if post.is_bookable else "Community post"
        post.availability_label = "Available Sat-Sun" if post.is_bookable else "Community post"
        post.address = self.cleaned_data.get("address", "")
        post.city = derived_city or profile.city or "Australia"
        post.style = " / ".join(tags[:2]) if tags else (profile.preferred_styles or "Community look")
        post.card_size = "tall" if post.is_bookable else "wide"
        post.image_url = ""
        post.image = self._build_cropped_image()

        if commit:
            post.save()
        return post

    def _build_cropped_image(self):
        upload = self.cleaned_data["image"]
        crop_left = self.cleaned_data.get("crop_left")
        crop_top = self.cleaned_data.get("crop_top")
        crop_width = self.cleaned_data.get("crop_width")
        crop_height = self.cleaned_data.get("crop_height")

        image = Image.open(upload)
        image = image.convert("RGB")
        width, height = image.size

        if all(value is not None for value in [crop_left, crop_top, crop_width, crop_height]):
            left = max(0, min(width - 1, round(crop_left)))
            top = max(0, min(height - 1, round(crop_top)))
            crop_w = max(1, min(width - left, round(crop_width)))
            crop_h = max(1, min(height - top, round(crop_height)))
            image = image.crop((left, top, left + crop_w, top + crop_h))

        image = image.resize((1200, 1500), Image.Resampling.LANCZOS)
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=90)
        filename_root = (self.cleaned_data.get("title") or "community-post").lower().replace(" ", "-")[:40]
        return ContentFile(buffer.getvalue(), name=f"{filename_root or 'community-post'}.jpg")


class ArtistOnboardingForm(forms.Form):
    location_query = forms.CharField(
        label="Service city",
        widget=forms.TextInput(attrs={"placeholder": "Start typing an Australian city"}),
    )
    location = forms.CharField(widget=forms.HiddenInput())
    location_city = forms.CharField(widget=forms.HiddenInput(), required=False)
    price_low = forms.DecimalField(
        min_value=0,
        decimal_places=2,
        max_digits=8,
        label="Low price",
    )
    price_high = forms.DecimalField(
        min_value=0,
        decimal_places=2,
        max_digits=8,
        label="High price",
    )
    style_tags = forms.CharField(widget=forms.HiddenInput())
    social_platform = forms.ChoiceField(choices=ARTIST_REGISTRATION_SOCIAL_PLATFORMS, required=False)
    social_handle = forms.CharField(
        max_length=240,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "@yourname, https://..., or a portfolio URL"}),
        help_text="Add a handle, website, or portfolio link.",
    )

    def clean_style_tags(self):
        tags = [tag.strip() for tag in (self.cleaned_data.get("style_tags") or "").split(",") if tag.strip()]
        if not tags:
            raise forms.ValidationError("Choose at least one style tag.")
        if len(tags) > 5:
            raise forms.ValidationError("Choose 5 style tags or fewer.")
        return ", ".join(tags)

    def clean(self):
        cleaned = super().clean()
        location = (cleaned.get("location") or "").strip()
        location_query = (cleaned.get("location_query") or "").strip()
        price_low = cleaned.get("price_low")
        price_high = cleaned.get("price_high")
        if not location:
            self.add_error("location_query", "Choose a city from the suggestions.")
        if price_low is not None and price_high is not None and price_low > price_high:
            self.add_error("price_high", "High price must be greater than or equal to low price.")
        cleaned["social_handle"] = (cleaned.get("social_handle") or "").strip()
        cleaned["location"] = location
        cleaned["location_query"] = location_query
        return cleaned


class AvailabilityWindowForm(forms.ModelForm):
    class Meta:
        model = AvailabilityWindow
        fields = ["weekday", "start_time", "pause_start", "pause_end", "end_time"]
        widgets = {
            "start_time": forms.TimeInput(attrs={"type": "time"}),
            "pause_start": forms.TimeInput(attrs={"type": "time"}),
            "pause_end": forms.TimeInput(attrs={"type": "time"}),
            "end_time": forms.TimeInput(attrs={"type": "time"}),
        }

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("start_time")
        end = cleaned.get("end_time")
        pause_start = cleaned.get("pause_start")
        pause_end = cleaned.get("pause_end")

        if start and end and start >= end:
            raise forms.ValidationError("Business start time must be before end time.")

        if bool(pause_start) != bool(pause_end):
            raise forms.ValidationError("Fill both pause start and pause end, or leave both empty.")

        if pause_start and pause_end:
            if pause_start >= pause_end:
                raise forms.ValidationError("Pause start time must be before pause end time.")
            if start and end and not (start < pause_start < pause_end < end):
                raise forms.ValidationError("Pause time must sit inside business hours.")

        return cleaned


class OccupiedTimeForm(forms.ModelForm):
    class Meta:
        model = OccupiedTime
        fields = ["date", "start_time", "end_time", "note"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "start_time": forms.TimeInput(attrs={"type": "time"}),
            "end_time": forms.TimeInput(attrs={"type": "time"}),
        }

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("start_time")
        end = cleaned.get("end_time")
        if start and end and start >= end:
            raise forms.ValidationError("Occupied start time must be before end time.")
        return cleaned


class AppointmentForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ["appointment_date", "expected_finish_time", "address", "notes"]
        widgets = {
            "appointment_date": forms.DateInput(attrs={"type": "date"}),
            "expected_finish_time": forms.TimeInput(attrs={"type": "time"}),
            "notes": forms.Textarea(attrs={"rows": 4, "placeholder": "Style, mood, skin notes, reference details"}),
        }


class PostCommentForm(forms.ModelForm):
    class Meta:
        model = PostComment
        fields = ["body"]
        widgets = {
            "body": forms.Textarea(attrs={"rows": 3, "placeholder": "Add a comment to this post"}),
        }


class ChatMessageForm(forms.ModelForm):
    class Meta:
        model = ChatMessage
        fields = ["body"]
        widgets = {
            "body": forms.Textarea(attrs={"rows": 3, "placeholder": "Write your message"}),
        }
