# Generated by Django 2.2.7 on 2019-11-14 22:57

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models

import bidpazari.core.models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Item',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('title', models.CharField(max_length=128)),
                ('description', models.CharField(blank=True, max_length=128)),
                ('item_type', models.CharField(blank=True, max_length=128)),
                ('on_sale', models.BooleanField(default=False)),
                ('image', models.ImageField(upload_to='images/%Y-%m/')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AlterModelOptions(
            name='user',
            options={},
        ),
        migrations.AddField(
            model_name='user',
            name='created',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='user',
            name='modified',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name='user',
            name='verification_number',
            field=models.CharField(blank=True, default=bidpazari.core.models.generate_verification_number, max_length=16),
        ),
        migrations.AddField(
            model_name='user',
            name='verification_status',
            field=models.CharField(choices=[('verified', 'Verified'), ('unverified', 'Unverified')], default='unverified', max_length=16),
        ),
        migrations.CreateModel(
            name='UserHasItem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('is_sold', models.BooleanField(default=False)),
                ('item', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='item_has_users', to='core.Item')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='user_has_items', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Transaction',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=7)),
                ('destination', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='incoming_transactions', to=settings.AUTH_USER_MODEL)),
                ('item', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='transactions', to='core.Item')),
                ('source', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='outgoing_transactions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
    ]