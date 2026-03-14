from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('mark_attendance/', views.mark_attendance, name='mark_attendance_base'),
    path('mark_attendance/<slug:company_slug>/', views.mark_attendance, name='mark_attendance'),
    path('dashboard/', views.dashboard_redirect, name='admin_dashboard'),
    path('dashboard/qr/', views.dashboard_qr, name='dashboard_qr'),
    path('dashboard/employees/', views.dashboard_employees, name='dashboard_employees'),
    path('dashboard/employees/add/', views.dashboard_add_employee, name='dashboard_add_employee'),
    path('dashboard/attendance/', views.dashboard_attendance, name='dashboard_attendance'),
    path('dashboard/salary/', views.admin_dashboard, name='dashboard_salary'),
    path('dashboard/salary/print/<str:emp_id>/<str:month_str>/', views.print_salary_slip, name='print_salary_slip'),
    path('dashboard/location/', views.dashboard_location, name='dashboard_location'),
    path('dashboard/location/add/', views.dashboard_add_location, name='dashboard_add_location'),
    path('export_attendance/', views.export_attendance, name='export_attendance'),
    path('check_punch_status/<slug:company_slug>/<str:employee_id>/', views.check_punch_status, name='check_punch_status'),
]
