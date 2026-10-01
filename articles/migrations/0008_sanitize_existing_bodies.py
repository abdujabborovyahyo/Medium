from django.db import migrations


def sanitize_bodies(apps, schema_editor):
    """Articles saved before sanitization was added may contain unsafe HTML."""
    from articles.sanitizers import sanitize_html

    Article = apps.get_model("articles", "Article")
    for article in Article.objects.only("pk", "body").iterator():
        clean = sanitize_html(article.body)
        if clean != article.body:
            # .update() so that updated_at (auto_now) is not touched
            Article.objects.filter(pk=article.pk).update(body=clean)


class Migration(migrations.Migration):

    dependencies = [
        ("articles", "0007_tag_ordering"),
    ]

    operations = [
        migrations.RunPython(sanitize_bodies, migrations.RunPython.noop),
    ]
