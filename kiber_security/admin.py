from django.contrib import admin
from .models import Users, Link, Ball, LinkVisit

admin.site.register(Users)
admin.site.register(Link)
admin.site.register(Ball)
admin.site.register(LinkVisit)
