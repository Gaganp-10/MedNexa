from django.db import migrations


def cleanup_wording(apps, schema_editor):
    Alert = apps.get_model('alerts', 'Alert')
    WoundImage = apps.get_model('monitoring', 'WoundImage')

    replacements = {
        "Critical fever detected": "Urgent medical review recommended: high temperature recorded (prototype indicator)",
        "High fever detected": "Medical review recommended: elevated temperature recorded (prototype indicator)",
        "Severe pain detected": "Urgent review recommended: severe pain reported (prototype indicator)",
        "Severe pain reported": "Medical review recommended: notable pain reported (prototype indicator)",
        "Medication missed": "Medication adherence notice: scheduled dose not recorded (prototype indicator)",
        "Possible infection detected": "Possible visual concern; medical review recommended (prototype indicator)",
        "Normal wound healing": "Normal visual variation; routine observation recommended (prototype indicator)",
    }

    for alert in Alert.objects.all():
        updated = False
        for old_txt, new_txt in replacements.items():
            if old_txt in alert.message:
                alert.message = alert.message.replace(old_txt, new_txt)
                updated = True
        if updated:
            alert.save()

    for wound in WoundImage.objects.all():
        updated = False
        for old_txt, new_txt in replacements.items():
            if old_txt in (wound.analysis_result or ""):
                wound.analysis_result = wound.analysis_result.replace(old_txt, new_txt)
                updated = True
        if updated:
            wound.save()


class Migration(migrations.Migration):

    dependencies = [
        ('alerts', '0001_initial'),
        ('monitoring', '0002_dailyhealthlog_recovery_score'),
    ]

    operations = [
        migrations.RunPython(cleanup_wording, migrations.RunPython.noop),
    ]
