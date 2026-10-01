from django import forms
from django.conf import settings
from django.utils.html import strip_tags

from .models import Article, Tag

MAX_TAGS = 5


class ArticleForm(forms.ModelForm):
    # Tags are typed as comma-separated text and turned into Tag objects in save()
    tags = forms.CharField(
        required=False,
        label="Tags",
        help_text="Comma-separated, up to 5 tags",
        widget=forms.TextInput(attrs={"placeholder": "e.g. technology, django, web"}),
    )
    # Filled by the Quill editor in the browser
    body = forms.CharField(widget=forms.HiddenInput())
    cover_image = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(attrs={"accept": "image/jpeg,image/png,image/webp,image/gif"}),
    )

    class Meta:
        model = Article
        # `tags` is deliberately not listed: it's not a model field on the form level
        fields = ["title", "excerpt", "body", "cover_image", "is_member_only", "status"]
        labels = {"is_member_only": "Member-only story"}
        help_texts = {"is_member_only": "Only your followers can read this article"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and not self.is_bound:
            self.initial["tags"] = ", ".join(self.instance.tags.values_list("name", flat=True))

    def clean_body(self):
        body = self.cleaned_data["body"]
        # Quill's "empty" document is "<p><br></p>"
        if not strip_tags(body).strip() and "<img" not in body and "<iframe" not in body:
            raise forms.ValidationError("Article body cannot be empty.")
        return body

    def clean_tags(self):
        raw = self.cleaned_data.get("tags", "")
        names = []
        for name in raw.split(","):
            name = name.strip()[:50]
            if name and name.lower() not in (n.lower() for n in names):
                names.append(name)
        if len(names) > MAX_TAGS:
            raise forms.ValidationError(f"Use at most {MAX_TAGS} tags.")
        return names

    def clean_cover_image(self):
        image = self.cleaned_data.get("cover_image")
        if image and hasattr(image, "content_type"):
            if image.size > settings.IMAGE_MAX_UPLOAD_SIZE:
                raise forms.ValidationError(
                    f"Cover image is too large (max {settings.IMAGE_MAX_UPLOAD_SIZE // (1024 * 1024)} MB)."
                )
        return image

    def save(self, commit=True):
        article = super().save(commit=commit)
        if commit:
            self.save_tags(article)
        return article

    def save_tags(self, article):
        tags = []
        for name in self.cleaned_data.get("tags", []):
            tag = Tag.objects.filter(name__iexact=name).first() or Tag.objects.create(name=name)
            tags.append(tag)
        article.tags.set(tags)
