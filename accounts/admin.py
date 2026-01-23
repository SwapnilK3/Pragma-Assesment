from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from accounts.models import User, UserRole


class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'first_name', 'last_name', 'role', 'is_staff', 'is_superuser', 'is_active')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('-created_at',)
    list_filter = ('role', 'is_staff', 'is_superuser', 'is_active', 'is_loyalty_member')
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'date_of_birth', 'gender')}),
        ('Role & Permissions', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'is_loyalty_member')}),
        ('Groups', {'fields': ('groups', 'user_permissions')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'role', 'password1', 'password2'),
        }),
    )

    def save_model(self, request, obj, form, change):
        # Sync is_staff based on role
        if obj.role in [UserRole.STAFF, UserRole.ADMIN]:
            obj.is_staff = True
        if obj.role == UserRole.ADMIN:
            obj.is_superuser = True
        super().save_model(request, obj, form, change)


admin.site.register(User, UserAdmin)