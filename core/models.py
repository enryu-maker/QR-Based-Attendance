from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.utils import timezone

class Company(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    admin_user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='company')
    emp_id_prefix = models.CharField(max_length=10, default="EMP")
    next_serial = models.IntegerField(default=1)
    serial_padding = models.IntegerField(default=1)
    
    # SMTP Settings
    smtp_host = models.CharField(max_length=100, blank=True, null=True)
    smtp_port = models.IntegerField(default=587)
    smtp_user = models.CharField(max_length=100, blank=True, null=True)
    smtp_password = models.CharField(max_length=255, blank=True, null=True)
    smtp_use_tls = models.BooleanField(default=True)
    smtp_use_ssl = models.BooleanField(default=False)
    smtp_from_email = models.EmailField(blank=True, null=True)
    
    # Localization
    currency_symbol = models.CharField(max_length=5, default="₹")
    
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
    
    # Advanced Payroll Fields
    joining_date = models.DateField(default=timezone.now)
    hra = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="House Rent Allowance")
    travel_allowance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    special_allowance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    pf_deduction = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Provident Fund Deduction")
    esi_deduction = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="ESI Deduction")
    professional_tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Shift Tracking Fields
    shift_start = models.TimeField(default="09:00:00")
    shift_end = models.TimeField(default="18:00:00")
    
    class Meta:
        unique_together = ('company', 'employee_id')

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.employee_id}) - {self.company.name}"

class EmployeeDocument(models.Model):
    DOC_TYPES = [
        ('ID', 'Government ID'),
        ('Address', 'Address Proof'),
        ('Education', 'Education Certificate'),
        ('Contract', 'Signed Contract'),
        ('Other', 'Other Document'),
    ]
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='documents')
    name = models.CharField(max_length=100)
    doc_type = models.CharField(max_length=20, choices=DOC_TYPES, default='Other')
    file = models.FileField(upload_to='employee_docs/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.employee.first_name} - {self.name}"

class SalaryAdvance(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending Review'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
        ('Paid', 'Disbursed'),
    ]
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='advances')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    requested_at = models.DateTimeField(auto_now_add=True)

class Reimbursement(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
        ('Paid', 'Paid'),
    ]
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='reimbursements')
    title = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    receipt = models.FileField(upload_to='receipts/', null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

class Asset(models.Model):
    STATUS_CHOICES = [
        ('Available', 'Available'),
        ('Assigned', 'In Use'),
        ('Maintenance', 'Maintenance'),
        ('Lost', 'Lost/Damaged'),
    ]
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='assets')
    name = models.CharField(max_length=100)
    asset_id = models.CharField(max_length=50)
    assigned_to = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name='assets')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Available')
    purchase_date = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = ('company', 'asset_id')

    def __str__(self):
        return f"{self.name} ({self.asset_id})"

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
    STATUS_CHOICES = [
        ('Pending', 'Pending Approval'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    ]
    LEAVE_TYPE_CHOICES = [
        ('Sick', 'Sick Leave'),
        ('Casual', 'Casual Leave'),
        ('Planned', 'Planned/Vacation'),
        ('Other', 'Other'),
    ]
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='absences')
    date = models.DateField()
    is_paid = models.BooleanField(default=False)
    is_half_day = models.BooleanField(default=False)
    leave_type = models.CharField(max_length=20, choices=LEAVE_TYPE_CHOICES, default='Planned')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Approved') # Default to Approved for legacy admin entries
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('employee', 'date')

    def __str__(self):
        return f"{self.employee.employee_id} - {self.date} - {self.status}"
