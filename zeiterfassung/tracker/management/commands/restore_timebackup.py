import json
from datetime import date
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.db import transaction
from tracker.models import Profile, Schedule, YearAllowance, Entry
from tracker.forms import EntryForm

class Command(BaseCommand):
    help='Persönliche JSON-Sicherung einem bestehenden Benutzer zuordnen und wiederherstellen.'
    def add_arguments(self,parser):
        parser.add_argument('file')
        parser.add_argument('--username',required=True)
        parser.add_argument('--replace',action='store_true',help='Bestehende Zeiterfassungsdaten dieses Benutzers ersetzen.')
    def handle(self,*args,**opts):
        try:
            user=get_user_model().objects.get(username=opts['username'])
        except get_user_model().DoesNotExist:
            raise CommandError('Benutzer existiert nicht. Zuerst createsuperuser ausführen.')
        try:
            payload=json.loads(Path(opts['file']).read_text(encoding='utf-8'))
            if not isinstance(payload,dict) or payload.get('format')!='zeiterfassung-v1' or not isinstance(payload.get('data'),list):
                raise ValueError('Unbekanntes Sicherungsformat.')
            mapping={'tracker.profile':Profile,'tracker.schedule':Schedule,'tracker.yearallowance':YearAllowance,'tracker.entry':Entry}
            if not opts['replace'] and any(m.objects.filter(user=user).exists() for m in mapping.values()):
                raise CommandError('Benutzer hat schon Daten. Zuerst aktuelle Sicherung erstellen; dann bewusst --replace angeben.')
            with transaction.atomic():
                for model in mapping.values(): model.objects.filter(user=user).delete()
                profile_count=0
                for item in payload['data']:
                    cls=mapping.get(item.get('model'))
                    if not cls: raise ValueError('Unzulässiger Datensatz in Sicherung.')
                    fields=dict(item['fields']); fields.pop('user',None)
                    allowed={f.name for f in cls._meta.fields}-{'id','user'}
                    if not set(fields)<=allowed: raise ValueError('Unbekannte Felder.')
                    obj=cls(user=user,**fields)
                    obj.full_clean()
                    if cls is Profile:
                        profile_count+=1
                        if not 2000<=obj.start_date.year<=2100: raise ValueError('Startdatum ausserhalb des unterstützten Bereichs.')
                    if cls is Schedule:
                        if not isinstance(obj.weekdays,list) or not obj.weekdays or len(set(obj.weekdays))!=len(obj.weekdays) or any(type(v)!=int or v not in range(7) for v in obj.weekdays):
                            raise ValueError('Ungültige Arbeitstage.')
                        if not 2000<=obj.effective_from.year<=2100: raise ValueError('Ungültiges Plandatum.')
                    if cls is Entry:
                        if not 2000<=obj.date.year<=2100: raise ValueError('Ungültiges Eintragsdatum.')
                        # ModelForm prüft zusätzlich Reihenfolge, Paare und Abwesenheiten.
                        form_data={k:getattr(obj,k) for k in EntryForm.Meta.fields}
                        form_data['fraction']=format(obj.fraction.normalize(),'f')
                        form=EntryForm(data=form_data,instance=obj)
                        if not form.is_valid(): raise ValueError(str(form.errors))
                    obj.save()
                if profile_count!=1 or not Schedule.objects.filter(user=user).exists():
                    raise ValueError('Sicherung benötigt genau ein Profil und mindestens einen Arbeitsplan.')
                start=Profile.objects.get(user=user).start_date
                if Entry.objects.filter(user=user,date__lt=start).exists(): raise ValueError('Einträge liegen vor dem Erfassungsbeginn.')
        except CommandError:
            raise
        except (OSError,ValueError,TypeError,KeyError,AttributeError,ValidationError) as exc:
            raise CommandError(f'Sicherung nicht übernommen: {exc}')
        self.stdout.write(self.style.SUCCESS('Persönliche Zeiterfassungsdaten wiederhergestellt.'))
