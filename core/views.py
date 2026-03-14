from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.db import models
from datetime import datetime
import csv
import calendar
from .models import Company, Employee, Attendance, OfficeLocation, Holiday, Absence
from geopy.distance import geodesic
import qrcode
import base64
from io import BytesIO
from django.utils import timezone

def get_payroll_stats(emp, year, month, company):
    _, total_days = calendar.monthrange(year, month)
    
    # Sundays and Holidays
    free_dates = set()
    for day in range(1, total_days + 1):
        if datetime(year, month, day).weekday() == 6: # Sunday only
            free_dates.add(datetime(year, month, day).date())
    
    holidays = Holiday.objects.filter(
        models.Q(company=company) | models.Q(company=None),
        date__year=year, date__month=month
    )
    for h in holidays:
        free_dates.add(h.date)

    # Actual Presence (Valid IN punches)
    # Using python list comprehension to handle DateTimeField -> date conversion reliably
    valid_attendances = Attendance.objects.filter(
        employee=emp, status='Valid', punch_type='IN',
        timestamp__year=year, timestamp__month=month
    )
    valid_dates = set(a.timestamp.date() for a in valid_attendances)
    
    # Paid Leaves
    paid_leave_dates = set(Absence.objects.filter(
        employee=emp, date__year=year, date__month=month, is_paid=True
    ).values_list('date', flat=True))
    
    # Unpaid Absences
    unpaid_absence_dates = set(Absence.objects.filter(
        employee=emp, date__year=year, date__month=month, is_paid=False
    ).values_list('date', flat=True))
    
    # Total Payable Days: (Present OR Holiday/Sunday OR Paid Leave) MINUS Unpaid Absences
    payable_dates = (valid_dates | free_dates | paid_leave_dates) - unpaid_absence_dates
    payable_count = len(payable_dates)
    
    # Breakdown for UI/Slips
    punched_working_days = len(valid_dates - free_dates - unpaid_absence_dates)
    paid_free_days = len(free_dates - unpaid_absence_dates)
    actual_paid_leaves = len(paid_leave_dates - valid_dates - free_dates - unpaid_absence_dates)
    
    salary = (float(emp.monthly_salary) / total_days) * payable_count if total_days > 0 else 0
    
    return {
        'total_days': total_days,
        'days_present': punched_working_days, 
        'free_days': paid_free_days,
        'paid_leaves': actual_paid_leaves,
        'unpaid_absences': total_days - payable_count,
        'payable_days': payable_count,
        'salary': round(salary, 2),
        'original_paid_leave_count': len(paid_leave_dates), # For backward compatibility in some views if needed
        'original_unpaid_absence_count': len(unpaid_absence_dates)
    }

def check_punch_status(request, company_slug, employee_id):
    try:
        company = Company.objects.get(slug=company_slug)
        employee = Employee.objects.get(company=company, employee_id=employee_id)
        
        # Get last valid punch for today
        today = timezone.now().date()
        last_punch = Attendance.objects.filter(
            employee=employee, 
            timestamp__date=today,
            status='Valid'
        ).order_by('-timestamp').first()
        
        if last_punch and last_punch.punch_type == 'IN':
            next_punch = 'OUT'
            message = "Punch Out Required"
        else:
            next_punch = 'IN'
            message = "Punch In Required"
            
        return JsonResponse({
            'success': True,
            'next_punch': next_punch,
            'message': message,
            'employee_name': f"{employee.first_name} {employee.last_name}"
        })
    except (Company.DoesNotExist, Employee.DoesNotExist):
        return JsonResponse({'success': False, 'message': 'Invalid ID'})

def home(request):
    return redirect('mark_attendance_base') # Redirect to general entry or show error

def get_user_company(user):
    if user.is_superuser:
        return Company.objects.first()
    try:
        return user.company
    except Company.DoesNotExist:
        return None

def login_view(request):
    if request.user.is_authenticated:
        return redirect('admin_dashboard')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            # Ensure user has a company assigned
            if not hasattr(user, 'company') and not user.is_superuser:
                logout(request)
                return render(request, 'core/dashboard/login.html', {'form': form, 'error': 'Account not associated with any company.'})
            return redirect('admin_dashboard')
    else:
        form = AuthenticationForm()
    return render(request, 'core/dashboard/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('login')

def show_qr(request):
    # This view is deprecated for simplified universal use.
    return redirect('admin_dashboard')

@login_required
def dashboard_qr(request):
    company = get_user_company(request.user)
    if not company:
        return redirect('logout')
    host = request.get_host()
    scheme = request.scheme
    target_url = f"{scheme}://{host}/mark_attendance/{company.slug}/"
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(target_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    qr_image = base64.b64encode(buffer.getvalue()).decode()
    
    return render(request, 'core/dashboard/show_qr.html', {
        'company': company,
        'qr_image': qr_image, 
        'url': target_url,
        'active_tab': 'show_qr'
    })

def mark_attendance(request, company_slug=None):
    if not company_slug:
        return render(request, 'core/mark_attendance.html', {'error': 'Invalid access. Please scan a company QR code.'})
    
    try:
        company = Company.objects.get(slug=company_slug)
    except Company.DoesNotExist:
        return render(request, 'core/mark_attendance.html', {'error': 'Company not found.'})

    if request.method == 'POST':
        employee_id = request.POST.get('employee_id')
        lat = request.POST.get('latitude')
        lon = request.POST.get('longitude')
        punch_type = request.POST.get('punch_type', 'IN')
        
        if not all([employee_id, lat, lon]):
            return render(request, 'core/mark_attendance.html', {'company': company, 'error': 'Missing required fields or location not provided.'})
        
        try:
            employee = Employee.objects.get(employee_id=employee_id, company=company)
        except Employee.DoesNotExist:
            return render(request, 'core/mark_attendance.html', {'company': company, 'error': f'Employee ID {employee_id} not found.'})
            
        try:
            lat = float(lat)
            lon = float(lon)
        except ValueError:
            return render(request, 'core/mark_attendance.html', {'company': company, 'error': 'Invalid location data.'})
            
        offices = OfficeLocation.objects.filter(company=company)
        if not offices.exists():
            return render(request, 'core/mark_attendance.html', {'company': company, 'error': 'No office locations configured for this company.'})
            
        user_location = (lat, lon)
        valid_office = None
        min_distance = float('inf')
        
        for office in offices:
            office_location = (office.latitude, office.longitude)
            try:
                distance = geodesic(user_location, office_location).meters
                if distance < min_distance:
                    min_distance = distance
                if distance <= office.max_distance_meters:
                    valid_office = office
                    break
            except ValueError:
                continue
        
        if valid_office:
            status = 'Valid'
            msg = f'Attendance marked successfully at {valid_office.name}!'
            msg_type = 'success'
            distance = geodesic(user_location, (valid_office.latitude, valid_office.longitude)).meters
        else:
            status = 'Invalid'
            msg = f'You are too far from office! Closest is {min_distance:.2f}m away.'
            msg_type = 'error'
            distance = min_distance
            
        Attendance.objects.create(
            employee=employee,
            punch_type=punch_type,
            latitude=lat,
            longitude=lon,
            distance_from_office=distance,
            status=status
        )
        
        return render(request, 'core/mark_attendance.html', {'company': company, 'message': msg, 'message_type': msg_type})

    return render(request, 'core/mark_attendance.html', {'company': company})

@login_required
def admin_dashboard(request):
    company = get_user_company(request.user)
    if not company:
        return redirect('logout')
    month_str = request.GET.get('month', datetime.now().strftime('%Y-%m'))
    try:
        year, month = map(int, month_str.split('-'))
    except ValueError:
        year, month = datetime.now().year, datetime.now().month

    _, total_days_in_month = calendar.monthrange(year, month)
    
    free_dates = set()
    for day in range(1, total_days_in_month + 1):
        d = datetime(year, month, day).date()
        if d.weekday() == 6: # Sunday only
            free_dates.add(d)
            
    holidays = Holiday.objects.filter(models.Q(company=company) | models.Q(company=None), date__year=year, date__month=month)
    for h in holidays:
        free_dates.add(h.date)

    employees = Employee.objects.filter(company=company)
    data = []
    
    for emp in employees:
        stats = get_payroll_stats(emp, year, month, company)
        
        data.append({
            'employee': emp,
            'days_present': stats['days_present'] + stats['paid_leaves'], # Showing "Authorized Days" or similar? No, let's stick to breakdown
            'actual_present': stats['days_present'],
            'absences': stats['unpaid_absences'],
            'paid_leaves': stats['paid_leaves'],
            'salary': stats['salary']
        })
        
    return render(request, 'core/dashboard/salary.html', {
        'data': data,
        'current_month': f"{year}-{month:02d}",
        'active_tab': 'salary'
    })

@login_required
def print_salary_slip(request, emp_id, month_str):
    company = get_user_company(request.user)
    if not company:
        return redirect('logout')
    try:
        year, month = map(int, month_str.split('-'))
    except ValueError:
        year, month = datetime.now().year, datetime.now().month

    try:
        emp = Employee.objects.get(employee_id=emp_id, company=company)
    except Employee.DoesNotExist:
        return redirect('dashboard_salary')

    stats = get_payroll_stats(emp, year, month, company)
    month_name = calendar.month_name[month]
    
    context = {
        'employee': emp,
        'company': company,
        'year': year,
        'month': month_str,
        'month_name': month_name,
        'total_days_in_month': stats['total_days'],
        'days_present': stats['days_present'],
        'free_days': stats['free_days'],
        'paid_leaves': stats['paid_leaves'],
        'payable_days': stats['payable_days'],
        'absent_days': stats['unpaid_absences'],
        'salary': stats['salary'],
    }
    
    return render(request, 'core/dashboard/salary_slip.html', context)

@login_required
def dashboard_redirect(request):
    return redirect('dashboard_employees')

@login_required
def dashboard_employees(request):
    company = get_user_company(request.user)
    if not company:
        return redirect('logout')
    employees = Employee.objects.filter(company=company)
    first_employee = employees.first()
    return render(request, 'core/dashboard/employees.html', {'company': company, 'employees': employees, 'first_employee': first_employee, 'active_tab': 'employees'})

@login_required
def dashboard_attendance(request):
    company = get_user_company(request.user)
    if not company:
        return redirect('logout')
    attendances = Attendance.objects.filter(employee__company=company).select_related('employee').all().order_by('-timestamp')[:50]
    return render(request, 'core/dashboard/attendance.html', {'attendances': attendances, 'active_tab': 'attendance'})

@login_required
def dashboard_location(request):
    company = get_user_company(request.user)
    if not company:
        return redirect('logout')
    offices = OfficeLocation.objects.filter(company=company)
    return render(request, 'core/dashboard/location.html', {'offices': offices, 'active_tab': 'location'})

@login_required
def dashboard_add_location(request):
    company = get_user_company(request.user)
    if not company:
        return redirect('logout')
    if request.method == 'POST':
        name = request.POST.get('name')
        lat = request.POST.get('latitude')
        lon = request.POST.get('longitude')
        dist = request.POST.get('max_distance_meters')
        
        if name and lat and lon and dist:
            OfficeLocation.objects.create(
                company=company,
                name=name,
                latitude=float(lat),
                longitude=float(lon),
                max_distance_meters=int(dist)
            )
            return redirect('dashboard_location')
    return render(request, 'core/dashboard/add_location.html', {'active_tab': 'location'})

@login_required
def dashboard_add_employee(request):
    company = get_user_company(request.user)
    if not company:
        return redirect('logout')
    if request.method == 'POST':
        emp_id = request.POST.get('employee_id')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone_number')
        wage = request.POST.get('monthly_salary')
        designation = request.POST.get('designation', 'Employee')
        
        if emp_id and first_name and last_name and email and wage:
            Employee.objects.create(
                company=company,
                employee_id=emp_id,
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone_number=phone,
                monthly_salary=wage,
                designation=designation
            )
            return redirect('dashboard_employees')
    return render(request, 'core/dashboard/add_employee.html', {'active_tab': 'employees'})

@login_required
def dashboard_mark_absence(request):
    company = get_user_company(request.user)
    if not company:
        return redirect('logout')
    
    if request.method == 'POST':
        emp_id = request.POST.get('employee_id')
        dates_str = request.POST.get('dates') # Expecting comma separated or list
        is_paid = request.POST.get('is_paid') == 'true'
        reason = request.POST.get('reason', '')
        
        try:
            emp = Employee.objects.get(employee_id=emp_id, company=company)
            date_list = dates_str.split(',')
            for date_str in date_list:
                date = datetime.strptime(date_str.strip(), '%Y-%m-%d').date()
                Absence.objects.update_or_create(
                    employee=emp,
                    date=date,
                    defaults={'reason': reason, 'is_paid': is_paid}
                )
            return JsonResponse({'success': True, 'message': 'Absence(s) marked successfully.'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
            
    return JsonResponse({'success': False, 'message': 'Invalid request'})

@login_required
def export_attendance(request):
    company = get_user_company(request.user)
    if not company:
        return HttpResponse('Unauthorized', status=401)
    month_str = request.GET.get('month', datetime.now().strftime('%Y-%m'))
    try:
        year, month = map(int, month_str.split('-'))
    except ValueError:
        year, month = datetime.now().year, datetime.now().month

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{company.slug}_attendance_{year}_{month:02d}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Employee ID', 'Name', 'Designation', 'Email', 'Days Present', 'Paid Leaves', 'Unpaid Absences', 'Monthly Base', 'Calculated Salary'])
    
    employees = Employee.objects.filter(company=company)
    for emp in employees:
        stats = get_payroll_stats(emp, year, month, company)
        
        writer.writerow([
            emp.employee_id,
            f"{emp.first_name} {emp.last_name}",
            emp.designation,
            emp.email,
            stats['days_present'],
            stats['paid_leaves'],
            stats['unpaid_absences'],
            emp.monthly_salary,
            stats['salary']
        ])
    return response
