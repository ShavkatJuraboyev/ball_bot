from django.shortcuts import render, get_object_or_404, redirect
from kiber_security.models import Users, Link, Ball, LinkVisit, Test, UserTest, UserAnswer, Answer, Question
from django.views.decorators.csrf import csrf_exempt
from urllib.parse import parse_qs
import json
from django.http import JsonResponse, HttpResponse
from django.utils import timezone

def index(request):
    telegram_id = request.session.get('telegram_id')
    ball = None
    try:
        ball = Ball.objects.get(user__telegram_id=telegram_id)
    except Ball.DoesNotExist:
        ball = None 
        
    context = {'ball':ball, 'segment': 'index',}
    return render(request, 'users/index.html', context)

def get_referral_link(user):
    base_url = "https://t.me/samcyber102_bot?start="  # Botning haqiqiy username
    referral_link = f"{base_url}{user.referral_code}"
    return referral_link

def friends(request):
    telegram_id = request.session.get('telegram_id')
    user = Users.objects.filter(telegram_id=telegram_id).first()

    referral_link = get_referral_link(user) if user else None 
    referrals = Users.objects.filter(referred_by=user) if user else []
    Users.objects.filter(referred_by=user) if user else []
    referred_by = user.referred_by.first_name if user and user.referred_by else None
    context = {'referral_link': referral_link, 'referrals': referrals, 'referred_by': referred_by, 'segment': 'friends',}
    return render(request, 'users/friends.html', context)

def share(request): 
    telegram_id = request.session.get('telegram_id')
    if telegram_id:
        user = get_object_or_404(Users, telegram_id=telegram_id)
    youtube_links = Link.objects.filter(link_type='youtube')
    telegram_links = Link.objects.filter(link_type='telegram')
    instagram_links = Link.objects.filter(link_type='instagram')
    
    context = {
        'youtube_links': youtube_links,
        'telegram_links': telegram_links,
        'instagram_links': instagram_links,
        'user': user,
        'segment': 'share',
    }
    return render(request, 'users/share.html', context)


def add_link_ball(request, link_id, telegram_id):
    print(telegram_id)
    
    if telegram_id:
        try:
            # Foydalanuvchini bazadan olish
            user = get_object_or_404(Users, telegram_id=telegram_id)
            
            # Linkni olish
            link = get_object_or_404(Link, id=link_id)
            
            # Linkni foydalanuvchi birinchi marta ko'rayotganini tekshirish
            if not LinkVisit.objects.filter(user=user, link=link).exists():
                # Linkni foydalanuvchi tomonidan ko'rildi deb belgilash
                LinkVisit.objects.create(user=user, link=link)
 
                # Foydalanuvchi uchun ballni olish yoki yaratish
                ball, created = Ball.objects.get_or_create(user=user)
                
                # Ballarni qo'shish
                ball.add_ball(link.link_type, link.ball)
                
                # Ballni saqlash
                ball.save()

            else:
                print(f"Foydalanuvchi {user} allaqachon {link} linkiga kirgan.")
                # Agar foydalanuvchi allaqachon kirgan bo'lsa, ball berilmaydi.

            # Linkga yo'naltirish
            return redirect(link.url)
        
        except Exception as e:
            # Xatolik bo'lsa, konsolga chiqarish va foydalanuvchiga xabar berish
            print(f"Xatolik: {str(e)}")
            return HttpResponse(f"Xatolik yuz berdi: {str(e)}")
    
    else:
        # Agar telegram_id bo'lmasa, xato javob yuboring
        return HttpResponse("Telegram ID topilmadi. Iltimos, tizimga kiring.")
    

def style(request):
    telegram_id = request.session.get('telegram_id')
    
    ball = None
    # `telegram_id` mavjud bo'lsa, faqatgina unda `Ball` obyektini qidiramiz
    if telegram_id:
        ball = Ball.objects.filter(user__telegram_id=telegram_id).first()

    context = {'ball': ball, 'segment': 'style',}
    return render(request, 'users/style.html', context)


def style2(request):
    return render(request, 'users/style2.html')


@csrf_exempt
def verify_user(request):
    if request.method == 'POST':
        # So'rovdan kelgan ma'lumotni o'qiymiz
        data = json.loads(request.body)
        init_data_encoded = data.get('initData')
        
        # initData ni URL kodlangan matndan dictionary ga aylantiramiz
        if init_data_encoded:
            parsed_data = parse_qs(init_data_encoded)
            user_data_json = parsed_data.get('user', [None])[0]
            
            if user_data_json:
                try:
                    # JSON formatidagi `user_data_json` ni JSON obyektiga aylantiramiz
                    user_data = json.loads(user_data_json)
                    telegram_id = user_data.get('id')
                    if telegram_id:
                        # Telegram ID ni sessiyaga saqlaymiz
                        request.session['telegram_id'] = telegram_id
                    # Bazadan foydalanuvchini qidiramiz yoki topilmasa, xato qaytaramiz
                    try:
                        user = Users.objects.get(telegram_id=telegram_id)
                        return JsonResponse({
                            "first_name": user.first_name,
                            "last_name": user.last_name,
                            "username": user.username_link 
                        })
                    except Users.DoesNotExist:
                        return JsonResponse({"error": "Foydalanuvchi topilmadi"}, status=404)
                except json.JSONDecodeError:
                    return JsonResponse({"error": "user malumotlari noto'g'ri formatda"}, status=400)
            else:
                return JsonResponse({"error": "user ma'lumotlari topilmadi"}, status=400)
        else:
            return JsonResponse({"error": "initData mavjud emas"}, status=400)

    return JsonResponse({"error": "Notog'ri so'rov"}, status=400)


def test_list(request):
    telegram_id = request.session.get('telegram_id')
    ball = None
    try:
        ball = Ball.objects.get(user__telegram_id=telegram_id)
    except Ball.DoesNotExist:
        ball = None 
    user = Users.objects.filter(telegram_id=telegram_id).first()    
    tests = Test.objects.all()
    # Foydalanuvchi testni tugatgan bo'lsa, testlarni faqat ko'rsatish
    completed_tests = UserTest.objects.filter(user=user, is_completed=True).values_list('test_id', flat=True)
    # Foydalanuvchi tugatgan testlardan ajratilgan testlar
    available_tests = tests.exclude(id__in=completed_tests)
    return render(request, 'users/test_list.html', {'tests': tests, 'completed_tests': completed_tests, 'ball':ball})




def test_detail(request, test_id):
    telegram_id = request.session.get('telegram_id')
    ball = None
    try:
        ball = Ball.objects.get(user__telegram_id=telegram_id)
    except Ball.DoesNotExist:
        ball = None 
    user = Users.objects.filter(telegram_id=telegram_id).first()
    test = get_object_or_404(Test, id=test_id)
    # Foydalanuvchi uchun UserTestni olish yoki yaratish
    user_test, created = UserTest.objects.get_or_create(test=test, user=user)
    # Agar test tugatilgan bo'lsa, qayta ishlashga ruxsat bermaslik
    if user_test.is_completed:
        return redirect('test_result', test_id=test_id)
    questions = test.questions.all()  # Testga tegishli savollarni olish
    if request.method == "POST":
        for question in questions:
            selected_answer_id = request.POST.get(f'question_{question.id}')
            if selected_answer_id:
                selected_answer = get_object_or_404(Answer, id=selected_answer_id)
                # Javobni saqlash uchun UserAnswer modeli yaratish yoki yangilash
                UserAnswer.objects.update_or_create(
                    user=user,
                    question=question,
                    test=test,
                    defaults={
                        'selected_answer': selected_answer,
                        'is_correct': selected_answer.is_correct
                    }
                )
        # UserTestni yangilash: foydalanuvchi testni yakunladi
        user_test.is_completed = True
        user_test.save()
        return redirect('test_result', test_id=test_id)
    return render(request, 'users/start.html', {'test': test, 'questions': questions, 'ball':ball})


def test_result(request, test_id):
    telegram_id = request.session.get('telegram_id')
    ball = None
    try:
        ball = Ball.objects.get(user__telegram_id=telegram_id)
    except Ball.DoesNotExist:
        ball = None 
    user = Users.objects.filter(telegram_id=telegram_id).first()
    test = get_object_or_404(Test, id=test_id)

    # Foydalanuvchi uchun UserTestni olish
    user_test, created = UserTest.objects.get_or_create(test=test, user=user)
    user_answers = UserAnswer.objects.filter(test=test, user=user)
    # Ballarni hisoblash
    score = 0
    for answer in user_answers:
        if answer.selected_answer.is_correct:
            score += 1
            answer.is_correct = True
        else:
            answer.is_correct = False
        answer.save()  # Yangi is_correct qiymatini saqlash
    
    user_test.score = score
    user_test.is_completed = True  # Testni tugagan deb belgilash
    user_test.save()

    return render(request, 'users/test_result.html', {
        'user_test': user_test,
        'user_answers': user_answers,
        'score': score,
        'ball':ball
    })