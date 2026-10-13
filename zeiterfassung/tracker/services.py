from datetime import date, timedelta
from decimal import Decimal
from .models import Profile, Schedule, Entry, YearAllowance

def setup(user):
    profile,_=Profile.objects.get_or_create(user=user)
    if not Schedule.objects.filter(user=user).exists():
        Schedule.objects.create(user=user,effective_from=profile.start_date)
    return profile

def minutes(t): return t.hour*60+t.minute

def worked(entry):
    if not entry: return 0
    pairs=[(entry.start,entry.break_start),(entry.break_end,entry.end)]
    return sum(minutes(b)-minutes(a) for a,b in pairs if a is not None and b is not None)

def incomplete(entry):
    if not entry: return False
    return any((a is None)!=(b is None) for a,b in [(entry.start,entry.break_start),(entry.break_end,entry.end)])

def dates(start,end):
    while start<=end:
        yield start
        start+=timedelta(days=1)

def duration(n, signed=False):
    sign='−' if n<0 else ('+' if signed else '')
    n=abs(int(n))
    return f'{sign}{n//60}:{n%60:02d}'

class Ledger:
    def __init__(self,user,today=None):
        self.profile=setup(user)
        self.today=today or date.today()
        self.schedules=list(Schedule.objects.filter(user=user))
        self.entries={e.date:e for e in Entry.objects.filter(user=user)}
        self.allowances={a.year:a for a in YearAllowance.objects.filter(user=user)}
    def planned(self,day):
        if day<self.profile.start_date: return 0
        schedule=next((s for s in reversed(self.schedules) if s.effective_from<=day),None)
        return schedule.daily_minutes if schedule and day.weekday() in schedule.weekdays else 0
    def row(self,day):
        entry=self.entries.get(day)
        target=(entry.target_override if entry and entry.target_override is not None else self.planned(day)) if day>=self.profile.start_date else 0
        actual=worked(entry)
        credited=0
        vacation=Decimal('0')
        if entry and entry.kind in ('vacation','sick','holiday'):
            credited=round(Decimal(target)*entry.fraction)
            if entry.kind=='vacation' and target>0: vacation=entry.fraction
        if entry and entry.kind=='unpaid':
            target-=round(Decimal(target)*entry.fraction)
        partial=incomplete(entry)
        # Ein fehlender oder unvollständiger Eintrag ist offen, keine erfundene Arbeitszeit.
        closed=bool(entry and not partial and (entry.finalized or (entry.kind!='work' and entry.fraction==1) or all([entry.start,entry.break_start,entry.break_end,entry.end])))
        future=day>self.today
        active=day>=self.profile.start_date
        delta=actual+credited-target
        included=closed and not future and active
        pending=active and not future and not closed and (target>0 or bool(entry and (actual or partial)))
        return {'date':day,'entry':entry,'target':target,'actual':actual,'credit':credited,'delta':delta if included else None,'included':included,'pending':pending,'future':future,'vacation':vacation,'closed':closed,'partial':partial}
    def totals(self,start,end):
        rows=[self.row(d) for d in dates(start,end)]
        return {'target':sum(r['target'] for r in rows),'actual':sum(r['actual'] for r in rows if r['included']),'credit':sum(r['credit'] for r in rows if r['included']),'delta':sum(r['delta'] for r in rows if r['included']),'pending':sum(r['pending'] for r in rows)}
    def balance(self):
        return self.profile.opening_minutes+self.totals(self.profile.start_date,self.today)['delta']
    def vacation(self,year):
        used=Decimal('0'); planned=Decimal('0')
        for day,entry in self.entries.items():
            if day.year==year:
                r=self.row(day)
                if day>self.today: planned+=r['vacation']
                else: used+=r['vacation']
        allowance=self.allowances.get(year)
        total=allowance.days+allowance.carry if allowance else None
        return {'allowance':allowance,'total':total,'used':used,'planned':planned,'remaining':total-used-planned if total is not None else None}
