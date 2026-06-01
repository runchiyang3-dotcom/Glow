from datetime import date, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from core.models import (
    Appointment,
    ArtistPortfolio,
    AvailabilityWindow,
    MessageItem,
    OccupiedTime,
    UserProfile,
)


class Command(BaseCommand):
    help = "Create repeatable Glow AU demo users, artists, portfolios, messages and bookings."

    def handle(self, *args, **options):
        User = get_user_model()
        artist, _ = User.objects.get_or_create(
            username="ava_artist",
            defaults={"email": "ava.artist@example.com", "first_name": "Ava", "last_name": "Studio"},
        )
        artist.set_unusable_password()
        artist.save()
        artist.profile.role = UserProfile.ROLE_ARTIST
        artist.profile.display_name = "Ava Studio"
        artist.profile.city = "Sydney NSW"
        artist.profile.address = "Level 3, 88 Pitt Street, Sydney NSW 2000"
        artist.profile.avatar_url = "https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=120&q=80"
        artist.profile.bio = "Soft bridal glow, long-wear skin prep and editorial event makeup."
        artist.profile.social_media = "@avastudio"
        artist.profile.payment_enabled = True
        artist.profile.stripe_onboarding_started = True
        artist.profile.save()

        client, _ = User.objects.get_or_create(
            username="amanda_client",
            defaults={"email": "amanda@example.com", "first_name": "Amanda", "last_name": "Lee"},
        )
        client.set_unusable_password()
        client.save()
        client.profile.display_name = "Amanda Lee"
        client.profile.city = "Brisbane QLD"
        client.profile.address = "Garden City, Brisbane"
        client.profile.preferred_styles = "Bridal glow, soft and warm"
        client.profile.save()

        portfolio, _ = ArtistPortfolio.objects.update_or_create(
            artist=artist,
            title="Bridal soft-glow trial",
            defaults={
                "style": "Bridal makeup",
                "city": "Sydney NSW",
                "description": "Refined bridal skin, soft rose tones, lashes and camera-ready complexion.",
                "image_url": "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?auto=format&fit=crop&w=900&q=85",
                "full_price": Decimal("320.00"),
                "price_range": "AUD 220-320",
                "style_tags": "Clean beauty, bridal glow, soft glam",
                "is_bookable": True,
                "post_type": ArtistPortfolio.POST_BOOKABLE,
                "card_size": "tall",
                "availability_label": "Available Sat-Sun",
                "latest_score": 96,
                "hot_score": 88,
                "views": 128,
            },
        )

        mia, _ = User.objects.get_or_create(
            username="mia_chen",
            defaults={"email": "mia@example.com", "first_name": "Mia", "last_name": "Chen"},
        )
        mia.set_unusable_password()
        mia.save()
        mia.profile.role = UserProfile.ROLE_ARTIST
        mia.profile.display_name = "Mia Chen MUA"
        mia.profile.city = "Brisbane QLD"
        mia.profile.address = "12 James Street, Fortitude Valley QLD 4006"
        mia.profile.avatar_url = "https://images.unsplash.com/photo-1488426862026-3ee34a7d66df?auto=format&fit=crop&w=120&q=80"
        mia.profile.bio = "Clean beauty, editorial and event makeup artist based in Brisbane."
        mia.profile.social_media = "@mia.chen"
        mia.profile.payment_enabled = False
        mia.profile.stripe_onboarding_started = True
        mia.profile.save()
        ArtistPortfolio.objects.update_or_create(
            artist=mia,
            title="Making clean event makeup last comfortably",
            defaults={
                "style": "Clean event technique",
                "city": "Brisbane QLD",
                "description": "Mia shares how she balances breathable skin prep, soft definition and long-wear touch points for clean event looks that stay comfortable through long bookings.",
                "image_url": "https://images.unsplash.com/photo-1516975080664-ed2fc6a32937?auto=format&fit=crop&w=900&q=85",
                "full_price": Decimal("180.00"),
                "price_range": "AUD 160-240",
                "style_tags": "Clean beauty, soft event makeup",
                "is_bookable": False,
                "post_type": ArtistPortfolio.POST_TIP,
                "card_size": "tall",
                "price_label": "Technique share",
                "availability_label": "For long events",
                "latest_score": 84,
                "hot_score": 97,
                "views": 2100,
            },
        )

        jisoo, _ = User.objects.get_or_create(
            username="jisoo_park",
            defaults={"email": "jisoo@example.com", "first_name": "Jisoo", "last_name": "Park"},
        )
        jisoo.set_unusable_password()
        jisoo.save()
        jisoo.profile.display_name = "Jisoo Park"
        jisoo.profile.city = "Melbourne VIC"
        jisoo.profile.address = "305 Swanston Street, Melbourne VIC 3000"
        jisoo.profile.avatar_url = "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?auto=format&fit=crop&w=120&q=80"
        jisoo.profile.bio = "Melbourne client looking for soft clean-beauty makeup for personal events and photo sessions."
        jisoo.profile.save()
        ArtistPortfolio.objects.update_or_create(
            artist=jisoo,
            title="Seeking a K-pop idol-inspired makeup artist",
            defaults={
                "style": "K-pop idol glam",
                "city": "Melbourne VIC",
                "description": "Jisoo is looking for an artist experienced in glass skin, aegyo-sal detail, soft contour, glossy lips and camera-ready styling for a birthday shoot.",
                "image_url": "https://images.unsplash.com/photo-1508214751196-bcfd4ca60f91?auto=format&fit=crop&w=900&q=85",
                "full_price": Decimal("220.00"),
                "price_range": "Budget AUD 150-220",
                "style_tags": "Soft clean beauty",
                "is_bookable": False,
                "post_type": ArtistPortfolio.POST_REQUEST,
                "card_size": "wide",
                "price_label": "Budget AUD 150-220",
                "availability_label": "Needed next Friday",
                "latest_score": 92,
                "hot_score": 94,
                "views": 96,
            },
        )

        AvailabilityWindow.objects.get_or_create(
            artist=artist,
            weekday=5,
            start_time=time(8, 0),
            pause_start=time(12, 30),
            pause_end=time(13, 30),
            end_time=time(18, 0),
        )
        OccupiedTime.objects.get_or_create(
            artist=artist,
            date=date.today() + timedelta(days=3),
            start_time=time(14, 0),
            end_time=time(16, 0),
            defaults={"note": "Anna, clean event makeup, CBD"},
        )

        appointment, _ = Appointment.objects.get_or_create(
            client=client,
            artist=artist,
            portfolio=portfolio,
            appointment_date=date.today(),
            defaults={
                "expected_finish_time": time(15, 30),
                "address": "Garden City, Brisbane",
                "notes": "Demo client order: soft clean beauty makeup for an afternoon event.",
                "full_price": portfolio.full_price,
                "status": Appointment.STATUS_ACCEPTED,
            },
        )
        appointment.appointment_date = date.today()
        appointment.expected_finish_time = time(15, 30)
        appointment.notes = "Demo client order: soft clean beauty makeup for an afternoon event."
        appointment.status = Appointment.STATUS_ACCEPTED
        appointment.save()

        MessageItem.objects.get_or_create(
            user=artist,
            category=MessageItem.CATEGORY_BOOKING,
            title="Demo booking request",
            defaults={
                "body": f"Amanda requested {portfolio.title} on {appointment.appointment_date}.",
                "link": "/dashboard/",
            },
        )
        self.stdout.write(self.style.SUCCESS("Demo data ready."))
