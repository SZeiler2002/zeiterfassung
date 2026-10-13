from datetime import date
from decimal import Decimal
from django import forms
from .models import Entry, Profile, YearAllowance
from .services import minutes

class EntryForm(forms.ModelForm):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        if 'fraction' in self.initial:
            self.initial['fraction']=format(Decimal(self.initial['fraction']).normalize(),'f')
    class Meta:
        model=Entry
        fields=['kind','fraction','start','break_start','break_end','end','target_override','finalized','note']
        labels={'kind':'Eintragsart','fraction':'Abwesenheitsdauer','start':'Arbeitsbeginn','break_start':'Beginn Mittagspause','break_end':'Ende Mittagspause','end':'Feierabend','target_override':'Abweichendes Tagessoll (Minuten)','finalized':'Tag abschliessen','note':'Notiz'}
        widgets={**{k:forms.TimeInput(format='%H:%M',attrs={'type':'time'}) for k in ['start','break_start','break_end','end']},'note':forms.Textarea(attrs={'rows':3}),'target_override':forms.NumberInput(attrs={'min':0,'max':1440})}
        help_texts={'target_override':'Leer = Arbeitsplan, 0 = freier Tag. 520 Minuten = 8:40 Stunden.','finalized':'Auch einen Tag mit nur einem Zeitpaar oder ohne Arbeit abschliessen. Ein abgeschlossener Arbeitstag ohne Zeiten ergibt das volle Minus.','fraction':'Gilt nur für Abwesenheiten. Bei einem halben Tag die restliche Arbeitszeit zusätzlich eintragen.'}
    def clean(self):
        c=super().clean()
        ts=[c.get(k) for k in ['start','break_start','break_end','end']]
        filled=[minutes(t) for t in ts if t is not None]
        if any(b<=a for a,b in zip(filled,filled[1:])):
            raise forms.ValidationError('Stempelzeiten müssen aufsteigend am selben Tag liegen. Nachtschichten bitte auf zwei Tage aufteilen.')
        partial=any((ts[i] is None)!=(ts[i+1] is None) for i in [0,2])
        if c.get('finalized') and partial:
            raise forms.ValidationError('Zum Abschliessen beide Zeiten eines Zeitpaares ausfüllen.')
        if c.get('kind')!='work' and c.get('fraction')==1 and any(ts):
            raise forms.ValidationError('Bei ganztägiger Abwesenheit keine Stempelzeiten eintragen; gegebenenfalls halben Tag wählen.')
        if c.get('kind')=='work': c['fraction']=Decimal('1')
        return c

class ProfileForm(forms.ModelForm):
    class Meta:
        model=Profile
        fields=['start_date','opening_minutes']
        labels={'start_date':'Beginn der Zeiterfassung','opening_minutes':'Anfangssaldo in Minuten (Minus erlaubt)'}
        widgets={'start_date':forms.DateInput(format='%Y-%m-%d',attrs={'type':'date'})}
        help_texts={'opening_minutes':'Beispiel: +2:30 Stunden = 150; −1:00 Stunde = −60.'}

class ScheduleForm(forms.Form):
    effective_from=forms.DateField(label='Arbeitsplan gültig ab',widget=forms.DateInput(attrs={'type':'date'}))
    daily_minutes=forms.IntegerField(label='Soll pro Arbeitstag in Minuten',initial=520,min_value=1,max_value=1440)
    weekdays=forms.TypedMultipleChoiceField(label='Reguläre Arbeitstage',coerce=int,choices=list(enumerate(['Montag','Dienstag','Mittwoch','Donnerstag','Freitag','Samstag','Sonntag'])),widget=forms.CheckboxSelectMultiple,initial=[3,4])

class AllowanceForm(forms.ModelForm):
    class Meta:
        model=YearAllowance
        fields=['year','days','carry']
        labels={'year':'Kalenderjahr','days':'Ferienanspruch in deinen Arbeitstagen','carry':'Übertrag aus Vorjahr (Tage)'}
        help_texts={'days':'Beispiel: 5 Wochen × 2 Arbeitstage = 10 Ferientage. Nicht nochmals mit 40 % multiplizieren.','carry':'Manuell gemäss deinem bestätigten Restanspruch eintragen.'}

class MoveForm(forms.Form):
    source=forms.DateField(label='Arbeitstag verschieben von',widget=forms.DateInput(attrs={'type':'date'}))
    destination=forms.DateField(label='Neuer Arbeitstag',widget=forms.DateInput(attrs={'type':'date'}))

class AbsenceForm(forms.Form):
    start=forms.DateField(label='Von',widget=forms.DateInput(attrs={'type':'date'}))
    end=forms.DateField(label='Bis',widget=forms.DateInput(attrs={'type':'date'}))
    kind=forms.ChoiceField(label='Abwesenheit',choices=Entry.KINDS[1:])
    fraction=forms.TypedChoiceField(label='Dauer pro Arbeitstag',choices=[('1','Ganzer Tag'),('0.5','Halber Tag')],coerce=Decimal)
    note=forms.CharField(label='Notiz',required=False,max_length=2000,widget=forms.Textarea(attrs={'rows':2}))
    def clean(self):
        c=super().clean()
        if c.get('start') and c.get('end') and not 0<=(c['end']-c['start']).days<=366:
            raise forms.ValidationError('Bitte einen Zeitraum von höchstens 367 Tagen in aufsteigender Reihenfolge wählen.')
        return c
