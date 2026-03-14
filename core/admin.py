from django.contrib import admin
from .models import Company, OfficeLocation, Employee, Attendance, Holiday

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'admin_user', 'created_at')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(OfficeLocation)
class OfficeLocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'latitude', 'longitude', 'max_distance_meters')
    list_filter = ('company',)

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('employee_id', 'first_name', 'last_name', 'email', 'company', 'monthly_salary')
    list_filter = ('company',)
    search_fields = ('employee_id', 'first_name', 'last_name', 'email', 'company__name')

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('employee', 'company_name', 'timestamp', 'punch_type', 'status', 'distance_from_office')
    list_filter = ('punch_type', 'status', 'timestamp', 'employee__company')
    search_fields = ('employee__employee_id', 'employee__first_name', 'employee__last_name', 'employee__company__name')

    def company_name(self, obj):
        return obj.employee.company.name
    company_name.short_description = 'Company'

@admin.register(Holiday)
class HolidayAdmin(admin.ModelAdmin):
    list_display = ('name', 'date', 'company')
    list_filter = ('company',)
    search_fields = ('name',)
