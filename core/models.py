from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify

class Company(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    admin_user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='company')
    emp_id_prefix = models.CharField(max_length=10, default="EMP")
    next_serial = models.IntegerField(default=1)
    serial_padding = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class OfficeLocation(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='locations')
    name = models.CharField(max_length=100, default="Main Office")
    latitude = models.FloatField()
    longitude = models.FloatField()
    max_distance_meters = models.IntegerField(default=100)

    def __str__(self):
        return self.name

class Employee(models.Model):
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='employee_profile')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='employees')
    employee_id = models.CharField(max_length=50)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField()
    phone_number = models.CharField(max_length=20, blank=True)
    designation = models.CharField(max_length=100, default="Employee")
    monthly_salary = models.DecimalField(max_digits=10, decimal_places=2, default=30000.00)
    
    # New Shift Tracking Fields
    shift_start = models.TimeField(default="09:00:00")
    shift_end = models.TimeField(default="18:00:00")
    
    class Meta:
        unique_together = ('company', 'employee_id')

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.employee_id}) - {self.company.name}"

class Attendance(models.Model):
    STATUS_CHOICES = [
        ('Valid', 'Valid'),
        ('Manual', 'Manual (Admin Override)'),
        ('Invalid', 'Invalid (Out of range)'),
    ]
    PUNCH_CHOICES = [
        ('IN', 'Punch In'),
        ('OUT', 'Punch Out'),
    ]
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    punch_type = models.CharField(max_length=3, choices=PUNCH_CHOICES, default='IN')
    latitude = models.FloatField()
    longitude = models.FloatField()
    distance_from_office = models.FloatField(help_text="Distance in meters", null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    
    # New Analytics Fields
    is_late = models.BooleanField(default=False)
    work_duration_minutes = models.IntegerField(null=True, blank=True, help_text="Duration between IN and OUT in minutes")

    def __str__(self):
        return f"{self.employee.employee_id} - {self.timestamp.date()} - {self.punch_type} - {self.status}"

class Holiday(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='holidays', null=True, blank=True) # null for global holidays
    name = models.CharField(max_length=100)
    date = models.DateField()

    class Meta:
        unique_together = ('company', 'date')

    def __str__(self):
        return f"{self.name} - {self.date}"

class Absence(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='absences')
    date = models.DateField()
    is_paid = models.BooleanField(default=False)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('employee', 'date')

    def __str__(self):
        return f"{self.employee.employee_id} - {self.date} - Absent"
