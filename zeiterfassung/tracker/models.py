from datetime import date
from decimal import Decimal
from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

def default_days(): return [3,4]
class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
    start_date = models.DateField(default=date.today)
    opening_minutes = models.IntegerField(default=0)

class Schedule(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
    effective_from = models.DateField()
    daily_minutes = models.PositiveIntegerField(default=520,validators=[MinValueValidator(1),MaxValueValidator(1440)])
    weekdays = models.JSONField(default=default_days)
    class Meta:
        ordering=['effective_from']
        constraints=[models.UniqueConstraint(fields=['user','effective_from'],name='unique_schedule_date')]

class YearAllowance(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
    year = models.PositiveIntegerField(validators=[MinValueValidator(2000),MaxValueValidator(2100)])
    days = models.DecimalField(max_digits=5,decimal_places=2,validators=[MinValueValidator(0)])
    carry = models.DecimalField(max_digits=5,decimal_places=2,default=0,validators=[MinValueValidator(0)])
    class Meta:
        constraints=[models.UniqueConstraint(fields=['user','year'],name='unique_allowance_year')]

class Entry(models.Model):
    KINDS=[('work','Arbeit'),('vacation','Ferien'),('sick','Krankheit'),('holiday','Feiertag'),('comp','Überstundenabbau'),('unpaid','Unbezahlte Abwesenheit')]
    user = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
    date = models.DateField()
    kind = models.CharField(max_length=10,choices=KINDS,default='work')
    fraction = models.DecimalField(max_digits=2,decimal_places=1,default=Decimal('1'),choices=[(Decimal('1'),'Ganzer Tag'),(Decimal('0.5'),'Halber Tag')])
    start = models.TimeField(null=True,blank=True)
    break_start = models.TimeField(null=True,blank=True)
    break_end = models.TimeField(null=True,blank=True)
    end = models.TimeField(null=True,blank=True)
    target_override = models.PositiveIntegerField(null=True,blank=True,validators=[MaxValueValidator(1440)])
    finalized = models.BooleanField(default=False)
    note = models.TextField(blank=True,max_length=2000)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering=['date']
        constraints=[models.UniqueConstraint(fields=['user','date'],name='unique_entry_date')]
