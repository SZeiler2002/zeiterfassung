from django.contrib import admin
from django.urls import path, include
from tracker import views
urlpatterns = [path('admin/',admin.site.urls),path('accounts/',include('django.contrib.auth.urls')),path('',views.calendar_view,name='calendar'),path('day/<str:day>/',views.day_view,name='day'),path('settings/',views.settings_view,name='settings'),path('move/',views.move_view,name='move'),path('absence/',views.absence_view,name='absence'),path('year/',views.year_view,name='year'),path('export/',views.export_view,name='export'),path('backup/',views.backup_view,name='backup')]
