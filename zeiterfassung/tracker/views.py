import calendar
import csv
import json
from datetime import date, timedelta
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core import serializers
from django.db import transaction
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect
from django.urls import reverse
from .models import Profile, Schedule, Entry, YearAllowance
from .forms import EntryForm, ProfileForm, ScheduleForm, AllowanceForm, MoveForm, AbsenceForm
from .services import Ledger, dates, duration, setup

MONTHS=['Januar','Februar','März','April','Mai','Juni','Juli','August','September','Oktober','November','Dezember']
def selected_month(request):
    try:
        day=date.fromisoformat(request.GET.get('month',date.today().strftime('%Y-%m'))+'-01')
        if not 2000<=day.year<=2100: raise ValueError
        return day
    except ValueError:
        return date.today().replace(day=1)
def month_last(day): return date(day.year,day.month,calendar.monthrange(day.year,day.month)[1])
def back_to_day(day): return reverse('calendar')+'?month='+day.strftime('%Y-%m')

@login_required
def calendar_view(request):
    month=selected_month(request); ledger=Ledger(request.user)
    weeks=[]
    for week in calendar.Calendar(firstweekday=0).monthdatescalendar(month.year,month.month):
        weeks.append({'number':week[0].isocalendar().week,'days':[dict(ledger.row(d),outside=d.month!=month.month,today=d==ledger.today) for d in week],'total':ledger.totals(week[0],week[-1])})
    current_start=ledger.today-timedelta(days=ledger.today.weekday())
    return render(request,'tracker/calendar.html',{'month':month,'month_name':MONTHS[month.month-1],'previous':(month-timedelta(days=1)).strftime('%Y-%m'),'next':(month_last(month)+timedelta(days=1)).strftime('%Y-%m'),'weeks':weeks,'monthly':ledger.totals(month,month_last(month)),'weekly':ledger.totals(current_start,current_start+timedelta(days=6)),'balance':ledger.balance(),'vacation':ledger.vacation(month.year),'today':ledger.today,'profile':ledger.profile,'total_pending':ledger.totals(ledger.profile.start_date,ledger.today)['pending']})

@login_required
def day_view(request,day):
    try:
        day=date.fromisoformat(day)
        if not 2000<=day.year<=2100: raise ValueError
    except ValueError: return HttpResponseBadRequest('Ungültiges Datum.')
    ledger=Ledger(request.user)
    entry=ledger.entries.get(day) or Entry(user=request.user,date=day)
    if request.method=='POST' and request.POST.get('action')=='delete':
        if entry.pk: entry.delete()
        messages.success(request,'Eintrag entfernt. Das Soll aus dem Arbeitsplan gilt wieder.')
        return redirect(back_to_day(day))
    form=EntryForm(request.POST or None,instance=entry)
    if request.method=='POST' and form.is_valid():
        if day<ledger.profile.start_date:
            form.add_error(None,'Dieser Tag liegt vor deinem Erfassungsbeginn. Ändere zuerst das Startdatum in den Einstellungen.')
        else:
            form.save(); messages.success(request,'Tag gespeichert.')
            return redirect(back_to_day(day))
    return render(request,'tracker/day.html',{'form':form,'day':day,'row':ledger.row(day),'back':back_to_day(day),'exists':bool(entry.pk)})

@login_required
def settings_view(request):
    profile=setup(request.user)
    action=request.POST.get('action') if request.method=='POST' else None
    pf=ProfileForm(request.POST if action=='profile' else None,instance=profile)
    sf=ScheduleForm(request.POST if action=='schedule' else None,initial={'effective_from':date.today()})
    af=AllowanceForm(request.POST if action=='allowance' else None,initial={'year':date.today().year,'carry':0})
    if action=='profile' and pf.is_valid():
        start=pf.cleaned_data['start_date']
        earliest=Entry.objects.filter(user=request.user).order_by('date').first()
        if earliest and earliest.date<start:
            pf.add_error('start_date','Vor diesem Startdatum liegen bereits Einträge. Entferne diese zuerst oder wähle ein früheres Datum.')
        elif not 2000<=start.year<=2100:
            pf.add_error('start_date','Bitte ein Datum zwischen 2000 und 2100 wählen.')
        else:
            with transaction.atomic():
                pf.save()
                first=Schedule.objects.filter(user=request.user).first()
                if first and start<first.effective_from:
                    Schedule.objects.create(user=request.user,effective_from=start,daily_minutes=first.daily_minutes,weekdays=first.weekdays)
            messages.success(request,'Grundeinstellungen gespeichert.'); return redirect('settings')
    if action=='schedule' and sf.is_valid():
        c=sf.cleaned_data
        if c['effective_from']<profile.start_date or not 2000<=c['effective_from'].year<=2100:
            sf.add_error('effective_from','Gültigkeitsbeginn muss ab Erfassungsbeginn und zwischen 2000 und 2100 liegen.')
        elif Schedule.objects.filter(user=request.user,effective_from=c['effective_from']).exists() and not request.POST.get('confirm_replace'):
            sf.add_error(None,'Für dieses Datum existiert bereits ein Plan. Zum Ersetzen unten die Bestätigung aktivieren.')
        else:
            Schedule.objects.update_or_create(user=request.user,effective_from=c['effective_from'],defaults={'daily_minutes':c['daily_minutes'],'weekdays':c['weekdays']})
            messages.success(request,'Arbeitsplan gespeichert. Er gilt ab dem angegebenen Datum.'); return redirect('settings')
    if action=='allowance' and af.is_valid():
        c=af.cleaned_data
        YearAllowance.objects.update_or_create(user=request.user,year=c['year'],defaults={'days':c['days'],'carry':c['carry']})
        messages.success(request,'Ferienanspruch gespeichert.'); return redirect('settings')
    allowances=YearAllowance.objects.filter(user=request.user).order_by('-year')
    return render(request,'tracker/settings.html',{'profile_form':pf,'schedule_form':sf,'allowance_form':af,'schedules':Schedule.objects.filter(user=request.user),'allowances':allowances})

@login_required
def move_view(request):
    form=MoveForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        a=form.cleaned_data['source']; b=form.cleaned_data['destination']
        with transaction.atomic():
            ledger=Ledger(request.user)
            old=ledger.entries.get(a); new=ledger.entries.get(b)
            if a==b or a<ledger.profile.start_date or b<ledger.profile.start_date or not (2000<=a.year<=2100 and 2000<=b.year<=2100):
                form.add_error(None,'Bitte zwei verschiedene Tage ab Erfassungsbeginn (2000–2100) wählen.')
            elif ledger.row(a)['target']<=0 or ledger.row(b)['target']!=0:
                form.add_error(None,'Der Ausgangstag muss ein Arbeitstag und der Zieltag frei sein.')
            elif any(e and (e.kind!='work' or e.start or e.break_start or e.break_end or e.end or e.finalized) for e in [old,new]):
                form.add_error(None,'An einem der Tage sind bereits Zeiten oder Abwesenheiten erfasst. Bitte zuerst die Tageseinträge bearbeiten.')
            else:
                target=ledger.row(a)['target']
                Entry.objects.update_or_create(user=request.user,date=a,defaults={'target_override':0})
                Entry.objects.update_or_create(user=request.user,date=b,defaults={'target_override':target})
                messages.success(request,f'Arbeitstag von {a:%d.%m.%Y} auf {b:%d.%m.%Y} verschoben.'); return redirect(back_to_day(b))
    return render(request,'tracker/form.html',{'form':form,'title':'Arbeitstag verschieben','intro':'Das Soll wandert mit. Die Stempelzeiten werden anschliessend am neuen Arbeitstag eingetragen. Bei einer Verschiebung über eine Wochen- oder Monatsgrenze wandert auch das Periodensoll mit.','button':'Arbeitstag verschieben'})

@login_required
def absence_view(request):
    form=AbsenceForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        c=form.cleaned_data; ledger=Ledger(request.user)
        if c['start']<ledger.profile.start_date or not (2000<=c['start'].year<=2100 and 2000<=c['end'].year<=2100):
            form.add_error(None,'Zeitraum muss ab Erfassungsbeginn und zwischen 2000 und 2100 liegen.')
        else:
            selected=[d for d in dates(c['start'],c['end']) if ledger.row(d)['target']>0]
            conflicts=[d for d in selected if (e:=ledger.entries.get(d)) and (e.kind!='work' or e.start or e.break_start or e.break_end or e.end or e.finalized or e.note)]
            if conflicts:
                form.add_error(None,'Vorhandene Einträge werden nicht überschrieben. Bitte diese Tage einzeln bearbeiten: '+', '.join(d.strftime('%d.%m.%Y') for d in conflicts))
            elif not selected: form.add_error(None,'In diesem Zeitraum sind keine Arbeitstage geplant.')
            else:
                with transaction.atomic():
                    for d in selected:
                        Entry.objects.update_or_create(user=request.user,date=d,defaults={'kind':c['kind'],'fraction':c['fraction'],'note':c['note'],'finalized':c['fraction']==1})
                messages.success(request,f'Abwesenheit für {len(selected)} Arbeitstage gespeichert.'); return redirect(back_to_day(c['start']))
    return render(request,'tracker/form.html',{'form':form,'title':'Ferien & Abwesenheiten','intro':'Nur geplante Arbeitstage werden eingetragen. Ferien, Krankheit und Feiertage erhalten eine Zeitgutschrift; Überstundenabbau verbraucht Zeitguthaben. Feiertage werden manuell erfasst.','button':'Zeitraum eintragen'})

@login_required
def year_view(request):
    try: year=int(request.GET.get('year',date.today().year)); assert 2000<=year<=2100
    except (ValueError,AssertionError): year=date.today().year
    ledger=Ledger(request.user)
    months=[{'name':MONTHS[m-1],'month':f'{year}-{m:02d}',**ledger.totals(date(year,m,1),date(year,m,calendar.monthrange(year,m)[1]))} for m in range(1,13)]
    return render(request,'tracker/year.html',{'year':year,'previous':year-1,'next':year+1,'months':months,'total':ledger.totals(date(year,1,1),date(year,12,31)),'vacation':ledger.vacation(year)})

@login_required
def export_view(request):
    month=selected_month(request); ledger=Ledger(request.user)
    response=HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition']=f'attachment; filename="zeiterfassung-{month:%Y-%m}.csv"'
    response.write('\ufeff'); writer=csv.writer(response,delimiter=';')
    writer.writerow(['Datum','Art','Beginn','Pause von','Pause bis','Ende','Soll','Arbeit','Gutschrift','Saldo','Status','Notiz'])
    for day in dates(month,month_last(month)):
        r=ledger.row(day); e=r['entry']
        note=e.note if e else ''
        if note.lstrip().startswith(('=','+','-','@')): note="'"+note
        times=[getattr(e,k).strftime('%H:%M') if e and getattr(e,k) else '' for k in ['start','break_start','break_end','end']]
        writer.writerow([day.isoformat(),e.get_kind_display() if e else '',*times,duration(r['target']),duration(r['actual']),duration(r['credit']),duration(r['delta'],True) if r['delta'] is not None else '', 'Geplant' if r['future'] else ('Offen' if r['pending'] else ('Erfasst' if r['included'] else 'Frei')),note])
    return response

@login_required
def backup_view(request):
    setup(request.user)
    objects=[*Profile.objects.filter(user=request.user),*Schedule.objects.filter(user=request.user),*YearAllowance.objects.filter(user=request.user),*Entry.objects.filter(user=request.user)]
    data={'format':'zeiterfassung-v1','exported_at':date.today().isoformat(),'data':json.loads(serializers.serialize('json',objects))}
    response=HttpResponse(json.dumps(data,ensure_ascii=False,indent=2),content_type='application/json')
    response['Content-Disposition']=f'attachment; filename="zeiterfassung-backup-{date.today()}.json"'
    return response
