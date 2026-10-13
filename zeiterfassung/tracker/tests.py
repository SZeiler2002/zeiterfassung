from datetime import date, time
from decimal import Decimal
import json
import tempfile
from pathlib import Path
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from .models import Profile, Schedule, Entry, YearAllowance
from .services import Ledger
from .forms import EntryForm

class TimeTests(TestCase):
    def setUp(self):
        self.user=get_user_model().objects.create_user('stefan',password='testing-password')
        Profile.objects.create(user=self.user,start_date=date(2026,1,1),opening_minutes=120)
        Schedule.objects.create(user=self.user,effective_from=date(2026,1,1))
        self.client.force_login(self.user)
    def ledger(self,today=date(2026,10,20)): return Ledger(self.user,today)
    def work(self,d=date(2026,10,15),**kw):
        values=dict(start=time(7),break_start=time(12),break_end=time(13),end=time(16,50));values.update(kw)
        return Entry.objects.create(user=self.user,date=d,**values)
    def test_four_stamps_and_break(self):
        self.work(); r=self.ledger().row(date(2026,10,15))
        self.assertEqual((r['actual'],r['target'],r['delta']),(530,520,10))
    def test_week_month_opening_balance(self):
        self.work();self.work(date(2026,10,16),end=time(16,20))
        ledger=self.ledger()
        self.assertEqual(ledger.totals(date(2026,10,12),date(2026,10,18))['delta'],-10)
        self.assertEqual(ledger.totals(date(2026,10,1),date(2026,10,31))['delta'],-10)
        self.assertEqual(ledger.balance(),110)
    def test_future_not_counted_and_missing_is_open(self):
        self.work(date(2026,10,22));l=self.ledger()
        self.assertIsNone(l.row(date(2026,10,22))['delta'])
        self.assertTrue(l.row(date(2026,10,15))['pending'])
        self.assertEqual(l.balance(),120)
    def test_incomplete_is_excluded(self):
        self.work(end=None)
        r=self.ledger().row(date(2026,10,15))
        self.assertTrue(r['partial']);self.assertTrue(r['pending']);self.assertIsNone(r['delta'])
    def test_closed_empty_day_negative(self):
        Entry.objects.create(user=self.user,date=date(2026,10,15),finalized=True)
        self.assertEqual(self.ledger().row(date(2026,10,15))['delta'],-520)
    def test_half_work_with_half_vacation(self):
        Entry.objects.create(user=self.user,date=date(2026,10,15),kind='vacation',fraction=Decimal('0.5'),start=time(7),break_start=time(11,20),finalized=True)
        r=self.ledger().row(date(2026,10,15))
        self.assertEqual((r['actual'],r['credit'],r['delta']),(260,260,0))
        self.assertEqual(r['vacation'],Decimal('0.5'))
    def test_full_vacation_and_remaining(self):
        YearAllowance.objects.create(user=self.user,year=2026,days=10,carry=1)
        Entry.objects.create(user=self.user,date=date(2026,10,15),kind='vacation')
        Entry.objects.create(user=self.user,date=date(2026,10,22),kind='vacation')
        Entry.objects.create(user=self.user,date=date(2026,10,17),kind='vacation')
        ledger=self.ledger();v=ledger.vacation(2026)
        self.assertEqual((v['used'],v['planned'],v['remaining']),(1,1,9))
        self.assertEqual(ledger.row(date(2026,10,15))['delta'],0)
    def test_sick_holiday_comp_and_unpaid(self):
        day=date(2026,10,15)
        e=Entry.objects.create(user=self.user,date=day,kind='sick')
        for kind,expected in [('sick',0),('holiday',0),('comp',-520),('unpaid',0)]:
            e.kind=kind;e.save()
            self.assertEqual(self.ledger().row(day)['delta'],expected)
    def test_move_keeps_weekly_target(self):
        response=self.client.post('/move/',{'source':'2026-10-15','destination':'2026-10-14'})
        self.assertEqual(response.status_code,302)
        l=self.ledger(); self.assertEqual(l.row(date(2026,10,15))['target'],0)
        self.assertEqual(l.row(date(2026,10,14))['target'],520)
        self.assertEqual(l.totals(date(2026,10,12),date(2026,10,18))['target'],1040)
    def test_move_rejects_occupied_destination(self):
        self.work(date(2026,10,14))
        self.client.post('/move/',{'source':'2026-10-15','destination':'2026-10-14'})
        self.assertEqual(self.ledger().row(date(2026,10,15))['target'],520)
    def test_historical_schedule(self):
        Schedule.objects.create(user=self.user,effective_from=date(2026,11,1),weekdays=[0,1],daily_minutes=480)
        l=self.ledger()
        self.assertEqual(l.planned(date(2026,10,15)),520)
        self.assertEqual(l.planned(date(2026,11,5)),0)
        self.assertEqual(l.planned(date(2026,11,2)),480)
    def test_absence_range_only_workdays(self):
        self.client.post('/absence/',{'start':'2026-10-12','end':'2026-10-18','kind':'vacation','fraction':'1'})
        self.assertEqual(Entry.objects.filter(user=self.user,kind='vacation').count(),2)
    def test_absence_range_does_not_overwrite(self):
        self.work()
        self.client.post('/absence/',{'start':'2026-10-12','end':'2026-10-18','kind':'vacation','fraction':'1'})
        self.assertEqual(Entry.objects.filter(user=self.user,kind='vacation').count(),0)
    def test_stamp_validation(self):
        for data in [dict(start='12:00',break_start='07:00'),dict(start='07:00',finalized='on'),dict(kind='vacation',start='07:00',break_start='12:00')]:
            form=EntryForm(data={'kind':'work','fraction':'1',**data})
            self.assertFalse(form.is_valid())
        self.assertTrue(EntryForm(data={'kind':'work','fraction':'1','start':'07:00','break_start':'11:20','finalized':'on'}).is_valid())
    def test_cross_year_iso_week(self):
        l=self.ledger(date(2027,1,5))
        self.assertEqual(l.totals(date(2026,12,28),date(2027,1,3))['target'],1040)
        self.assertEqual(l.totals(date(2027,1,1),date(2027,1,31))['target'],9*520)
    def test_views_and_exports(self):
        self.work(note='=HYPERLINK("bad")')
        for path in ['/?month=2026-10','/settings/','/day/2026-10-15/','/move/','/absence/','/year/?year=2026','/export/?month=2026-10','/backup/']:
            response=self.client.get(path)
            self.assertEqual(response.status_code,200,path)
        self.assertIn("'=HYPERLINK",self.client.get('/export/?month=2026-10').content.decode('utf-8-sig'))
    def test_ownership_and_login(self):
        self.work(note='PRIVATE NOTE')
        other=get_user_model().objects.create_user('other',password='testing-password')
        self.client.force_login(other)
        self.assertNotContains(self.client.get('/day/2026-10-15/'),'PRIVATE NOTE')
        self.assertNotIn('PRIVATE NOTE',self.client.get('/backup/').content.decode())
        self.client.post('/day/2026-10-15/',{'action':'delete'})
        self.assertEqual(Entry.objects.filter(user=self.user).count(),1)
        self.client.logout();self.assertEqual(self.client.get('/').status_code,302)
    def test_csrf_required(self):
        client=Client(enforce_csrf_checks=True);client.force_login(self.user)
        self.assertEqual(client.post('/day/2026-10-15/',{'action':'delete'}).status_code,403)
    def test_backup_roundtrip_and_reject_invalid(self):
        self.work(); data=self.client.get('/backup/').content
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'backup.json';path.write_bytes(data)
            call_command('restore_timebackup',str(path),username='stefan',replace=True,verbosity=0)
            self.assertEqual(self.ledger().row(date(2026,10,15))['delta'],10)
            bad=json.loads(data);bad['data'][-1]['fields']['end']='06:00'
            path.write_text(json.dumps(bad))
            with self.assertRaises(CommandError):call_command('restore_timebackup',str(path),username='stefan',replace=True,verbosity=0)
            self.assertEqual(self.ledger().row(date(2026,10,15))['delta'],10)
