import io
import tempfile

from PIL import Image
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import ArtistPortfolio, UserProfile


TEST_MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class CommunityPostCreateTests(TestCase):
    def _make_image_upload(self, color=(220, 160, 170)):
        image = Image.new("RGB", (1200, 1500), color)
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG")
        return SimpleUploadedFile("post.jpg", buffer.getvalue(), content_type="image/jpeg")

    def _create_user(self, username, role, payment_enabled=False):
        user = get_user_model().objects.create_user(username=username, password="testpass123")
        profile = user.profile
        profile.role = role
        profile.city = "Brisbane, QLD"
        profile.address = "South Brisbane studio, Brisbane QLD"
        profile.payment_enabled = payment_enabled
        profile.save()
        return user

    def test_client_can_publish_non_bookable_community_post(self):
        user = self._create_user("client_user", UserProfile.ROLE_CLIENT)
        self.client.force_login(user)

        response = self.client.post(
            reverse("community_post_create"),
            data={
                "title": "Soft glam notes",
                "description": "Everyday glow with a little extra shimmer.",
                "style_tags": "soft glam, shimmer",
                "crop_left": "0",
                "crop_top": "0",
                "crop_width": "1200",
                "crop_height": "1500",
                "image": self._make_image_upload(),
            },
        )

        self.assertRedirects(response, reverse("community"))
        post = ArtistPortfolio.objects.get(title="Soft glam notes")
        self.assertFalse(post.is_bookable)
        self.assertEqual(post.post_type, ArtistPortfolio.POST_TIP)
        self.assertEqual(post.full_price, 0)
        self.assertTrue(bool(post.image))

    def test_artist_bookable_post_requires_address_and_price(self):
        user = self._create_user("artist_user", UserProfile.ROLE_ARTIST, payment_enabled=True)
        self.client.force_login(user)

        response = self.client.post(
            reverse("community_post_create"),
            data={
                "title": "Bridal booking slot",
                "description": "Openings for bridal mornings.",
                "style_tags": "bridal, clean skin",
                "is_bookable": "true",
                "crop_left": "0",
                "crop_top": "0",
                "crop_width": "1200",
                "crop_height": "1500",
                "image": self._make_image_upload(),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bookable posts require a full price.")
        self.assertContains(response, "Choose or type the booking address.")
        self.assertFalse(ArtistPortfolio.objects.filter(title="Bridal booking slot").exists())

    def test_post_detail_increments_views(self):
        user = self._create_user("viewer_user", UserProfile.ROLE_CLIENT)
        post = ArtistPortfolio.objects.create(
            artist=user,
            title="Reference look",
            style="Soft glam",
            city="Brisbane, QLD",
            description="Natural skin and gloss.",
            is_bookable=False,
            post_type=ArtistPortfolio.POST_TIP,
            views=3,
        )

        response = self.client.get(reverse("post_detail", args=[post.pk]))

        self.assertEqual(response.status_code, 200)
        post.refresh_from_db()
        self.assertEqual(post.views, 4)

    def test_logged_in_user_sees_real_booking_form_on_artist_profile(self):
        artist = self._create_user("artist_profile_user", UserProfile.ROLE_ARTIST, payment_enabled=True)
        client = self._create_user("client_profile_user", UserProfile.ROLE_CLIENT)
        portfolio = ArtistPortfolio.objects.create(
            artist=artist,
            title="Weekend bridal slot",
            style="Bridal glow",
            city="Brisbane, QLD",
            address="South Brisbane studio, Brisbane QLD",
            description="Soft bridal makeup for weekend bookings.",
            full_price="180.00",
            is_bookable=True,
            post_type=ArtistPortfolio.POST_BOOKABLE,
        )
        self.client.force_login(client)

        response = self.client.get(reverse("artist_profile", args=[artist.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'action="{reverse("request_appointment", args=[portfolio.pk])}"')
        self.assertContains(response, 'name="appointment_date"')
        self.assertContains(response, 'name="expected_finish_time"')
        self.assertContains(response, 'name="address"')
        self.assertContains(response, 'name="notes"')
        self.assertNotContains(response, "Please log in to submit a booking request.")

    def test_artist_registration_uses_select_based_fields(self):
        user = self._create_user("registration_user", UserProfile.ROLE_CLIENT)
        self.client.force_login(user)

        response = self.client.post(
            reverse("portfolio_create"),
            data={
                "location_query": "CBD studio, Sydney NSW",
                "location": "CBD studio, Sydney NSW",
                "location_city": "Sydney, NSW",
                "price_low": "260",
                "price_high": "380",
                "style_tags": "clean beauty, bridal glow, soft glam",
                "social_platform": "REDnote",
                "social_handle": "@glowbyrunchi",
            },
        )

        self.assertRedirects(response, reverse("dashboard"))
        user.refresh_from_db()
        self.assertEqual(user.profile.role, UserProfile.ROLE_ARTIST)
        self.assertEqual(user.profile.city, "Sydney, NSW")
        self.assertEqual(user.profile.address, "CBD studio, Sydney NSW")
        self.assertEqual(user.profile.artist_price_range, "AUD 260.00-380.00")
        self.assertEqual(user.profile.preferred_styles, "clean beauty, bridal glow, soft glam")
        self.assertEqual(user.profile.social_media, "REDnote: @glowbyrunchi")

    def test_artist_registration_allows_empty_social_fields(self):
        user = self._create_user("registration_user_no_social", UserProfile.ROLE_CLIENT)
        self.client.force_login(user)

        response = self.client.post(
            reverse("portfolio_create"),
            data={
                "location_query": "CBD studio, Sydney NSW",
                "location": "CBD studio, Sydney NSW",
                "location_city": "Sydney, NSW",
                "price_low": "260",
                "price_high": "380",
                "style_tags": "clean beauty, bridal glow",
                "social_platform": "",
                "social_handle": "",
            },
        )

        self.assertRedirects(response, reverse("dashboard"))
        user.refresh_from_db()
        self.assertEqual(user.profile.social_media, "")

    def test_artist_demo_login_shows_artist_login_label_before_registration(self):
        response = self.client.get(
            reverse("google_login_demo"),
            {"role": UserProfile.ROLE_ARTIST, "email": "artist.label@example.com"},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Logged in as Makeup artist")
