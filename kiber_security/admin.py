from django.contrib import admin
from .models import Users, Link, Ball, LinkVisit, UserChannels, Test, UserTest, Question, Answer, UserAnswer, BadWord, GroupId

admin.site.register(Users)
admin.site.register(Link)
admin.site.register(Ball)
admin.site.register(LinkVisit)
admin.site.register(UserChannels)
admin.site.register(BadWord)
admin.site.register(GroupId)



# Javoblarni birlashtirib ko'rsatish uchun InlineModelAdmin
class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 1  # Qo'shimcha javob qatorlarini ko'rsatish (ya'ni yangi javob qo'shish uchun qator)
    fields = ('text', 'is_correct')  # Ko'rsatiladigan maydonlar
    # to'g'ri javobni belgilash uchun `is_correct`ni belgilashni qo'shish mumkin

class QuestionAdmin(admin.ModelAdmin):
    list_display = ('text', 'test')  # Savollarni ko'rsatish
    list_filter = ('test',)  # Testga qarab filtrni qo'llash
    inlines = [AnswerInline]  # Javoblarni savolga inline qo'shish


class UserAnswerInline(admin.TabularInline):
    model = UserAnswer
    extra = 1
class TestAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_at')  # Testni ko'rsatish
    search_fields = ('title',)  # Testni qidirish uchun sarlavhani ishlatish
    inlines = [UserAnswerInline]


# UserTest modeli uchun admin sinfi
class UserTestAdmin(admin.ModelAdmin):
    list_display = ('user', 'test', 'is_completed')
    list_filter = ('is_completed', 'test')
    search_fields = ('user__username', 'test__title')



# Modellarni admin interfeysiga ro'yxatdan o'tkazish
admin.site.register(Test, TestAdmin)
admin.site.register(UserTest, UserTestAdmin)
admin.site.register(Question, QuestionAdmin)
# admin.site.register(Answer)
admin.site.register(UserAnswer)