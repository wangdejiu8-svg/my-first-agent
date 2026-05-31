from django.db import migrations


SUPPORTED_SUFFIXES = (".docx", ".pdf")


def backfill_attachment_knowledge_documents(apps, schema_editor):
    Attachment = apps.get_model("chat", "Attachment")
    KnowledgeDocument = apps.get_model("chat", "KnowledgeDocument")

    existing_attachment_ids = set(
        KnowledgeDocument.objects.values_list("attachment_id", flat=True)
    )
    pending_documents = []
    for attachment in Attachment.objects.all().iterator():
        original_name = str(getattr(attachment, "original_name", "") or "")
        if attachment.id in existing_attachment_ids:
            continue
        if not original_name.lower().endswith(SUPPORTED_SUFFIXES):
            continue
        pending_documents.append(
            KnowledgeDocument(
                owner_id=attachment.owner_id,
                conversation_id=attachment.conversation_id,
                attachment_id=attachment.id,
                title=original_name[:255],
                source_type="attachment",
                index_status="pending",
            )
        )

    if pending_documents:
        KnowledgeDocument.objects.bulk_create(pending_documents, batch_size=200)


class Migration(migrations.Migration):
    dependencies = [
        ("chat", "0003_message_metadata_json_knowledgedocument_and_more"),
    ]

    operations = [
        migrations.RunPython(
            backfill_attachment_knowledge_documents,
            migrations.RunPython.noop,
        ),
    ]
