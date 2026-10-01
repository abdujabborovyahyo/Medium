from django import forms
from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import CustomUser


class EmailUniqueMixin:
    """Emails are compared case-insensitively: Ali@Mail.com == ali@mail.com."""

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        qs = CustomUser.objects.filter(email__iexact=email)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email


class CustomUserCreationForm(EmailUniqueMixin, UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={"placeholder": "you@example.com", "autocomplete": "email"}),
    )

    class Meta:
        model = CustomUser
        fields = ("username", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update(
            {"placeholder": "e.g. yahyobek", "autocomplete": "username", "autofocus": True}
        )
        self.fields["username"].help_text = "Letters, digits and @/./+/-/_ only."
        self.fields["password1"].widget.attrs.update({"placeholder": "At least 8 characters"})
        self.fields["password1"].help_text = "Use 8+ characters. Avoid common or only-numeric passwords."
        self.fields["password2"].widget.attrs.update({"placeholder": "Repeat the password"})
        self.fields["password2"].label = "Confirm password"
        self.fields["password2"].help_text = ""


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update({"placeholder": "Your username", "autofocus": True})
        self.fields["password"].widget.attrs.update({"placeholder": "Your password"})


class ProfileForm(EmailUniqueMixin, forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ("username", "email", "bio", "website", "avatar")
        widgets = {
            "bio": forms.Textarea(attrs={"rows": 4, "placeholder": "Tell readers a little about yourself..."}),
            "website": forms.URLInput(attrs={"placeholder": "https://your-site.example"}),
            "username": forms.TextInput(attrs={"placeholder": "Display name"}),
            "email": forms.EmailInput(attrs={"placeholder": "you@example.com"}),
            "avatar": forms.ClearableFileInput(attrs={"accept": "image/jpeg,image/png,image/webp,image/gif"}),
        }

    def clean_avatar(self):
        avatar = self.cleaned_data.get("avatar")
        if avatar and hasattr(avatar, "content_type") and avatar.size > settings.IMAGE_MAX_UPLOAD_SIZE:
            raise forms.ValidationError("Avatar is too large (max 5 MB).")
        return avatar
