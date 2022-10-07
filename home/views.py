from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from operator import attrgetter
from home.models import *
from teacher.models import categories, subcategories, Courses, Sections, VideoUploads
from student.models import student_register_courses, course_comments, student_cart_courses, student_favourite_courses, \
    payment
from discount.models import discount
from teacher.views import getAllCourseList, get_courseDetails, getLanguage, getPaidCourseList, getFreeCourseList
from django.template.loader import render_to_string
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
# import json
import os, sys, shutil
import traceback
import uuid
import datetime
import hashlib
from django.http import HttpResponse, HttpResponseRedirect
from django.core.mail import get_connection, EmailMultiAlternatives
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import Group
from django.conf import settings
import os, shutil
from datetime import datetime, date
from datetime import timedelta
import pytz
from textblob import TextBlob
from django.core.wsgi import get_wsgi_application
import json
from django.conf.urls.static import static
from builtins import str as _str

import logging

# from moviepy.editor import VideoFileClip
import os
from django.core.mail import send_mail
import smtplib, ssl

from django.db.models import Q

from django.core import serializers
# from django.utils.translation import LANGUAGE_SESSION_KEY
import subprocess
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw
from django.conf import settings
import img2pdf
from django.contrib.sessions.models import Session

## For paypal

from django.contrib import messages
from django.conf import settings
from decimal import Decimal
from paypal.standard.forms import PayPalPaymentsForm
import random, string
from django.utils.translation import LANGUAGE_SESSION_KEY
from django.utils import translation
import re

os.environ['DJANGO_SETTINGS_MODULE'] = 'booctop.settings'
application = get_wsgi_application()


# def forgetme(request):
#     if request.method == 'POST':
#         return password_reset(request, from_email=request.POST.get('email'))
#         # return render(request, 'signup.html')
#     else:
#         return redirect('/')

def set_language_from_url(request, user_language):
    translation.activate(user_language)
    request.session[translation.LANGUAGE_SESSION_KEY] = user_language
    return redirect('/')


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split('.')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


# def view_404(request, *args, **kwargs):
# 	return redirect('404.html')


def home_view(request):
    # Getting the host name and port and saving them into db for admin panel
    host_url = request.build_absolute_uri()[:-4]
    options = Option.objects.filter(oname="main_host")
    if options.count() == 0:
        option = Option(oname="main_host", oval=host_url)
    else:
        option = options[0]
        option.oval = host_url

    option.save()

    # Session.objects.all().delete()
    ip = get_client_ip(request)
    if request.session.get(ip) == None:
        request.session[ip] = 'ar' + '-' + 'light'

    # for users logged in with social
    if request.user.is_authenticated and request.session.get("user_id") == None:
        request.session['user_id'] = str(request.user.id)
        request.session['user_type'] = request.user.group.name
    user_id = request.session.get("user_id")
    user_type = request.session.get("user_type")

    type = request.POST.get('type')
    page = request.POST.get('page')
    order = request.POST.get('order')

    if type == '' or type == None:
        type = -1
    else:
        type = int(type)

    if page == '' or page == None:
        page = 1
    else:
        page = int(page)

    if order == '' or order == None:
        order = 0
    else:
        order = int(order)

    category_obj = categories.objects.all()
    for c in category_obj:
        c.urlname = re.sub(r'[^\w]', '', c.name)

    if user_id == None:    
        if type == -1:
            course_list = Courses.objects.filter(approval_status=2).order_by('created_at')
        else:
            course_list = Courses.objects.filter(approval_status=2).filter(type=type).order_by('created_at')
    else:
        register_course_ids = student_register_courses.objects.filter(student_id_id=user_id).values_list('course_id_id', flat=True)
        if type == -1:
            course_list = Courses.objects.filter(approval_status=2).exclude(id__in=register_course_ids).order_by('created_at')
        else:
            course_list = Courses.objects.filter(approval_status=2).filter(type=type).exclude(id__in=register_course_ids).order_by('created_at')
    
    # get discount information
    discount = Discount.objects.all()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    for course in course_list:
        course.link = courseUrlGenerator(course)
        rate_list = course_comments.objects.filter(course_id_id=course.id)
        course.rating = getRatingFunc(rate_list)
        course.student_count = len(rate_list)
        if discount.count() == 0:
            discount_percent = 1
        else:
            if now > discount[0].expire_date:
                discount_percent = 1
            else:
                not_str = discount[0].not_apply_course
                not_list = not_str.split('.')
                if str(course.id) in not_list:
                    discount_percent = 1
                else:
                    discount_percent = (100 - discount[0].discount) / 100
        course.discount_price = round(course.price * discount_percent, 2)

    # new part with admin... (05-17)
    ele = Admincontrol.objects.get(pk=1)
    cat_id = int(ele.priority)

    favListShow, favCnt, alreadyinFavView, cartListShow, cartCnt, alreadyinCartView, cartTotalSum, noti_list, noti_cnt, msg_list, msg_cnt, stu_msg_list, stu_msg_cnt, total_msg_cnt = findheader(
        request.user.id)

    course_list_paginator = Paginator(course_list, 10)
    try:
        course_list = course_list_paginator.page(page)
    except PageNotAnInteger:
        course_list = course_list_paginator.page(1)
    except EmptyPage:
        course_list = course_list_paginator.page(course_list_paginator.num_pages)

    for course in course_list:
        rating_list = course_comments.objects.filter(course_id_id=course.id).values_list('rating', flat=True)
        sum = 0
        count = 0
        cur_rating = 0
        flag = 1
        for rating in rating_list:
            sum += rating
            count += 1
        if count == 0:
            cur_rating = 0
        else:
            cur_rating = (sum / count)
        course.count = count
        course.student_num = len(student_register_courses.objects.filter(course_id_id=course.id))
        if cur_rating < 4.8:
            flag = 0
        else:
            student_num = course.student_num
            if student_num < 2000:
                flag = 0
            else:
                spam_num = len(Spam.objects.filter(course_id=course.id))
                if spam_num > 3:
                    flag = 0

        course.booctep_choice = flag
        course.video = getVideoCnt(course)

    course_list_tmp = course_list
    if order == 1:
        course_list = sorted(course_list_tmp, key=attrgetter('rating'), reverse=True)
    elif order == 2:
        course_list = sorted(course_list_tmp, key=attrgetter('student_num'), reverse=True)
    elif order == 3:
        course_list = sorted(course_list_tmp, key=attrgetter('created_at'), reverse=True)
    request.session[LANGUAGE_SESSION_KEY] = 'ar'

    if getLanguage(request)[1] == None:
        if user_type == "student":
            stu_courses = student_register_courses.objects.filter(student_id_id=request.user.id)
            for course in stu_courses:
                courses = Courses.objects.get(pk=course.course_id_id)
                course.videoCnt = getVideoCnt(courses)
            print("stu_courses:::", stu_courses)
            return render(request, 'index.html',
                          {'course_list': course_list, 'page': page, 'type': type,
                           'lang': getLanguage(request)[0], "user_id": user_id, "category_obj": category_obj,
                           'favList': favListShow, 'alreadyinFav': alreadyinFavView, 'cartList': cartListShow,
                           'alreadyinCart': alreadyinCartView, 'favCnt': favCnt, 'cartCnt': cartCnt,
                           'msg_list': msg_list, 'msg_cnt': msg_cnt,
                           'stu_courses': stu_courses, 'cartTotalSum': cartTotalSum, 'noti_cnt': noti_cnt,
                           'noti_list': noti_list, 'cat_id': cat_id, 'ip': ip, 'order': order, 'host_url': host_url})
        elif user_type == "stuteach":
            stu_courses = student_register_courses.objects.filter(student_id_id=request.user.id)
            for course in stu_courses:
                courses = Courses.objects.get(pk=course.course_id_id)
                course.videoCnt = getVideoCnt(courses)
            if user_id:
                return render(request, 'index.html', {'course_list': course_list, 'page': page, 'type': type,
                                                      'lang': getLanguage(request)[0], "category_obj": category_obj,
                                                      "user_id": user_id, 'stu_courses': stu_courses, 'favList': favListShow,
                                                      'alreadyinFav': alreadyinFavView, 'cartList': cartListShow,
                                                      'alreadyinCart': alreadyinCartView, 'favCnt': favCnt,
                                                      'cartCnt': cartCnt, 'cartTotalSum': cartTotalSum,
                                                      'msg_list': msg_list, 'msg_cnt': msg_cnt, 
                                                      'stu_msg_list': stu_msg_list, 'stu_msg_cnt': stu_msg_cnt, 'total_msg_cnt': total_msg_cnt,
                                                      'noti_cnt': noti_cnt, 'noti_list': noti_list, 'cat_id': cat_id,
                                                      'ip': ip, 'order': order, 'host_url': host_url})
            else:
                return render(request, 'index.html', {'course_list': course_list, 'page': page, 'type': type,
                                                      'lang': getLanguage(request)[0], "category_obj": category_obj, 'stu_courses': stu_courses,
                                                      'favList': favListShow, 'cartList': cartListShow,
                                                      'favCnt': favCnt, 'cartCnt': cartCnt,
                                                      'cartTotalSum': cartTotalSum, 'noti_cnt': noti_cnt,
                                                      'msg_list': msg_list, 'msg_cnt': msg_cnt, 
                                                      'stu_msg_list': stu_msg_list, 'stu_msg_cnt': stu_msg_cnt, 'total_msg_cnt': total_msg_cnt,
                                                      'noti_list': noti_list, 'cat_id': cat_id, 'ip': ip,
                                                      'order': order, 'host_url': host_url})
        else:
            if user_id:
                return render(request, 'index.html', {'course_list': course_list, 'page': page, 'type': type,
                                                      'lang': getLanguage(request)[0], "category_obj": category_obj,
                                                      "user_id": user_id, 'favList': favListShow,
                                                      'alreadyinFav': alreadyinFavView, 'cartList': cartListShow,
                                                      'alreadyinCart': alreadyinCartView, 'favCnt': favCnt,
                                                      'cartCnt': cartCnt, 'cartTotalSum': cartTotalSum,
                                                      'msg_list': msg_list, 'msg_cnt': msg_cnt,
                                                      'noti_cnt': noti_cnt, 'noti_list': noti_list, 'cat_id': cat_id,
                                                      'ip': ip, 'order': order, 'host_url': host_url})
            else:
                return render(request, 'index.html', {'course_list': course_list, 'page': page, 'type': type,
                                                      'lang': getLanguage(request)[0], "category_obj": category_obj,
                                                      'favList': favListShow, 'cartList': cartListShow,
                                                      'favCnt': favCnt, 'cartCnt': cartCnt,
                                                      'cartTotalSum': cartTotalSum, 'noti_cnt': noti_cnt,
                                                      'msg_list': msg_list, 'msg_cnt': msg_cnt,
                                                      'noti_list': noti_list, 'cat_id': cat_id, 'ip': ip,
                                                      'order': order, 'host_url': host_url})
    else:
        ur = getLanguage(request)[1].split('/')
        print("language test:", ur)
        if getLanguage(request)[0] == "":
            ln = "en"
        else:
            ln = "ar"

        if len(ur) == 1 and ur[1] == "":
            la = "en"
        else:
            la = ur[3]
        if la == ln:
            if user_type == "student":
                stu_courses = student_register_courses.objects.filter(student_id_id=request.user.id)
                return render(request, 'index.html',
                              {'stu_courses': stu_courses,
                               'course_list': course_list, 'page': page, 'type': type, 'lang': getLanguage(request)[0],
                               "category_obj": category_obj, "user_id": user_id, "category_obj": category_obj,
                               'favList': favListShow, 'alreadyinFav': alreadyinFavView, 'cartList': cartListShow,
                               'alreadyinCart': alreadyinCartView, 'favCnt': favCnt, 'cartCnt': cartCnt,
                               'cartTotalSum': cartTotalSum, 'noti_cnt': noti_cnt, 'noti_list': noti_list,
                               'msg_list': msg_list, 'msg_cnt': msg_cnt,
                               'cat_id': cat_id, 'ip': ip, 'order': order, 'host_url': host_url})
            elif user_type == "stuteach":
                stu_courses = student_register_courses.objects.filter(student_id_id=request.user.id)
                if user_id:
                    return render(request, 'index.html',
                                  {'stu_courses': stu_courses, 'course_list': course_list, 'page': page, 'type': type,
                                   'lang': getLanguage(request)[0],
                                   "category_obj": category_obj, "user_id": user_id, 'favList': favListShow,
                                   'alreadyinFav': alreadyinFavView, 'cartList': cartListShow,
                                   'alreadyinCart': alreadyinCartView, 'favCnt': favCnt, 'cartCnt': cartCnt,
                                   'cartTotalSum': cartTotalSum, 'noti_cnt': noti_cnt, 'noti_list': noti_list,
                                   'msg_list': msg_list, 'msg_cnt': msg_cnt,
                                   'stu_msg_list': stu_msg_list, 'stu_msg_cnt': stu_msg_cnt, 'total_msg_cnt': total_msg_cnt,
                                   'cat_id': cat_id, 'ip': ip, 'order': order, 'host_url': host_url})
                else:
                    return render(request, 'index.html',
                                  {'stu_courses': stu_courses, 'course_list': course_list, 'page': page, 'type': type,
                                   'lang': getLanguage(request)[0],
                                   "category_obj": category_obj, 'favList': favListShow, 'cartList': cartListShow,
                                   'favCnt': favCnt, 'cartCnt': cartCnt, 'cartTotalSum': cartTotalSum,
                                   'msg_list': msg_list, 'msg_cnt': msg_cnt, 
                                   'stu_msg_list': stu_msg_list, 'stu_msg_cnt': stu_msg_cnt, 'total_msg_cnt': total_msg_cnt,
                                   'noti_cnt': noti_cnt, 'noti_list': noti_list, 'cat_id': cat_id, 'ip': ip,
                                   'order': order, 'host_url': host_url})
            else:
                if user_id:
                    return render(request, 'index.html',
                                  {'course_list': course_list, 'page': page, 'type': type,
                                   'lang': getLanguage(request)[0],
                                   "category_obj": category_obj, "user_id": user_id, 'favList': favListShow,
                                   'alreadyinFav': alreadyinFavView, 'cartList': cartListShow,
                                   'alreadyinCart': alreadyinCartView, 'favCnt': favCnt, 'cartCnt': cartCnt,
                                   'cartTotalSum': cartTotalSum, 'noti_cnt': noti_cnt, 'noti_list': noti_list,
                                   'msg_list': msg_list, 'msg_cnt': msg_cnt, 
                                   'cat_id': cat_id, 'ip': ip, 'order': order, 'host_url': host_url})
                else:
                    return render(request, 'index.html',
                                  {'course_list': course_list, 'page': page, 'type': type,
                                   'lang': getLanguage(request)[0],
                                   "category_obj": category_obj, 'favList': favListShow, 'cartList': cartListShow,
                                   'favCnt': favCnt, 'cartCnt': cartCnt, 'cartTotalSum': cartTotalSum,
                                   'msg_list': msg_list, 'msg_cnt': msg_cnt, 
                                   'noti_cnt': noti_cnt, 'noti_list': noti_list, 'cat_id': cat_id, 'ip': ip,
                                   'order': order, 'host_url': host_url})
        else:
            li = getLanguage(request)[0].split('/')
            if len(ur) == 7:
                u = ur[0] + "//" + ur[2] + "/" + ln + "/" + ur[4] + "/" + ur[5] + "/"

                if ur[5] == "":
                    u = u[:len(u) - 1]
                    if user_type == "student":
                        stu_courses = student_register_courses.objects.filter(student_id_id=request.user.id)
                        return render(request, 'index.html',
                                      {'course_list': course_list, 'page': page, 'type': type,
                                       'lang': getLanguage(request)[0], "category_obj": category_obj,
                                       "user_id": user_id, "category_obj": category_obj, 'favList': favListShow,
                                       'alreadyinFav': alreadyinFavView, 'cartList': cartListShow,
                                       'alreadyinCart': alreadyinCartView, 'favCnt': favCnt, 'cartCnt': cartCnt,
                                       'cartTotalSum': cartTotalSum, 'noti_cnt': noti_cnt, 'noti_list': noti_list,
                                       'msg_list': msg_list, 'msg_cnt': msg_cnt,
                                       'stu_courses': stu_courses, 'cat_id': cat_id, 'ip': ip, 'order': order, 'host_url': host_url})
                    elif user_type == "stuteacher":
                        stu_courses = student_register_courses.objects.filter(student_id_id=request.user.id)
                        if user_id:
                            return render(request, 'index.html',
                                          {'stu_courses': stu_courses, 'course_list': course_list, 'page': page, 'type': type,
                                           'lang': getLanguage(request)[0],
                                           "category_obj": category_obj, "user_id": user_id, 'favList': favListShow,
                                           'alreadyinFav': alreadyinFavView, 'cartList': cartListShow,
                                           'alreadyinCart': alreadyinCartView, 'favCnt': favCnt, 'cartCnt': cartCnt,
                                           'cartTotalSum': cartTotalSum, 'noti_cnt': noti_cnt, 'noti_list': noti_list,
                                           'msg_list': msg_list, 'msg_cnt': msg_cnt, 
                                           'stu_msg_list': stu_msg_list, 'stu_msg_cnt': stu_msg_cnt, 'total_msg_cnt': total_msg_cnt,
                                           'cat_id': cat_id, 'ip': ip, 'order': order, 'host_url': host_url})
                        else:
                            return render(request, 'index.html',
                                          {'stu_courses': stu_courses, 'course_list': course_list, 'page': page, 'type': type,
                                           'lang': getLanguage(request)[0],
                                           "category_obj": category_obj, 'favList': favListShow,
                                           'cartList': cartListShow, 'favCnt': favCnt, 'cartCnt': cartCnt,
                                           'cartTotalSum': cartTotalSum, 'noti_cnt': noti_cnt, 'noti_list': noti_list,
                                           'msg_list': msg_list, 'msg_cnt': msg_cnt, 
                                           'stu_msg_list': stu_msg_list, 'stu_msg_cnt': stu_msg_cnt, 'total_msg_cnt': total_msg_cnt,
                                           'cat_id': cat_id, 'ip': ip, 'order': order, 'host_url': host_url})
                    else:
                        if user_id:
                            return render(request, 'index.html',
                                          {'course_list': course_list, 'page': page, 'type': type,
                                           'lang': getLanguage(request)[0],
                                           "category_obj": category_obj, "user_id": user_id, 'favList': favListShow,
                                           'alreadyinFav': alreadyinFavView, 'cartList': cartListShow,
                                           'alreadyinCart': alreadyinCartView, 'favCnt': favCnt, 'cartCnt': cartCnt,
                                           'cartTotalSum': cartTotalSum, 'noti_cnt': noti_cnt, 'noti_list': noti_list,
                                           'msg_list': msg_list, 'msg_cnt': msg_cnt,
                                           'cat_id': cat_id, 'ip': ip, 'order': order, 'host_url': host_url})
                        else:
                            return render(request, 'index.html',
                                          {'course_list': course_list, 'page': page, 'type': type,
                                           'lang': getLanguage(request)[0],
                                           "category_obj": category_obj, 'favList': favListShow,
                                           'cartList': cartListShow, 'favCnt': favCnt, 'cartCnt': cartCnt,
                                           'cartTotalSum': cartTotalSum, 'noti_cnt': noti_cnt, 'noti_list': noti_list,
                                           'msg_list': msg_list, 'msg_cnt': msg_cnt,
                                           'cat_id': cat_id, 'ip': ip, 'order': order, 'host_url': host_url})
                else:
                    return redirect(u)
            else:
                if user_type == "student":
                    stu_courses = student_register_courses.objects.filter(student_id_id=request.user.id)
                    return render(request, 'index.html',
                                  {'course_list': course_list, 'page': page, 'type': type,
                                   'lang': getLanguage(request)[0], "category_obj": category_obj,
                                   "user_id": user_id, 'favList': favListShow, 'alreadyinFav': alreadyinFavView,
                                   'cartList': cartListShow, 'alreadyinCart': alreadyinCartView, 'favCnt': favCnt,
                                   'cartCnt': cartCnt, 'cartTotalSum': cartTotalSum, 'noti_cnt': noti_cnt,
                                   'msg_list': msg_list, 'msg_cnt': msg_cnt,
                                   'noti_list': noti_list, 'stu_courses': stu_courses, 'cat_id': cat_id, 'ip': ip,
                                   'order': order, 'host_url': host_url})
                elif user_type == "stuteach":
                    stu_courses = student_register_courses.objects.filter(student_id_id=request.user.id)
                    if user_id:
                        return render(request, 'index.html',
                                      {'stu_courses': stu_courses, 'course_list': course_list, 'page': page, 'type': type,
                                       'lang': getLanguage(request)[0],
                                       "category_obj": category_obj, 'favList': favListShow,
                                       'alreadyinFav': alreadyinFavView, 'cartList': cartListShow,
                                       'alreadyinCart': alreadyinCartView, 'favCnt': favCnt, 'cartCnt': cartCnt,
                                       'cartTotalSum': cartTotalSum, 'noti_cnt': noti_cnt, 'noti_list': noti_list,
                                       'msg_list': msg_list, 'msg_cnt': msg_cnt, 
                                       'stu_msg_list': stu_msg_list, 'stu_msg_cnt': stu_msg_cnt, 'total_msg_cnt': total_msg_cnt,
                                       'cat_id': cat_id, 'ip': ip, 'order': order, 'host_url': host_url})
                    else:
                        return render(request, 'index.html',
                                      {'stu_courses': stu_courses, 'course_list': course_list, 'page': page, 'type': type,
                                       'lang': getLanguage(request)[0],
                                       "category_obj": category_obj, 'favList': favListShow,
                                       'cartList': cartListShow, "user_id": user_id, 'favCnt': favCnt,
                                       'cartCnt': cartCnt, 'cartTotalSum': cartTotalSum, 'noti_cnt': noti_cnt,
                                       'msg_list': msg_list, 'msg_cnt': msg_cnt, 
                                       'stu_msg_list': stu_msg_list, 'stu_msg_cnt': stu_msg_cnt, 'total_msg_cnt': total_msg_cnt,
                                       'noti_list': noti_list, 'cat_id': cat_id, 'ip': ip, 'order': order, 'host_url': host_url})
                else:
                    if user_id:
                        return render(request, 'index.html',
                                      {'course_list': course_list, 'page': page, 'type': type,
                                       'lang': getLanguage(request)[0],
                                       "category_obj": category_obj, 'favList': favListShow,
                                       'alreadyinFav': alreadyinFavView, 'cartList': cartListShow,
                                       'alreadyinCart': alreadyinCartView, 'favCnt': favCnt, 'cartCnt': cartCnt,
                                       'cartTotalSum': cartTotalSum, 'noti_cnt': noti_cnt, 'noti_list': noti_list,
                                       'msg_list': msg_list, 'msg_cnt': msg_cnt,
                                       'cat_id': cat_id, 'ip': ip, 'order': order, 'host_url': host_url})
                    else:
                        return render(request, 'index.html',
                                      {'course_list': course_list, 'page': page, 'type': type,
                                       'lang': getLanguage(request)[0],
                                       "category_obj": category_obj, 'favList': favListShow,
                                       'cartList': cartListShow, "user_id": user_id, 'favCnt': favCnt,
                                       'cartCnt': cartCnt, 'cartTotalSum': cartTotalSum, 'noti_cnt': noti_cnt,
                                       'msg_list': msg_list, 'msg_cnt': msg_cnt,
                                       'noti_list': noti_list, 'cat_id': cat_id, 'ip': ip, 'order': order, 'host_url': host_url})
                # else:
                #     return redirect(u)


def home_view1(request):
    # Session.objects.all().delete()
    ip = get_client_ip(request)
    if request.session.get(ip) == None:
        request.session[ip] = 'ar' + '-' + 'light'

    user_id = request.session.get("user_id")
    user_type = request.session.get("user_type")
    category_obj = categories.objects.all()

    # new part with admin... (05-17)
    ele = Admincontrol.objects.get(pk=1)
    cat_id = int(ele.priority)
    print("cat_id", cat_id)

    if user_type == "student":
        enrolled_course_list_query = student_register_courses.objects.values('course_id_id').filter(
            student_id_id=request.user.id)
        enrolled_course_list = []
        for value in range(len(enrolled_course_list_query)):
            enrolled_course_list.append(enrolled_course_list_query[value]['course_id_id'])
        enrolled_course_list = map(str, enrolled_course_list)
        enrolled_ids = ','.join(enrolled_course_list)
        course_list = Courses.objects.extra(where=['find_in_set(id, "' + enrolled_ids + '")'])
        course_free_list = Courses.objects.extra(where=['find_in_set(id, "' + enrolled_ids + '")']).filter(type=1)
        course_paid_list = Courses.objects.extra(where=['find_in_set(id, "' + enrolled_ids + '")']).filter(type=0)
        print("enrolled::", course_list)
    elif user_type == "teacher":
        teachers_courses = get_teacher_CourseList(request)
        course_list = getAllCourseList()
        course_free_list = getFreeCourseList()
        course_paid_list = getPaidCourseList()
        excludedcourselist = [e for e in course_list if e not in teachers_courses]
        excludedcoursepaidlist = [e for e in course_paid_list if e not in teachers_courses]
        excludedcoursefreelist = [e for e in course_free_list if e not in teachers_courses]
        course_list = excludedcourselist
        course_paid_list = excludedcoursepaidlist
        course_free_list = excludedcoursefreelist
    else:
        course_list = getAllCourseList()
        course_free_list = getFreeCourseList()
        course_paid_list = getPaidCourseList()

    for course in course_list:
        rateList = course_comments.objects.filter(course_id_id=course.id).values_list('rating', flat=True)
        rateList = list(rateList)
        sum = 0
        for i in rateList:
            sum += i
        cnt = len(rateList)
        if cnt == 0:
            course.rating = 0
        else:
            course.rating = round(sum / cnt, 1)
        course.video = getVideoCnt(course)
        course.stuCnt = student_register_courses.objects.filter(course_id_id=course.id).count()
        course.ratertotal = cnt
        course.link = courseUrlGenerator(course)
    for course in course_free_list:
        rateList = course_comments.objects.filter(course_id_id=course.id).values_list('rating', flat=True)
        rateList = list(rateList)
        sum = 0
        for i in rateList:
            sum += i
        cnt = len(rateList)
        if cnt == 0:
            course.rating = 0
        else:
            course.rating = round(sum / cnt, 1)
        course.video = getVideoCnt(course)
        course.stuCnt = student_register_courses.objects.filter(course_id_id=course.id).count()
        course.ratertotal = cnt
        course.link = courseUrlGenerator(course)
    for course in course_paid_list:
        rateList = course_comments.objects.filter(course_id_id=course.id).values_list('rating', flat=True)
        rateList = list(rateList)
        sum = 0
        for i in rateList:
            sum += i
        cnt = len(rateList)
        if cnt == 0:
            course.rating = 0
        else:
            course.rating = round(sum / cnt, 1)
        course.video = getVideoCnt(course)
        course.stuCnt = student_register_courses.objects.filter(course_id_id=course.id).count()
        course.ratertotal = cnt
        course.link = courseUrlGenerator(course)

    favListShow, favCnt, alreadyinFavView, cartListShow, cartCnt, alreadyinCartView, cartTotalSum, noti_list, noti_cnt = findheader(
        request.user.id)

    ## Pagination
    number_of_courses_in_a_page = 15
    course_list_page = request.GET.get('course_list_page', 1)
    course_list_paginator = Paginator(course_list, number_of_courses_in_a_page)

    try:
        course_list = course_list_paginator.page(course_list_page)
    except PageNotAnInteger:
        course_list = course_list_paginator.page(1)
    except EmptyPage:
        course_list = course_list_paginator.page(course_list_paginator.num_pages)

    course_paid_list_page = request.GET.get('course_paid_list_page', 1)
    course_paid_list_paginator = Paginator(course_paid_list, number_of_courses_in_a_page)

    try:
        course_paid_list = course_paid_list_paginator.page(course_paid_list_page)
    except PageNotAnInteger:
        course_paid_list = course_paid_list_paginator.page(1)
    except EmptyPage:
        course_paid_list = course_paid_list_paginator.page(course_paid_list_paginator.num_pages)

    course_free_list_page = request.GET.get('course_free_list_page', 1)
    course_free_list_paginator = Paginator(course_free_list, number_of_courses_in_a_page)

    try:
        course_free_list = course_free_list_paginator.page(course_free_list_page)
    except PageNotAnInteger:
        course_free_list = course_free_list_paginator.page(1)
    except EmptyPage:
        course_free_list = course_free_list_paginator.page(course_free_list_paginator.num_pages)

    ## End Pagination
    request.session[LANGUAGE_SESSION_KEY] = 'ar'

    if getLanguage(request)[1] == None:

        if user_type == "student":
            stu_courses = student_register_courses.objects.filter(student_id_id=request.user.id)
            for course in stu_courses:
                courses = Courses.objects.get(pk=course.course_id_id)
                course.videoCnt = getVideoCnt(courses)
            print("stu_courses:::", stu_courses)
            return render(request, 'index.html',
                          {'enrolled_course_list': enrolled_course_list, 'course_list': course_list,
                           'course_free_list': course_free_list, 'course_paid_list': course_paid_list,
                           'lang': getLanguage(request)[0], "user_id": user_id, "category_obj": category_obj,
                           'favList': favListShow, 'alreadyinFav': alreadyinFavView, 'cartList': cartListShow,
                           'alreadyinCart': alreadyinCartView, 'favCnt': favCnt, 'cartCnt': cartCnt,
                           'stu_courses': stu_courses, 'cartTotalSum': cartTotalSum, 'noti_cnt': noti_cnt,
                           'noti_list': noti_list, 'cat_id': cat_id})
        else:
            if user_id:
                return render(request, 'index.html', {'course_list': course_list, 'course_free_list': course_free_list,
                                                      'course_paid_list': course_paid_list,
                                                      'lang': getLanguage(request)[0], "category_obj": category_obj,
                                                      "user_id": user_id, 'favList': favListShow,
                                                      'alreadyinFav': alreadyinFavView, 'cartList': cartListShow,
                                                      'alreadyinCart': alreadyinCartView, 'favCnt': favCnt,
                                                      'cartCnt': cartCnt, 'cartTotalSum': cartTotalSum,
                                                      'noti_cnt': noti_cnt, 'noti_list': noti_list, 'cat_id': cat_id})
            else:
                return render(request, 'index.html', {'course_list': course_list, 'course_free_list': course_free_list,
                                                      'course_paid_list': course_paid_list,
                                                      'lang': getLanguage(request)[0], "category_obj": category_obj,
                                                      'favList': favListShow, 'cartList': cartListShow,
                                                      'favCnt': favCnt, 'cartCnt': cartCnt,
                                                      'cartTotalSum': cartTotalSum, 'noti_cnt': noti_cnt,
                                                      'noti_list': noti_list, 'cat_id': cat_id})
    else:
        ur = getLanguage(request)[1].split('/')
        print("language test:", ur)
        if getLanguage(request)[0] == "":
            ln = "en"
        else:
            ln = "ar"

        if len(ur) == 1 and ur[1] == "":
            la = "en"
        else:
            la = ur[3]
        if la == ln:
            if user_type == "student":
                stu_courses = student_register_courses.objects.filter(student_id_id=request.user.id)
                return render(request, 'index.html',
                              {'stu_courses': stu_courses, 'enrolled_course_list': enrolled_course_list,
                               'course_list': course_list, 'course_free_list': course_free_list,
                               'course_paid_list': course_paid_list, 'lang': getLanguage(request)[0],
                               "category_obj": category_obj, "user_id": user_id, "category_obj": category_obj,
                               'favList': favListShow, 'alreadyinFav': alreadyinFavView, 'cartList': cartListShow,
                               'alreadyinCart': alreadyinCartView, 'favCnt': favCnt, 'cartCnt': cartCnt,
                               'cartTotalSum': cartTotalSum, 'noti_cnt': noti_cnt, 'noti_list': noti_list,
                               'cat_id': cat_id})
            else:
                if user_id:
                    return render(request, 'index.html',
                                  {'course_list': course_list, 'course_free_list': course_free_list,
                                   'course_paid_list': course_paid_list, 'lang': getLanguage(request)[0],
                                   "category_obj": category_obj, "user_id": user_id, 'favList': favListShow,
                                   'alreadyinFav': alreadyinFavView, 'cartList': cartListShow,
                                   'alreadyinCart': alreadyinCartView, 'favCnt': favCnt, 'cartCnt': cartCnt,
                                   'cartTotalSum': cartTotalSum, 'noti_cnt': noti_cnt, 'noti_list': noti_list,
                                   'cat_id': cat_id})
                else:
                    return render(request, 'index.html',
                                  {'course_list': course_list, 'course_free_list': course_free_list,
                                   'course_paid_list': course_paid_list, 'lang': getLanguage(request)[0],
                                   "category_obj": category_obj, 'favList': favListShow, 'cartList': cartListShow,
                                   'favCnt': favCnt, 'cartCnt': cartCnt, 'cartTotalSum': cartTotalSum,
                                   'noti_cnt': noti_cnt, 'noti_list': noti_list, 'cat_id': cat_id})
        else:
            li = getLanguage(request)[0].split('/')
            if len(ur) == 7:
                u = ur[0] + "//" + ur[2] + "/" + ln + "/" + ur[4] + "/" + ur[5] + "/"

                if ur[5] == "":
                    u = u[:len(u) - 1]
                    if user_type == "student":
                        stu_courses = student_register_courses.objects.filter(student_id_id=request.user.id)
                        return render(request, 'index.html',
                                      {'enrolled_course_list': enrolled_course_list, 'course_list': course_list,
                                       'course_free_list': course_free_list, 'course_paid_list': course_paid_list,
                                       'lang': getLanguage(request)[0], "category_obj": category_obj,
                                       "user_id": user_id, "category_obj": category_obj, 'favList': favListShow,
                                       'alreadyinFav': alreadyinFavView, 'cartList': cartListShow,
                                       'alreadyinCart': alreadyinCartView, 'favCnt': favCnt, 'cartCnt': cartCnt,
                                       'cartTotalSum': cartTotalSum, 'noti_cnt': noti_cnt, 'noti_list': noti_list,
                                       'stu_courses': stu_courses, 'cat_id': cat_id})
                    else:
                        if user_id:
                            return render(request, 'index.html',
                                          {'course_list': course_list, 'course_free_list': course_free_list,
                                           'course_paid_list': course_paid_list, 'lang': getLanguage(request)[0],
                                           "category_obj": category_obj, "user_id": user_id, 'favList': favListShow,
                                           'alreadyinFav': alreadyinFavView, 'cartList': cartListShow,
                                           'alreadyinCart': alreadyinCartView, 'favCnt': favCnt, 'cartCnt': cartCnt,
                                           'cartTotalSum': cartTotalSum, 'noti_cnt': noti_cnt, 'noti_list': noti_list,
                                           'cat_id': cat_id})
                        else:
                            return render(request, 'index.html',
                                          {'course_list': course_list, 'course_free_list': course_free_list,
                                           'course_paid_list': course_paid_list, 'lang': getLanguage(request)[0],
                                           "category_obj": category_obj, 'favList': favListShow,
                                           'cartList': cartListShow, 'favCnt': favCnt, 'cartCnt': cartCnt,
                                           'cartTotalSum': cartTotalSum, 'noti_cnt': noti_cnt, 'noti_list': noti_list,
                                           'cat_id': cat_id})
                else:
                    return redirect(u)
            else:
                u = ur[0] + "//" + ur[2] + "/" + ln + "/" + ur[4] + "/"
                if ur[4] == "":
                    u = u[:len(u) - 1]
                    if user_type == "student":
                        stu_courses = student_register_courses.objects.filter(student_id_id=request.user.id)
                        return render(request, 'index.html',
                                      {'enrolled_course_list': enrolled_course_list, 'course_list': course_list,
                                       'course_free_list': course_free_list, 'course_paid_list': course_paid_list,
                                       'lang': getLanguage(request)[0], "category_obj": category_obj,
                                       "user_id": user_id, 'favList': favListShow, 'alreadyinFav': alreadyinFavView,
                                       'cartList': cartListShow, 'alreadyinCart': alreadyinCartView, 'favCnt': favCnt,
                                       'cartCnt': cartCnt, 'cartTotalSum': cartTotalSum, 'noti_cnt': noti_cnt,
                                       'noti_list': noti_list, 'stu_courses': stu_courses, 'cat_id': cat_id})
                    else:
                        if user_id:
                            return render(request, 'index.html',
                                          {'course_list': course_list, 'course_free_list': course_free_list,
                                           'course_paid_list': course_paid_list, 'lang': getLanguage(request)[0],
                                           "category_obj": category_obj, 'favList': favListShow,
                                           'alreadyinFav': alreadyinFavView, 'cartList': cartListShow,
                                           'alreadyinCart': alreadyinCartView, 'favCnt': favCnt, 'cartCnt': cartCnt,
                                           'cartTotalSum': cartTotalSum, 'noti_cnt': noti_cnt, 'noti_list': noti_list,
                                           'cat_id': cat_id})
                        else:
                            return render(request, 'index.html',
                                          {'course_list': course_list, 'course_free_list': course_free_list,
                                           'course_paid_list': course_paid_list, 'lang': getLanguage(request)[0],
                                           "category_obj": category_obj, 'favList': favListShow,
                                           'cartList': cartListShow, "user_id": user_id, 'favCnt': favCnt,
                                           'cartCnt': cartCnt, 'cartTotalSum': cartTotalSum, 'noti_cnt': noti_cnt,
                                           'noti_list': noti_list, 'cat_id': cat_id})
                else:
                    return redirect(u)

def findheader(userid):
    # Getting user's group
    user_group_id = 0 if userid is None else User.objects.get(pk=userid).group_id
    # show fav page.., cart page...
    favList = student_favourite_courses.objects.filter(student_id_id=userid)
    favCnt = len(favList)
    alreadyinFav = student_favourite_courses.objects.values('course_id_id').filter(student_id_id=userid)
    alreadyinFavView = []

    for value in range(len(alreadyinFav)):
        alreadyinFavView.append(alreadyinFav[value]['course_id_id'])

    favListShow = student_favourite_courses.objects.filter(student_id_id=userid).order_by("-id")[:3]

    cartList = student_cart_courses.objects.filter(student_id_id=userid)
    cartCnt = len(cartList)
    alreadyinCart = student_cart_courses.objects.values('course_id_id').filter(student_id_id=userid)
    alreadyinCartView = []

    for value in range(len(alreadyinCart)):
        alreadyinCartView.append(alreadyinCart[value]['course_id_id'])

    cartListShow = student_cart_courses.objects.filter(student_id_id=userid).order_by("-id")[:3]
    cartTotalSum = 0

    for cart in cartList:
        cartTotalSum += cart.course_id.price

    # show notification...
    noti_list = notifications.objects.filter(user_id=userid, is_read=0).order_by("-id")[:3]
    noti_cnt = notifications.objects.filter(user_id=userid, is_read=0).count()

    msg_list = []
    sender_ids = []
    student_msg_list = []
    student_sender_ids = []
    stu_msg_cnt = 0
    msgs = Messages.objects.filter(receiver_id=userid, is_read=0).order_by("-id")
    # if user is student&teacher account
    if user_group_id != 4:
        # Adding one latest message per sender and number of send should be small than 3
        for msg in msgs:
            if msg.sender_id not in sender_ids and len(sender_ids) < 3:
                sender_ids.append(msg.sender_id)
                msg_list.append(msg)
        msg_cnt = Messages.objects.filter(receiver_id=userid, is_read=0).values('sender_id').distinct().count()
    else:
        for msg in msgs:
            sender_group_id = User.objects.get(pk=msg.sender_id).group_id
            if msg.sender_id not in sender_ids and len(sender_ids) < 3 and sender_group_id == 2:
                sender_ids.append(msg.sender_id)
                msg_list.append(msg)
            if msg.sender_id not in student_sender_ids and len(student_sender_ids) < 3 and (sender_group_id == 3 or sender_group_id == 4):
                student_sender_ids.append(msg.sender_id)
                student_msg_list.append(msg)

        msg_cnt = Messages.objects.filter(receiver_id=userid, is_read=0, sender_id__in=sender_ids).values('sender_id').distinct().count()
        stu_msg_cnt = Messages.objects.filter(receiver_id=userid, is_read=0, sender_id__in=student_sender_ids).values('sender_id').distinct().count()

    total_msg_cnt = msg_cnt + stu_msg_cnt
    return favListShow, favCnt, alreadyinFavView, cartListShow, cartCnt, alreadyinCartView, cartTotalSum, noti_list, noti_cnt, msg_list, msg_cnt, student_msg_list, stu_msg_cnt, total_msg_cnt


def signup(request):

    objC = categories.objects.all()
    cat_list = []
    for cat in objC:
        item = {'name': cat.name, 'namear': cat.namear, 'id': cat.id}
        cat_list.append(item)
    
    user_id = request.session.get("user_id")
    if user_id is None:
        #del request.session['user_id']
        #del request.session['user_type']
        return render(request, 'signup.html', {"objC": cat_list, 'lang': getLanguage(request)[0]})
    else:
        return redirect('/')


def loginn(request):
    user_id = request.session.get("user_id")
    if user_id == None:
        return render(request, 'login.html', {'lang': getLanguage(request)[0]})
    else:
        return redirect('/')    


def about(request):
    x1, x2, x3, y1, y2, y3, y4, z1, z2, msg_list, msg_cnt, stu_msg_list, stu_msg_cnt, total_msg_cnt = findheader(request.user.id)
    user_type = request.session.get("user_type")
    stu_courses = student_register_courses.objects.filter(student_id_id=request.user.id)
    return render(request, 'about.html',
                  {'lang': getLanguage(request)[0], 'favList': x1, 'favCnt': x2, 'alreadyinFav': x3, 'cartList': y1,
                   'cartCnt': y2, 'alreadyinCart': y3, 'cartTotalSum': y4, 'noti_list': z1, 'noti_cnt': z2,
                   'msg_list': msg_list, 'msg_cnt': msg_cnt, "stu_courses": stu_courses, 'stu_msg_list': stu_msg_list, 'stu_msg_cnt': stu_msg_cnt, 'total_msg_cnt': total_msg_cnt})


def faqs(request):
    x1, x2, x3, y1, y2, y3, y4, z1, z2, msg_list, msg_cnt, stu_msg_list, stu_msg_cnt, total_msg_cnt = findheader(request.user.id)
    user_type = request.session.get("user_type")
    stu_courses = student_register_courses.objects.filter(student_id_id=request.user.id)
    return render(request, 'faqs.html',
                  {'lang': getLanguage(request)[0], 'favList': x1, 'favCnt': x2, 'alreadyinFav': x3, 'cartList': y1,
                   'cartCnt': y2, 'alreadyinCart': y3, 'cartTotalSum': y4, 'noti_list': z1, 'noti_cnt': z2,
                   'msg_list': msg_list, 'msg_cnt': msg_cnt, "stu_courses": stu_courses, 'stu_msg_list': stu_msg_list, 'stu_msg_cnt': stu_msg_cnt, 'total_msg_cnt': total_msg_cnt})


def help(request):
    user_id = request.session.get("user_id")
    user_type = request.session.get("user_type")
    x1, x2, x3, y1, y2, y3, y4, z1, z2, msg_list, msg_cnt, stu_msg_list, stu_msg_cnt, total_msg_cnt = findheader(request.user.id)
    stu_courses = student_register_courses.objects.filter(student_id_id=request.user.id)
    return render(request, 'support.html',
                  {'lang': getLanguage(request)[0], 'user_type': user_type, "user_id": user_id, 'favList': x1,
                   'favCnt': x2, 'alreadyinFav': x3, 'cartList': y1,
                   'cartCnt': y2, 'alreadyinCart': y3, 'cartTotalSum': y4, 'noti_list': z1, 'noti_cnt': z2,
                   'msg_list': msg_list, 'msg_cnt': msg_cnt, "stu_courses": stu_courses, 'stu_msg_list': stu_msg_list, 'stu_msg_cnt': stu_msg_cnt, 'total_msg_cnt': total_msg_cnt})


def terms(request):
    x1, x2, x3, y1, y2, y3, y4, z1, z2, msg_list, msg_cnt, stu_msg_list, stu_msg_cnt, total_msg_cnt = findheader(request.user.id)
    user_type = request.session.get("user_type")
    stu_courses = student_register_courses.objects.filter(student_id_id=request.user.id)
    return render(request, 'terms.html',
                  {'lang': getLanguage(request)[0], 'favList': x1, 'favCnt': x2, 'alreadyinFav': x3, 'cartList': y1,
                   'cartCnt': y2, 'alreadyinCart': y3, 'cartTotalSum': y4, 'noti_list': z1, 'noti_cnt': z2,
                   'msg_list': msg_list, 'msg_cnt': msg_cnt, "stu_courses": stu_courses, 'stu_msg_list': stu_msg_list, 'stu_msg_cnt': stu_msg_cnt, 'total_msg_cnt': total_msg_cnt})


def policy(request):
    x1, x2, x3, y1, y2, y3, y4, z1, z2, msg_list, msg_cnt, stu_msg_list, stu_msg_cnt, total_msg_cnt = findheader(request.user.id)
    user_type = request.session.get("user_type")
    stu_courses = student_register_courses.objects.filter(student_id_id=request.user.id)
    return render(request, 'privacy.html',
                  {'lang': getLanguage(request)[0], 'favList': x1, 'favCnt': x2, 'alreadyinFav': x3, 'cartList': y1,
                   'cartCnt': y2, 'alreadyinCart': y3, 'cartTotalSum': y4, 'noti_list': z1, 'noti_cnt': z2,
                   'msg_list': msg_list, 'msg_cnt': msg_cnt, "stu_courses": stu_courses, 'stu_msg_list': stu_msg_list, 'stu_msg_cnt': stu_msg_cnt, 'total_msg_cnt': total_msg_cnt})


def contact(request):
    x1, x2, x3, y1, y2, y3, y4, z1, z2, msg_list, msg_cnt, stu_msg_list, stu_msg_cnt, total_msg_cnt = findheader(request.user.id)
    user_type = request.session.get("user_type")
    stu_courses = student_register_courses.objects.filter(student_id_id=request.user.id)
    return render(request, 'contact.html',
                  {'lang': getLanguage(request)[0], 'favList': x1, 'favCnt': x2, 'alreadyinFav': x3, 'cartList': y1,
                   'cartCnt': y2, 'alreadyinCart': y3, 'cartTotalSum': y4, 'noti_list': z1, 'noti_cnt': z2,
                   'msg_list': msg_list, 'msg_cnt': msg_cnt, "stu_courses": stu_courses, 'stu_msg_list': stu_msg_list, 'stu_msg_cnt': stu_msg_cnt, 'total_msg_cnt': total_msg_cnt})


def become(request):
    lang = getLanguage(request)[0]
    if lang == '':
        lang = "en/"
    # if user is teacher or stu&teach account
    if request.user.is_authenticated:
        user_type = request.session.get("user_type")
        if user_type == 'teacher' or user_type == 'stuteach':
            return redirect("/" + lang + "teacher/courses/")

    objC = categories.objects.all()
    favList = student_favourite_courses.objects.filter(student_id_id=request.user.id)
    favListShow = student_favourite_courses.objects.filter(student_id_id=request.user.id).order_by("-id")[:3]
    cartList = student_cart_courses.objects.filter(student_id_id=request.user.id)
    cartListShow = student_cart_courses.objects.filter(student_id_id=request.user.id).order_by("-id")[:3]
    cartTotalSum = 0

    # show notification...
    noti_list = notifications.objects.filter(user_id=request.user.id, is_read=0).order_by("-id")[:3]
    noti_cnt = notifications.objects.filter(user_id=request.user.id, is_read=0).count()
    x1, x2, x3, y1, y2, y3, y4, z1, z2, msg_list, msg_cnt, stu_msg_list, stu_msg_cnt, total_msg_cnt = findheader(request.user.id)
    user_type = request.session.get("user_type")
    stu_courses = student_register_courses.objects.filter(student_id_id=request.user.id)
    return render(request, 'become.html',
                  {'lang': getLanguage(request)[0], 'catList': objC, 'favList': favListShow, 'cartList': cartListShow,
                   'favCnt': len(favList), 'cartCnt': len(cartList), 'cartTotalSum': cartTotalSum, 'noti_cnt': noti_cnt,
                   'noti_list': noti_list, 'msg_list': msg_list, 'msg_cnt': msg_cnt, "stu_courses": stu_courses, 'stu_msg_list': stu_msg_list, 'stu_msg_cnt': stu_msg_cnt, 'total_msg_cnt': total_msg_cnt})


def become_a_teacher(request):
    categoryList = categories.objects.all()
    favList = student_favourite_courses.objects.filter(student_id_id=request.user.id)
    favListShow = student_favourite_courses.objects.filter(student_id_id=request.user.id).order_by("-id")[:3]
    cartList = student_cart_courses.objects.filter(student_id_id=request.user.id)
    cartListShow = student_cart_courses.objects.filter(student_id_id=request.user.id).order_by("-id")[:3]
    cartTotalSum = 0

    noti_list = notifications.objects.filter(user_id=request.user.id, is_read=0).order_by("-id")[:3]
    noti_cnt = notifications.objects.filter(user_id=request.user.id, is_read=0).count()
    x1, x2, x3, y1, y2, y3, y4, z1, z2, msg_list, msg_cnt, stu_msg_list, stu_msg_cnt, total_msg_cnt = findheader(request.user.id)
    stu_courses = student_register_courses.objects.filter(student_id_id=request.user.id)
    return render(request, 'become-teacher.html', {'lang': getLanguage(request)[0], 'categories': categoryList, 'favList': favListShow, 'cartList': cartListShow,
                   'favCnt': len(favList), 'cartCnt': len(cartList), 'cartTotalSum': cartTotalSum, 'noti_cnt': noti_cnt,
                   'noti_list': noti_list, 'msg_list': msg_list, 'msg_cnt': msg_cnt, "stu_courses": stu_courses, 'stu_msg_list': stu_msg_list, 'stu_msg_cnt': stu_msg_cnt, 'total_msg_cnt': total_msg_cnt})


def save_become_teacher(request):
    user_id = request.user.id
    cat_id = request.POST.get("cat_id")
    subcat_id = request.POST.get("subcat_id")

    status = 1
    try:
        user = User.objects.get(pk=user_id)
        # user.group_id = 3
        user.group_id = 4
        user.save()
    except:
        status = 0

    return JsonResponse({
        'status': status
    })


def getMessageHistory(request):
    sender_id = request.POST.get('sender_id')
    receiver_id = request.POST.get('receiver_id')
    course_id = request.POST.get('course_id')
    messages = Messages.objects.filter(
        Q(sender_id=sender_id, receiver_id=receiver_id) | Q(sender_id=receiver_id, receiver_id=sender_id)).filter(
        course_id=course_id).filter(~Q(delete_id=receiver_id))
    Messages.objects.filter(Q(sender_id=sender_id, receiver_id=receiver_id)).filter(course_id=course_id).update(
        is_read=1)

    ret = {
        'messages': serializers.serialize('json', messages),
    }
    return JsonResponse(ret)


def deleteMessageHistory(request):
    sender_id = request.POST.get('sender_id')
    receiver_id = request.POST.get('receiver_id')
    course_id = request.POST.get('course_id')
    messages = Messages.objects.filter(
        Q(sender_id=sender_id, receiver_id=receiver_id) | Q(sender_id=receiver_id, receiver_id=sender_id)).filter(
        course_id=course_id)
    status = 1
    try:
        for ele in messages:
            if int(ele.delete_id) == 0 or int(ele.delete_id) == int(receiver_id):
                ele.delete_id = receiver_id
                ele.save()
            else:
                ele.delete()
    except:
        status = 0
    ret = {
        'status': status
    }
    return JsonResponse(ret)


def setMessageRead(request):
    sender_id = request.POST.get('sender_id')
    receiver_id = request.POST.get('receiver_id')
    course_id = request.POST.get('course_id')
    status = 1
    try:
        Messages.objects.filter(sender_id=sender_id, receiver_id=receiver_id, course_id=course_id).update(is_read=1)
    except:
        status = 0
    ret = {
        'status': status
    }
    return JsonResponse(ret)


def setMessageReadById(request):
    id = request.POST.get('id')
    status = 1
    try:
        Messages.objects.filter(sender_id=id).update(is_read=1)
    except:
        status = 0
    ret = {
        'status': status
    }
    return JsonResponse(ret)


def getUserById(request):
    id = request.POST.get('id')
    user = User.objects.get(pk=id)
    ret = {
        'user': serializers.serialize('json', [user])
    }
    return JsonResponse(ret)


# delete in student's part
def deleteNotificationById(request):
    id = request.POST.get('id')
    status = 1
    try:
        notifications.objects.get(pk=id).delete()
    except:
        status = 0
    ret = {
        'status': status
    }
    return JsonResponse(ret)


# mark notification as read by id in header
def setNotificationReadById(request):
    id = request.POST.get('id')
    status = 1
    try:
        notifications.objects.filter(id=id).update(is_read=1)
    except:
        status = 0
    ret = {
        'status': status
    }
    return JsonResponse(ret)


# delete in teacher's part
def deleteNotification(request):
    course_id = request.POST.get('course_id')
    time = request.POST.get('time')
    sender_id = request.POST.get('sender_id')
    noti_id = request.POST.get('noti_id')
    status = 1
    try:
        notifications.objects.get(pk=noti_id).delete()
    except:
        status = 0
    ret = {
        'status': status
    }
    return JsonResponse(ret)


def editNotification(request):
    id = request.POST.get('id')
    title = request.POST.get('title')
    text = request.POST.get('text')
    status = 1
    try:
        ele = notifications.objects.get(pk=id)
        ele.title = title
        ele.text = text
        ele.save()
    except:
        status = 0
    ret = {
        'status': status
    }
    return JsonResponse(ret)


@csrf_exempt
def reportSpam(request):
    course_id = request.POST.get('course_id')
    student_id = request.POST.get('student_id')
    teacher_id = request.POST.get('teacher_id')
    title = request.POST.get('title')
    content = request.POST.get('content')
    time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status = 1
    try:
        ele = Spam(
            teacher_id=teacher_id,
            student_id=student_id,
            course_id=course_id,
            title=title,
            content=content,
            date_created=time
        )
        ele.save()
    except:
        status = 0
    ret = {
        'status': status
    }
    return JsonResponse(ret)


@csrf_exempt
def refund(request):
    course_id = request.POST.get('course_id')
    student_id = request.POST.get('student_id')
    teacher_id = request.POST.get('teacher_id')
    title = request.POST.get('title')
    content = request.POST.get('content')
    status = 1
    time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        if Refund.objects.filter(teacher_id=teacher_id, student_id=student_id, course_id=course_id).exists():
            status = 2
        else:
            ele = Refund(
                teacher_id=teacher_id,
                student_id=student_id,
                course_id=course_id,
                title=title,
                content=content,
                date_created=time
            )
            ele.save()
    except:
        status = 0
    ret = {
        'status': status
    }
    return JsonResponse(ret)


def courseUrlGenerator(course):
    name = course.course_url
    teacher_id = course.user_id
    courselink = str(teacher_id) + "/" + str(name)
    return courselink


def single_course(request, teacher_id, course_url):
    user_type = request.session.get("user_type")
    user_id = request.session.get("user_id")
    course = []

    # get discount information
    discount = Discount.objects.all()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if Courses.objects.filter(user_id=teacher_id, course_url=course_url).exists():
        course = Courses.objects.filter(user_id=teacher_id, course_url=course_url)[0]
    id = course.id

    # if this course is in user's registered courses, then redirecting user to home
    register_course_ids = student_register_courses.objects.filter(student_id_id=user_id).values_list('course_id_id', flat=True)
    if id in register_course_ids:
        return redirect(home_view)

    course = Courses.objects.get(id=id)
    if discount.count() == 0:
        discount_percent = 0
    else:
        if now > discount[0].expire_date:
            discount_percent = 0
        else:
            not_str = discount[0].not_apply_course
            not_list = not_str.split(',')
            if str(course.id) in not_list:
                discount_percent = 0
            else:
                discount_percent = discount[0].discount / 100

    tax = 0
    # calculating the tax for course
    if Admincontrol.objects.filter(id=1).exists():
        tax = Admincontrol.objects.get(pk=1).student_tax
    course.tax = round(course.price * tax / 100, 2)

    # calculating final price
    course.discount_price = round(course.price - (course.price * discount_percent) + course.tax, 2)
    course.discount = round(course.price * discount_percent, 2)

    similar_cat = course.subcat_id
    similar_parent_cat = course.scat_id

    similar_courses = Courses.objects.filter(Q(subcat_id=similar_cat) | Q(scat_id=similar_parent_cat)).filter(approval_status=2).exclude(id=id).exclude(id__in=register_course_ids).order_by('scat_id')                               
    for i in similar_courses:
        rating_list = course_comments.objects.filter(course_id_id=i.id)
        i.rating = getRatingFunc(rating_list)
        i.ratingCnt = course_comments.objects.filter(course_id_id=i.id).count()
        if discount.count() == 0:
            discount_percent = 1
        else:
            if now > discount[0].expire_date:
                discount_percent = 1
            else:
                not_str = discount[0].not_apply_course
                not_list = not_str.split('.')
                if str(i.id) in not_list:
                    discount_percent = 1
                else:
                    discount_percent = (100 - discount[0].discount) / 100
        i.discount_price = round(i.price * discount_percent, 2)

    similar_courses = sorted(similar_courses, key=attrgetter('rating'), reverse=True)[:3]
    for i in similar_courses:
        i.link = courseUrlGenerator(i)
        stuList = course_comments.objects.filter(course_id_id=i.id)
        i.stuCnt = len(stuList)
        i.video = getVideoCnt(i)

    data = get_courseDetails(id)

    # if user_type == 'teacher' or user_type == 'stuteach':
    #     obj_comment = course_comments.objects.filter(course_id_id=id)
    # else:
    #     obj_comment = course_comments.objects.filter(course_id_id=id).filter(user_id=user_id)
    obj_comment = course_comments.objects.filter(course_id_id=id)
    for comment in obj_comment:
        if Courses.objects.filter(id=comment.course_id_id).exists():
            course_tmp = Courses.objects.get(pk=comment.course_id_id)
            comment.teacher_name = course_tmp.user_name
            comment.teacher_img = User.objects.get(pk=course_tmp.user_id).image
        else:
            comment.teacher_name = ''
            comment.teacher_img = ''

    dict = {}

    # show fav page.., cart page...
    favList = student_favourite_courses.objects.filter(student_id_id=request.user.id)
    alreadyinFav = student_favourite_courses.objects.values('course_id_id').filter(student_id_id=request.user.id)
    alreadyinFavView = []

    for value in range(len(alreadyinFav)):
        alreadyinFavView.append(alreadyinFav[value]['course_id_id'])

    cartList = student_cart_courses.objects.filter(student_id_id=request.user.id)
    alreadyinCart = student_cart_courses.objects.values('course_id_id').filter(student_id_id=request.user.id)
    alreadyinCartView = []

    for value in range(len(alreadyinCart)):
        alreadyinCartView.append(alreadyinCart[value]['course_id_id'])

    cartTotalSum = 0

    for cart in cartList:
        cartTotalSum += cart.course_id.price

    favListShow, favCnt, alreadyinFavView, cartListShow, cartCnt, alreadyinCartView, cartTotalSum, noti_list, noti_cnt, msg_list, msg_cnt, stu_msg_list, stu_msg_cnt, total_msg_cnt = findheader(
        request.user.id)

    teacher_id = Courses.objects.get(pk=id).user_id

    user_info = User.objects.get(pk=teacher_id)
    user_info.url_name = user_info.first_name+ " " + user_info.last_name
    user_info.url_name = re.sub(r"\s+", '-', user_info.url_name)

    free_course = Courses.objects.filter(user_id=teacher_id).filter(type=1).filter(approval_status=2).count()
    paid_course = Courses.objects.filter(user_id=teacher_id).filter(type=0).filter(approval_status=2).count()

    rating_list = course_comments.objects.filter(course_id_id=course.id)

    course.rating = getRatingFunc(rating_list)
    stuList = student_register_courses.objects.filter(course_id_id=course.id)
    course.student = len(stuList)

    cur_course = Courses.objects.get(pk=id)
    is_me = 0
    if request.user.id == cur_course.user_id:
        is_me = 1
    promo_video = ''
    videocounter = 0
    _obj = []
    if Sections.objects.filter(course_id=id).exists():
        _obj = Sections.objects.filter(course_id=id, type="video")
        count = 0
        videocounter = 0
        includeList = []
        for i in _obj:
            if VideoUploads.objects.filter(section_id=i.id).exists():
                eleDict = []
                video_obj = VideoUploads.objects.filter(section_id=i.id)
                for j in video_obj:
                    myDict = {}
                    count += 1
                    myDict["sr_no"] = count
                    myDict["video"] = j
                    videocounter += 1
                    eleDict.append(myDict)
                i.videoList = eleDict
                i.tname = re.sub(r'[^\w]', '', i.name)
            if VideoUploads.objects.filter(section_id=i.id, promo=1).exists():
                promo_video = VideoUploads.objects.filter(section_id=i.id, promo=1)[0].url

    fav_exist = 0
    if student_favourite_courses.objects.filter(student_id_id=user_id, course_id_id=course.id).exists():
        fav_exist = 1
    cart_exist = 0
    if student_cart_courses.objects.filter(student_id_id=user_id, course_id_id=course.id).exists():
        cart_exist = 1

    stu_courses = student_register_courses.objects.filter(student_id_id=request.user.id)
    return render(request, 'single_course.html',
                  {'videocount': videocounter, "lang": getLanguage(request)[0], 'question_list': data['question_list'],
                   'course': course, 'similar_courses': similar_courses, 'user_type': user_type, "user_id": user_id,
                   "comment_list": obj_comment, 'id': id, 'user_info': user_info, 'free_course': free_course,
                   'teacher_id': teacher_id, 'stu_courses':stu_courses,
                   'paid_course': paid_course, 'includeList': _obj, 'favList': favListShow, 'promo_video': promo_video,
                   'alreadyinFav': alreadyinFavView, 'cartList': cartListShow, 'alreadyinCart': alreadyinCartView,
                   'favCnt': len(favList), 'cartCnt': len(cartList), 'cartTotalSum': cartTotalSum, 'noti_cnt': noti_cnt,
                   'noti_list': noti_list, 'is_me': is_me, 'fav_exist': fav_exist, 'cart_exist': cart_exist,
                   'msg_list': msg_list, 'msg_cnt': msg_cnt, 'stu_msg_list': stu_msg_list, 'stu_msg_cnt': stu_msg_cnt, 'total_msg_cnt': total_msg_cnt})


@csrf_exempt
def add_comment(request):
    course_id = request.POST.get("course_id")
    comment = request.POST.get("comment")
    # comment_id = request.POST.get("comment_id")
    rating = request.POST.get("rating")
    rating = float(rating or 0)
    user_id = request.POST.get("user_id")
    # dt = datetime.datetime.now()
    dt = datetime.now()

    if course_comments.objects.filter(course_id_id=course_id, user_id=user_id).exists():
        existRec = course_comments.objects.filter(course_id_id=course_id, user_id=user_id)[0]
        existRec.comment = comment
        existRec.rating = rating
        existRec.date = dt
        existRec.save()
    else:
        obj = course_comments(user_id=user_id, course_id_id=course_id, comment=comment, date=dt, rating=rating)
        obj.save()

    return HttpResponse("success")


def delete_comment(request):
    course_id = request.POST.get("id")
    obj = course_comments.objects.get(pk=course_id)
    print("delete", obj)
    obj.delete()
    return HttpResponse("success")


def get_teacher_CourseList(request):
    user_id = request.session.get("user_id")
    user_type = request.session.get("user_type")

    print(user_id)
    print(user_type)

    course_list = []
    course_list = Courses.objects.filter(user_id=user_id)
    return course_list


# check here farabi
@csrf_exempt
def student_courses(request):
    student_id = request.POST.get('student')
    course_id = request.POST.get('course')

    txt = '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">'
    txt += '<html xmlns="http://www.w3.org/1999/xhtml">'
    txt += '<head>'
    txt += '<meta http-equiv="Content-Type" content="text/html; charset=utf-8" /><meta http-equiv="X-UA-Compatible" content="IE=edge">'
    txt += '<meta name="viewport" content="width=device-width, initial-scale=1">'
    txt += '<title>Thanks for purchase Course</title>'
    txt += '</head>'
    txt += '<body leftmargin="0" marginwidth="0" topmargin="0" marginheight="0" offset="0" bgcolor="#ffffff" style="margin-top: 0;margin-bottom: 0;padding-top: 0;padding-bottom: 0;-webkit-text-size-adjust: 100%;-ms-text-size-adjust: 100%;-webkit-font-smoothing: antialiased;width: 100%;">'
    txt += '<div class="navbar-brand" style="float: unset;padding: unset;height: unset;"><h4 style="font-weight: 900">Hello ' + request.user.first_name + '! Congratlations! </h4></div>'
    txt += '</body>'
    txt += '</html>'

    to = request.user.email
    subject = 'Thanks :)'

    msg = EmailMultiAlternatives(subject, '', '', [to])
    msg.attach_alternative(txt, "text/html")
    msg.send()

    if student_register_courses.objects.filter(student_id_id=student_id, course_id_id=course_id).exists():
        return HttpResponse("error")
    else:
        obj = student_register_courses(student_id_id=student_id, course_id_id=course_id)
        obj.save()

    return HttpResponse("success")


@csrf_exempt
def student_Cart_courses(request):
    student_id = request.POST.get('student')
    course_id = request.POST.get('course')
    cartUpdatedView = []
    if student_id == 'None':
        return HttpResponse("require_login")
    else:
        if student_cart_courses.objects.filter(student_id_id=student_id, course_id_id=course_id).exists() == 0:
            obj = student_cart_courses(student_id_id=student_id, course_id_id=course_id)
            obj.save()
            cartUpdatedViewQuerySet = Courses.objects.filter(id=course_id)
            cartUpdatedView = serializers.serialize('json', cartUpdatedViewQuerySet)
            return HttpResponse(cartUpdatedView, content_type='application/json')
        else:
            student_cart_courses.objects.filter(student_id_id=student_id, course_id_id=course_id).delete()
            return HttpResponse("success")


@csrf_exempt
def delete_Cart_course_single(request):
    student_id = request.POST.get('student')
    course_id = request.POST.get('course')

    if student_cart_courses.objects.filter(student_id_id=student_id, course_id_id=course_id).exists() == 1:
        student_cart_courses.objects.filter(student_id_id=student_id, course_id_id=course_id).delete()

    cartList = student_cart_courses.objects.filter(student_id_id=request.user.id)
    cartTotalSum = 0

    for cart in cartList:
        cartTotalSum += cart.course_id.price

    data = {'cartTotalSum': cartTotalSum}

    return JsonResponse(data)


@csrf_exempt
def delete_Cart_courses_all(request):
    student_id = request.POST.get('student')

    if student_cart_courses.objects.filter(student_id_id=student_id).exists() == 1:
        student_cart_courses.objects.filter(student_id_id=student_id).delete()

    cartTotalSum = 0

    data = {'cartTotalSum': cartTotalSum}

    return JsonResponse(data)


@csrf_exempt
def student_Favourite_courses(request):
    print("test:::", type(request.POST.get('student')))
    course_id = request.POST.get('course')
    if request.POST.get('student') is None or request.POST.get('student') == '':
        return HttpResponse("require_login")
    else:
        student_id = request.POST.get('student')
        favUpdatedView = []
        if student_favourite_courses.objects.filter(student_id_id=student_id, course_id_id=course_id).exists() == 0:
            obj = student_favourite_courses(student_id_id=student_id, course_id_id=course_id)
            obj.save()
            favUpdatedViewQuerySet = Courses.objects.filter(id=course_id)
            favUpdatedView = serializers.serialize('json', favUpdatedViewQuerySet)
            return HttpResponse(favUpdatedView, content_type='application/json')

        else:
            student_favourite_courses.objects.filter(student_id_id=student_id, course_id_id=course_id).delete()
            return HttpResponse("success");


@csrf_exempt
def delete_Favourite_course_single(request):
    student_id = request.POST.get('student')
    course_id = request.POST.get('course')

    if student_favourite_courses.objects.filter(student_id_id=student_id, course_id_id=course_id).exists() == 1:
        student_favourite_courses.objects.filter(student_id_id=student_id, course_id_id=course_id).delete()

    favList = student_favourite_courses.objects.filter(student_id_id=request.user.id)
    favTotalSum = 0

    for fav in favList:
        favTotalSum += fav.course_id.price

    data = {'favTotalSum': favTotalSum}

    return JsonResponse(data)


@csrf_exempt
def delete_Favourite_courses_all(request):
    student_id = request.POST.get('student')

    if student_favourite_courses.objects.filter(student_id_id=student_id).exists() == 1:
        student_favourite_courses.objects.filter(student_id_id=student_id).delete()

    favTotalSum = 0

    data = {'favTotalSum': favTotalSum}

    return JsonResponse(data)


def check_email(request):
    msg = ''
    try:

        email = request.POST.get('email')

        lstUsers = User.objects.filter(email=email)
        if len(lstUsers) > 0:
            msg = 'already'
        else:

            msg = 'success'
    except:
        tb = sys.exc_info()[2]
        tbinfo = traceback.format_tb(tb)[0]
        msg = tbinfo + "\n" + ": " + str(sys.exc_info())

    to_return = {'msg': msg}
    serialized = json.dumps(to_return)
    return HttpResponse(serialized, content_type="application/json")


def getsubcategory(request):
    msg = ''
    try:
        category_id = request.POST.get('category_id')
        subcat_list = []
        objC = subcategories.objects.filter(categories_id=int(category_id))
        for subcat in objC:
            item = {'name': subcat.name, 'namear': subcat.namear, 'image': subcat.image,
                    'category_name': subcat.categories.name,
                    'id': subcat.id}
            subcat_list.append(item)
        msg = 'success'
    except:
        tb = sys.exc_info()[2]
        tbinfo = traceback.format_tb(tb)[0]
        msg = tbinfo + "\n" + ": " + str(sys.exc_info())

    to_return = {'msg': 'success', 'subcat_list': subcat_list}
    serialized = json.dumps(to_return)
    return HttpResponse(serialized, content_type="application/json")


def saveimg(request):
    msg = ''
    try:
        myfile = request.FILES['file']
        filename = myfile._get_name()

        ext = filename[filename.rfind('.'):]
        file_name = str(uuid.uuid4()) + ext
        path = '/user_images/'
        full_path = str(path) + str(file_name)
        fd = open('%s/%s' % (settings.STATICFILES_DIRS[0], str(path) + str(file_name)), 'wb')
        for chunk in myfile.chunks():
            fd.write(chunk)
        fd.close()
        msg = 'success'
    except:
        tb = sys.exc_info()[2]
        tbinfo = traceback.format_tb(tb)[0]
        msg = tbinfo + "\n" + ": " + str(sys.exc_info())

    #
    to_return = {'msg': msg}
    serialized = json.dumps(to_return)
    return HttpResponse(serialized, content_type="application/json")


def register_user(request):
    msg = ''
    try:
        firstname = request.POST.get('first_name')
        lastname = request.POST.get('last_name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        phone_number = request.POST.get('phone_number')
        subcategory_id = request.POST.get('subcategory')
        type = request.POST.get('type')
        group_id = 1
        lstUsers = User.objects.filter(email=email)
        coun = User.objects.filter(email=email).count()
        if coun > 0:
            msg = 'already'
        else:
            try:
                myfile = request.FILES['file']
                filename = myfile._get_name()

                ext = filename[filename.rfind('.'):]
                file_name = str(uuid.uuid4()) + ext
                path = '/user_images/'
                full_path = str(path) + str(file_name)
                fd = open('%s/%s' % (settings.STATICFILES_DIRS[0], str(path) + str(file_name)), 'wb')
                for chunk in myfile.chunks():
                    fd.write(chunk)
                fd.close()
            except:
                full_path = '/assets/img/man.jpg'
            dt = datetime.now()
            objUser = User(email=email, first_name=firstname, last_name=lastname, phone_number=phone_number,
                           password=password, is_staff=False, is_active=False, image=full_path, is_superuser=False,
                           date_joined=dt)

            objUser.set_password(password)

            if type == "teacher":
                group_id = 3
            elif type == "student":
                group_id = 2

            if Group.objects.filter(id=group_id).exists():
                group = Group.objects.get(id=group_id)

            else:
                group = Group(id=group_id)
                group.save()

            objUser.group = group
            objUser.save()
            objUA = user_activation()
            objUA.user = objUser
            objUA.code = str(uuid.uuid4())
            objUA.email = email
            objUA.save()
            user_group_id = str(objUser.group_id)

            # if user_group_id == "2":
            #     request.session['user_id'] = str(objUser.id)
            #     request.session['user_type'] = "student"
            # else:
            #     request.session['user_id'] = str(objUser.id)
            #     request.session['user_type'] = "teacher"

            if type == "teacher":
                print("subcategori ID: ", subcategory_id)
                objSubCat = subcategories.objects.get(id=subcategory_id)
                print("heeerrrr", objSubCat)
                objUS = user_categories()
                objUS.user = objUser
                objUS.category = objSubCat
                objUS.save()
            request.session['password'] = password
            domain = request.META['HTTP_HOST']
            msg = 'success'
            sendConfirmationMail(objUA, domain, user_group_id, request)
    except:
        tb = sys.exc_info()[2]
        tbinfo = traceback.format_tb(tb)[0]
        msg = tbinfo + "\n"     ": " + str(sys.exc_info())

    to_return = {'msg': msg}
    serialized = json.dumps(to_return)
    return HttpResponse(serialized, content_type="application/json")


# Store updated profile in DB
def updateUserProfile(data):
    user_id = data.user.id
    bio = data.POST.get('acc_bio')
    cat_id = data.POST.get('cat_id')
    subcat_ids = data.POST.get('subcat_ids')
    facebook_url = data.POST.get('facebook_url')
    instagram_url = data.POST.get('instagram_url')
    twitter_url = data.POST.get('twitter_url')
    website_url = data.POST.get('website_url')
    is_notification = data.POST.get('is_notification')
    if facebook_url == 'undefined' or facebook_url == None:
        facebook_url = ''
    if instagram_url == 'undefined' or instagram_url == None:
        instagram_url = ''
    if twitter_url == 'undefined' or twitter_url == None:
        twitter_url = ''
    if website_url == 'undefined' or website_url == None:
        website_url = ''

    status = 1
    print
    try:
        if user_profile.objects.filter(user_id=user_id).exists():
            objProfile = user_profile.objects.get(user_id=user_id)
            objProfile.bio = bio
            objProfile.cat_id = cat_id
            objProfile.subcat_ids = subcat_ids
            objProfile.facebook_url = facebook_url
            objProfile.instagram_url = instagram_url
            objProfile.twitter_url = twitter_url
            objProfile.website_url = website_url
            objProfile.notification = is_notification
        else:
            objProfile = user_profile(
                user_id=user_id,
                bio=bio,
                cat_id=cat_id,
                subcat_ids=subcat_ids,
                facebook_url=facebook_url,
                instagram_url=instagram_url,
                twitter_url=twitter_url,
                website_url=website_url,
                notification=is_notification,
            )

            objProfile.save()
    except:
        status = 0
    try:
        myfile = data.FILES['file2']
        filename = myfile._get_name()
        ext = filename[filename.rfind('.'):]
        file_name = str(uuid.uuid4()) + ext
        path = '/user_images/'
        full_path = str(path) + str(file_name)

        fd = open('%s/%s' % (settings.STATICFILES_DIRS[0], str(path) + str(file_name)), 'wb')
        for chunk in myfile.chunks():
            fd.write(chunk)
        fd.close()
    except:
        full_path = objProfile.header_img
    objProfile.header_img = full_path
    objProfile.save()


def update_user(request):
    msg = ''
    try:
        firstname = request.POST.get('first_name')
        lastname = request.POST.get('last_name')
        email = request.POST.get('email')
        objU = User.objects.get(email=email, id=request.user.id)

        # update user profile
        user_type = request.session['user_type']
        if user_type == 'teacher' or user_type == 'stuteach':
            updateUserProfile(request)
        try:
            myfile = request.FILES['file']
            filename = myfile._get_name()
            ext = filename[filename.rfind('.'):]
            file_name = str(uuid.uuid4()) + ext
            path = '/user_images/'
            full_path = str(path) + str(file_name)

            fd = open('%s/%s' % (settings.STATICFILES_DIRS[0], str(path) + str(file_name)), 'wb')
            for chunk in myfile.chunks():
                fd.write(chunk)
            fd.close()
        except:
            full_path = objU.image
        objU.first_name = firstname
        objU.last_name = lastname
        objU.image = full_path
        objU.save()
        msg = 'success'

    except:
        tb = sys.exc_info()[2]
        tbinfo = traceback.format_tb(tb)[0]
        msg = tbinfo + "\n"     ": " + str(sys.exc_info())

    to_return = {'msg': msg}
    serialized = json.dumps(to_return)
    return HttpResponse(serialized, content_type="application/json")


def sendConfirmationMail(objUA, domain, user_group_id, request):
    connection = get_connection()  # uses SMTP server specified in settings.py
    connection.open()  # If you don't open the connection manually, Django will automatically open, then tear down the connection in msg.send()
    imageLink = f"https://booctep.herokuapp.com/static/assets/img/favicon.png"
    try:
        link = 'http://' + domain + '/activation?code=' + objUA.code
        text = '<!DOCTYPE HTML PUBLIC "-//W3C//DTD XHTML 1.0 Transitional //EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">'
        text += '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">'
        text += '<head><!--[if gte mso 9]><xml><o:OfficeDocumentSettings><o:AllowPNG/><o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings></xml><![endif]--><meta http-equiv="Content-Type" content="text/html; charset=UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><meta name="x-apple-disable-message-reformatting"><!--[if !mso]><!-->'
        text += '<meta http-equiv="X-UA-Compatible" content="IE=edge"><!--<![endif]--><title></title><style type="text/css">table, td { color: #000000; } a { color: #0000ee; text-decoration: underline; } @media (max-width: 480px) { #u_content_button_4 .v-padding { padding: 20px 50px !important; } }'
        text += '@media only screen and (min-width: 620px) {.u-row { width: 600px !important;}.u-row .u-col {vertical-align: top;}.u-row .u-col-100 {width: 600px !important;}}'
        text += '@media (max-width: 620px) {.u-row-container {max-width: 100% !important;padding-left: 0px !important;padding-right: 0px !important;}.u-row .u-col {min-width: 320px !important;max-width: 100% !important;display: block !important;}'
        text += '.u-row {width: calc(100% - 40px) !important;}.u-col {width: 100% !important;}.u-col > div {margin: 0 auto;}}body {margin: 0;padding: 0;}table,tr,td {vertical-align: top;border-collapse: collapse;}p {margin: 0;}'
        text += '.ie-container table,.mso-container table {table-layout: fixed;}* {line-height: inherit;}a[x-apple-data-detectors="true"] {color: inherit !important;text-decoration: none !important;}</style>'
        text += '<!--[if !mso]><!--><link href="https://fonts.googleapis.com/css?family=Lato:400,700&display=swap" rel="stylesheet" type="text/css"><link href="https://fonts.googleapis.com/css?family=Open+Sans:400,700&display=swap" rel="stylesheet" type="text/css"><link href="https://fonts.googleapis.com/css?family=Raleway:400,700&display=swap" rel="stylesheet" type="text/css"><!--<![endif]--></head>'
        text += '<body class="clean-body" style="margin: 0;padding: 0;-webkit-text-size-adjust: 100%;background-color: #efefef;color: #000000"><!--[if IE]><div class="ie-container"><![endif]--><!--[if mso]><div class="mso-container"><![endif]--><table style="border-collapse: collapse;table-layout: fixed;border-spacing: 0;mso-table-lspace: 0pt;mso-table-rspace: 0pt;vertical-align: top;min-width: 320px;Margin: 0 auto;background-color: #efefef;width:100%" cellpadding="0" cellspacing="0"><tbody><tr style="vertical-align: top"><td style="word-break: break-word;border-collapse: collapse !important;vertical-align: top"><!--[if (mso)|(IE)]><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td align="center" style="background-color: #efefef;"><![endif]--><div class="u-row-container" style="padding: 0px;background-color: transparent"><div class="u-row" style="Margin: 0 auto;min-width: 320px;max-width: 600px;overflow-wrap: break-word;word-wrap: break-word;word-break: break-word;background-color:   #d7dbf5;"><div style="border-collapse: collapse;display: table;width: 100%;background-color: transparent;"><!--[if (mso)|(IE)]><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td style="padding: 0px;background-color: transparent;" align="center"><table cellpadding="0" cellspacing="0" border="0" style="width:600px;"><tr style="background-color: #0000ff;"><![endif]--><!--[if (mso)|(IE)]><td align="center" width="600" style="width: 600px;padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;" valign="top"><![endif]--><div class="u-col u-col-100" style="max-width: 320px;min-width: 600px;display: table-cell;vertical-align: top;"><div style="width: 100% !important;"><!--[if (!mso)&(!IE)]><!--><div style="padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;"><!--<![endif]-->'
        text += '<table style="font-family:Open Sans,sans-serif;" role="presentation" cellpadding="0" cellspacing="0" width="100%" border="0"><tbody><tr><td style="overflow-wrap:break-word;word-break:break-word;padding:10px;font-family:Open Sans,sans-serif;" align="left"><table width="100%" cellpadding="0" cellspacing="0" border="0" ><tr>'
        text += f'<td style="padding-right: 0px;padding-left: 0px;" align="center"><img align="center" border="0" src="{imageLink}" alt="Image" title="Image" style="outline: none;text-decoration: none;-ms-interpolation-mode: bicubic;clear: both;display: inline-block !important;border: none;height: auto;float: none;width: 100%;max-width: 80px;" width="80">'
        text += '</td></tr></table></td></tr></tbody></table><!--[if (!mso)&(!IE)]><!--></div><!--<![endif]--></div></div><!--[if (mso)|(IE)]></td><![endif]--><!--[if (mso)|(IE)]></tr></table></td></tr></table><![endif]--></div></div></div>'
        text += '<div class="u-row-container" style="padding: 0px;background-color: transparent"><div class="u-row" style="Margin: 0 auto;min-width: 320px;max-width: 600px;overflow-wrap: break-word;word-wrap: break-word;word-break: break-word;background-color: #ffffff;"><div style="border-collapse: collapse;display: table;width: 100%;background-color: transparent;">'
        text += '<!--[if (mso)|(IE)]><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td style="padding: 0px;background-color: transparent;" align="center"><table cellpadding="0" cellspacing="0" border="0" style="width:600px;"><tr style="background-color: #ffffff;"><![endif]--><!--[if (mso)|(IE)]><td align="center" width="600" style="width: 600px;padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;" valign="top"><![endif]--><div class="u-col u-col-100" style="max-width: 320px;min-width: 600px;display: table-cell;vertical-align: top;"><div style="width: 100% !important;"><!--[if (!mso)&(!IE)]><!--><div style="padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;"><!--<![endif]--><table style="font-family:Open Sans,sans-serif;" role="presentation" cellpadding="0" cellspacing="0" width="100%" border="0" >'
        text += '<tbody><tr><td style="overflow-wrap:break-word;word-break:break-word;padding:18px 10px 12px;font-family:Open Sans,sans-serif;" align="left"><div style="color: #333333; line-height: 140%; text-align: center; word-wrap: break-word;"><p style="font-size: 14px; line-height: 140%;">'
        text += '<span style="font-size: 22px; line-height: 30.8px;"><strong>Thank you for signup in Booctep</strong></span></p></div></td></tr></tbody></table><!--[if (!mso)&(!IE)]><!--></div><!--<![endif]--></div></div><!--[if (mso)|(IE)]></td><![endif]--><!--[if (mso)|(IE)]></tr></table></td></tr></table><![endif]--></div></div></div><div class="u-row-container" style="padding: 0px;background-color: transparent">'
        text += '<div class="u-row" style="Margin: 0 auto;min-width: 320px;max-width: 600px;overflow-wrap: break-word;word-wrap: break-word;word-break: break-word;background-color: #ffffff;"><div style="border-collapse: collapse;display: table;width: 100%;background-color: transparent;">'
        text += '<!--[if (mso)|(IE)]><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td style="padding: 0px;background-color: transparent;" align="center"><table cellpadding="0" cellspacing="0" border="0" style="width:600px;"><tr style="background-color: #ffffff;"><![endif]-->'
        text += '<!--[if (mso)|(IE)]><td align="center" width="600" style="width: 600px;padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;" valign="top"><![endif]--><div class="u-col u-col-100" style="max-width: 320px;min-width: 600px;display: table-cell;vertical-align: top;"><div style="width: 100% !important;"><!--[if (!mso)&(!IE)]><!--><div style="padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;"><!--<![endif]-->'
        text += '<table style="font-family:Open Sans,sans-serif;" role="presentation" cellpadding="0" cellspacing="0" width="100%" border="0" ><tbody><tr>'
        text += '<td style="overflow-wrap:break-word;word-break:break-word;padding:0px 25px 10px;font-family:Open Sans,sans-serif;" align="left"><div style="color: #333333; line-height: 160%; text-align: center; word-wrap: break-word;"><p style="font-size: 14px; line-height: 160%; text-align: left;">Hello ' + objUA.user.first_name + '</br>To activate your account please click button bellow</p></div></td></tr></tbody></table><!--[if (!mso)&(!IE)]><!--></div><!--<![endif]--></div></div><!--[if (mso)|(IE)]></td><![endif]--><!--[if (mso)|(IE)]></tr></table></td></tr></table><![endif]--></div></div></div><div class="u-row-container" style="padding: 0px;background-color: transparent"><div class="u-row" style="Margin: 0 auto;min-width: 320px;max-width: 600px;overflow-wrap: break-word;word-wrap: break-word;word-break: break-word;background-color: #ffffff;"><div style="border-collapse: collapse;display: table;width: 100%;background-color: transparent;">'
        text += '<!--[if (mso)|(IE)]><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td style="padding: 0px;background-color: transparent;" align="center"><table cellpadding="0" cellspacing="0" border="0" style="width:600px;"><tr style="background-color: #ffffff;"><![endif]-->'
        text += '<!--[if (mso)|(IE)]><td align="center" width="600" style="width: 600px;padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;" valign="top"><![endif]-->'
        text += '<div class="u-col u-col-100" style="max-width: 320px;min-width: 600px;display: table-cell;vertical-align: top;"><div style="width: 100% !important;"><!--[if (!mso)&(!IE)]><!--><div style="padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;"><!--<![endif]--><table id="u_content_button_4" style="font-family:Open Sans,sans-serif;" role="presentation" cellpadding="0" cellspacing="0" width="100%" border="0"><tbody><tr><td style="overflow-wrap:break-word;word-break:break-word;padding:10px;font-family:Open Sans,sans-serif;" align="left"><div align="center"><!--[if mso]><table width="100%" cellpadding="0" cellspacing="0" border="0" style="border-spacing: 0; border-collapse: collapse; mso-table-lspace:0pt; mso-table-rspace:0pt;font-family:Open Sans,sans-serif;"><tr><td style="font-family:Open Sans,sans-serif;" align="center"><v:roundrect xmlns:v="urn:schemas-microsoft-com:vml" xmlns:w="urn:schemas-microsoft-com:office:word" href="" style="height:38px; v-text-anchor:middle; width:274px;" arcsize="92%" stroke="f" fillcolor="#1b36ab"><w:anchorlock/><center style="color:#FFFFFF;font-family:Open Sans,sans-serif;"><![endif]-->'
        text += '<a href="' + link + '" target="_blank" style="box-sizing: border-box;display: inline-block;font-family:Open Sans,sans-serif;text-decoration: none;-webkit-text-size-adjust: none;text-align: center;color: #FFFFFF; background-color: #1b36ab; border-radius: 35px; -webkit-border-radius: 35px; -moz-border-radius: 35px; width:auto; max-width:100%; overflow-wrap: break-word; word-break: break-word; word-wrap:break-word; mso-border-alt: none;"><span class="v-padding" style="display:block;padding:12px 40px 10px;line-height:120%;"><span style="font-size: 14px; line-height: 16.8px;"><strong><span style="line-height: 16.8px; font-size: 14px;"> A c t i v a t e </span></strong></span></span></a><!--[if mso]></center></v:roundrect></td></tr></table><![endif]--></div></td></tr></tbody></table>'
        text += '<!--[if (!mso)&(!IE)]><!--></div><!--<![endif]--></div></div><!--[if (mso)|(IE)]></td><![endif]--><!--[if (mso)|(IE)]></tr></table></td></tr></table><![endif]--></div></div></div><div class="u-row-container" style="padding: 0px;background-color: transparent"><div class="u-row" style="Margin: 0 auto;min-width: 320px;max-width: 600px;overflow-wrap: break-word;word-wrap: break-word;word-break: break-word;background-color: #ffffff;"><div style="border-collapse: collapse;display: table;width: 100%;background-color: transparent;">'
        text += '<!--[if (mso)|(IE)]><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td style="padding: 0px;background-color: transparent;" align="center"><table cellpadding="0" cellspacing="0" border="0" style="width:600px;"><tr style="background-color: #ffffff;"><![endif]--><!--[if (mso)|(IE)]><td align="center" width="600" style="width: 600px;padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;" valign="top"><![endif]--><div class="u-col u-col-100" style="max-width: 320px;min-width: 600px;display: table-cell;vertical-align: top;"><div style="width: 100% !important;"><!--[if (!mso)&(!IE)]><!-->'
        text += '<div style="padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;">'
        text += '<!--<![endif]--><table style="font-family:Open Sans,sans-serif;" role="presentation" cellpadding="0" cellspacing="0" width="100%" border="0"><tbody><tr><td style="overflow-wrap:break-word;word-break:break-word;padding:15px 10px 9px;font-family:Open Sans,sans-serif;" align="left">'
        text += '<table height="0px" align="center" border="0" cellpadding="0" cellspacing="0" width="72%" style="border-collapse: collapse;table-layout: fixed;border-spacing: 0;mso-table-lspace: 0pt;mso-table-rspace: 0pt;vertical-align: top;border-top: 1px solid #413d45;-ms-text-size-adjust: 100%;-webkit-text-size-adjust: 100%"><tbody><tr style="vertical-align: top">'
        text += '<td style="word-break: break-word;border-collapse: collapse !important;vertical-align: top;font-size: 0px;line-height: 0px;mso-line-height-rule: exactly;-ms-text-size-adjust: 100%;-webkit-text-size-adjust: 100%">'
        text += '<span>&#160;</span></td></tr></tbody></table></td></tr></tbody></table><table style="font-family:Open Sans,sans-serif;" role="presentation" cellpadding="0" cellspacing="0" width="100%" border="0">'
        text += '<tbody><tr><td style="overflow-wrap:break-word;word-break:break-word;padding:10px;font-family:Open Sans,sans-serif;" align="left"><div style="color: #7e7e81; line-height: 150%; text-align: center; word-wrap: break-word;"><p style="font-size: 14px; line-height: 150%;">'
        text += '<span style="font-size: 12px; line-height: 18px;">You have received this email as a registered user of Booctep.com</span><span style="font-size: 12px; line-height: 18px;"></span>'
        text += '</p></div></td></tr></tbody></table><!--[if (!mso)&(!IE)]><!--></div><!--<![endif]--></div></div><!--[if (mso)|(IE)]></td><![endif]--><!--[if (mso)|(IE)]></tr></table></td></tr></table><![endif]--></div></div></div><!--[if (mso)|(IE)]></td></tr></table><![endif]--></td></tr></tbody></table><!--[if mso]></div><![endif]--><!--[if IE]></div><![endif]--></body></html>'

        to = objUA.email

        subject = 'Thanks for activating your email, welcome!'
        msg = EmailMultiAlternatives(subject, '...', 'support@booctep.com', [to])
        msg.attach_alternative(text, "text/html")
        msg.send()
    except:
        tb = sys.exc_info()[2]
        tbinfo = traceback.format_tb(tb)[0]
        msg = tbinfo + "\n" + ": " + str(sys.exc_info())
        msg = tbinfo + "\n" + ": " + str(sys.exc_info())

    connection.close()  # Cleanup


def activated(request):
    return render(request, 'activated.html', {'lang': getLanguage(request)[0]})

def activation(request):
    cod = request.GET.get('code')
    lenobj = user_activation.objects.get(code=cod)
    # lenobj.code = str(uuid.uuid4())
    lenobj.code = "33333-99999-77777"
    lenobj.save()
    user_id = lenobj.user_id
    user_object = User.objects.get(id=user_id)

    user_object.is_active = True
    user_object.save()

    email = user_object.email
    password = request.session['password']

    objU = authenticate(email=email, password=password)
    login(request, objU)

    request.session['user_id'] = str(user_id)
    user_group_id = user_object.group_id
    if user_group_id == "2":
        request.session['user_type'] = "student"
    else:
        request.session['user_type'] = "teacher"

    return HttpResponseRedirect("/" + request.LANGUAGE_CODE + "/activated")


@csrf_exempt
def ajaxlogin(request):
    msg = ''
    try:
        email = request.POST.get('email')
        password = request.POST.get('password')
        remember = request.POST.get('remember')
        objU = authenticate(email=email, password=password)
        obj = User.objects.get(email=email)
        if objU is not None:
            if objU.is_active == True:
                login(request, objU)
                obj = User.objects.get(email=email)
                user_id = obj.id
                # id = str(obj.group_id)
                # print('LoginId-------', "kl:",id)
                id = obj.group_id

                if remember == 'true':
                    request.session['user_id'] = request.POST.get('email')
                    request.session['password'] = request.POST.get('password')
                    request.session['remember'] = request.POST.get('remember')

                if id == 2:
                    request.session['user_id'] = str(user_id)
                    request.session['user_type'] = "student"
                elif id == 3:
                    request.session['user_id'] = str(user_id)
                    request.session['user_type'] = "teacher"
                else:
                    request.session['user_id'] = str(user_id)
                    request.session['user_type'] = "stuteach"
                request.session['password'] = request.POST.get('password')
                msg = 'success'
            else:
                msg = 'Not active'
                user_id = 0
        else:
            msg = 'error'
            user_id = 0
    except:
        tb = sys.exc_info()[2]
        tbinfo = traceback.format_tb(tb)[0]
        msg = tbinfo + "\n" + ": " + str(sys.exc_info())
        user_id = 0
    to_return = {'msg': msg, 'user_id': user_id}
    serialized = json.dumps(to_return)

    return HttpResponse(serialized, content_type="application/json")


def changepassword(request):
    msg = ''
    try:
        currentpassword = request.POST.get('currentpassword')
        print("currentpassword = ", currentpassword)
        newpassword = request.POST.get('newpassword')
        print("newpassword = ", newpassword)
        print("request.user.email = ", request.user.email)
        objU = authenticate(email=request.user.email, password=currentpassword)
        print(objU)
        if objU is not None:
            print("User is authenticated")
            u = User.objects.get(email=request.user.email)
            u.set_password(newpassword)
            u.save()
            msg = 'success'
        else:
            msg = 'error'
        print("msg - ", msg)
    except:
        tb = sys.exc_info()[2]
        tbinfo = traceback.format_tb(tb)[0]
        msg = tbinfo + "\n" + ": " + str(sys.exc_info())
    to_return = {'msg': msg}
    serialized = json.dumps(to_return)
    return HttpResponse(serialized, content_type="application/json")


def forgotpassword(request, param):
    return render(request, 'reset_password.html', {'lang': getLanguage(request)[0]})


def forgotChangepassword(request):
    msg = ''
    try:
        baseparam = request.POST.get('baseparam')
        u = User.objects.get(hash=baseparam)
        newpassword = request.POST.get('newpassword')
        u.set_password(newpassword)
        u.save()
        msg = 'success'
    except:
        tb = sys.exc_info()[2]
        tbinfo = traceback.format_tb(tb)[0]
        msg = tbinfo + "\n" + ": " + str(sys.exc_info())
    to_return = {'msg': msg}
    serialized = json.dumps(to_return)
    return render(request, 'changesuccesspage.html', {'lang': getLanguage(request)[0], 'message': msg})


def logout_(request):
    logout(request)
    url_parts = request.META['HTTP_REFERER'].split('/')

    for url_part in url_parts:
        if 'teacher' in url_part or 'student' in url_part:
            redirect_url = url_parts[0] + "//" + url_parts[2] + "/" + url_parts[3]
            return HttpResponseRedirect(redirect_url)
                
    return HttpResponseRedirect(request.META['HTTP_REFERER'])


@csrf_exempt
def search_course(request):
    print("search_course.................")
    cod = request.POST.get('inp')
    # course_list = getAllCourseList()
    course_list = []
    if cod == "":
        course_list = Courses.objects.all()
    else:
        course_list = Courses.objects.filter(name__icontains=cod)
    cnt = Courses.objects.filter(name__icontains=cod).count()
    print("cnt", cnt)
    print("lang", getLanguage(request)[0], getLanguage(request)[1])

    if getLanguage(request)[1] == None:
        print("g")
        if getLanguage(request)[0] == "":
            ln = "en"
        else:
            ln = "ar"
        if len(ur) == 1 and ur[1] == "":
            la = "en"
        else:
            la = ur[3]

        if la == ln:
            if cnt > 0:
                rendered = render_to_string('filter_course_list.html', {'course_list': course_list})
                return HttpResponse(rendered)
            else:
                rendered = render_to_string("filter_no_course.html", {"course": cod})
                return HttpResponse(rendered)
    else:
        print("jjjjjj", getLanguage(request)[1])
        ur = getLanguage(request)[1].split('/')
        print(ur)
        if getLanguage(request)[0] == "":
            ln = "en"
        else:
            ln = "ar"
        if len(ur) == 1 and ur[1] == "":
            la = "en"
        else:
            la = ur[3]

        if la == ln:
            for c in course_list:
                print("course_list", c.name, c.price)

        # rendered = render_to_string('filter_course_list.html',{'course_list': course_list})

        # return HttpResponse(rendered)
        else:
            print(getLanguage(request)[0].split('/'))
            li = getLanguage(request)[0].split('/')

            # if (li[0]=="" and len(li)==1) or (li[0]=="ar" and len(li)==2):
            # u=ur[0]+"//"+ur[2]+"/"+ln
            # else:
            # u=ur[0]+"//"+ur[2]+"/"+ln+"/"+ur[4]+"/"
            u = ur[0] + "//" + ur[2] + "/" + ln + "/" + ur[4] + "/"
            print("ur[4]", ur[4])
            if ur[4] == "":
                u = u[:len(u) - 1]
                print(ur[4])
                print("course_list", course_list)
            # rendered = render_to_string('filter_course_list.html',{'course_list': course_list})
            # return HttpResponse(rendered)
        # else:
        # return redirect(u)
        if cnt > 0:

            ul = ur[0] + "//" + ur[2] + "/" + ln + "/"
            print(getLanguage(request)[1], ul)

            # if getLanguage(request)[2] != ul:
            # print("he")
            # return render(request,'index.html',{'course_list': course_list, 'lang': getLanguage(request)[0]})
            #### return redirect('/')
            # else:
            # print("hello")
            # if ur[4]=="":
            rendered = render_to_string('filter_course_list.html', {'course_list': course_list})
            return HttpResponse(rendered)
        # else:
        # return render(request,'index.html',{'course_list': course_list, 'lang': la})
        ### return HttpResponse("success")

        else:

            rendered = render_to_string("filter_no_course.html", {"course": cod})
            return HttpResponse(rendered)


################## search engine 2
@csrf_exempt
def search_course2(request):
    print("search_course2.................")
    cod = request.POST.get('inp')
    user_id = request.session.get("user_id")
    user_type = request.session.get("user_type")
    if len(cod) > 0:
        hi_blob = TextBlob(str(cod))
        if hi_blob.detect_language() == 'ar':
            lang = 'ar'
            code = hi_blob.translate(to='en')
            print(code, type(code))
        else:
            code = cod
            lang = 'en'
    else:
        code = ""
        lang = getLanguage(request)[0]
    ####################

    course_list = []
    if cod == "":
        course_list = Courses.objects.all()
    else:
        course_list = Courses.objects.filter(name__icontains=code)
    cnt = Courses.objects.filter(name__icontains=code).count()
    print("cnt", cnt)
    print("lang", getLanguage(request)[0], getLanguage(request)[1])
    pat = getLanguage(request)[1].split('/')
    if pat[4] == "":
        if cnt > 0:
            if user_type == "student":
                rendered = render_to_string('filter_course_list.html', {'course_list': course_list, "user_id": user_id})

            else:
                rendered = render_to_string('filter_course_list.html', {'course_list': course_list})

            return HttpResponse(rendered)


        else:
            if user_type == "student":
                rendered = render_to_string("filter_no_course.html", {"course": code, "user_id": user_id})

            else:
                rendered = render_to_string("filter_no_course.html", {"course": code})

            return HttpResponse(rendered)
    else:

        response = {"status": "success", "value": cod, "lang": lang}
        print("cod", cod)
        ##############################
        print("type", type(cod))
        return JsonResponse(response)


def getRatingFunc(rating_list):
    sum = 0
    count = 0
    for rate in rating_list:
        sum += rate.rating
        count += 1
    if count == 0:
        _rating = 0
    else:
        _rating = sum / count
    return round(_rating, 1)


def getVideoCnt(course):
    ssss = Sections.objects.filter(course_id=course.id).values_list("id", flat=True)
    ssss = map(str, ssss)
    strr = ','.join(ssss)
    videoListCnt = VideoUploads.objects.extra(where=['FIND_IN_SET(section_id, "' + strr + '")']).count()
    return videoListCnt


def getVideoList(course):
    ssss = Sections.objects.filter(course_id=course.id).values_list("id", flat=True)
    ssss = map(str, ssss)
    strr = ','.join(ssss)
    videoList = VideoUploads.objects.extra(where=['FIND_IN_SET(section_id, "' + strr + '")'])
    return videoList


def getVideoDuration(filename):
    ffprobepath = "ffprobe"

    result = subprocess.run([ffprobepath, "-v", "error", "-show_entries",
                             "format=duration", "-of",
                             "default=noprint_wrappers=1:nokey=1", filename],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
    x = float(result.stdout or 0)
    y = convertToTimeFormat(x)
    return y


def convertToTimeFormat(seconds):
    seconds = seconds % (24 * 3600)
    hour = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60

    hour = int(hour)
    minutes = int(minutes)
    seconds = int(seconds)

    if hour == 0:
        show = str(minutes) + "m " + str(seconds) + "s"
        if minutes == 0:
            show = str(seconds) + "s"
    else:
        show = str(hour) + "h " + str(minutes) + "m " + str(seconds) + "s"
    # return "%dh %02dm %02ds" % (hour, minutes, seconds)
    return show


@csrf_exempt
def sort_by_category(request):
    user_id = request.session.get("user_id")
    user_type = request.session.get("user_type")
    category_id = request.POST.get("category_id")
    category_id_2 = request.POST.get("category_id_2")
    if category_id == '':
        category_id = "All"
    if category_id_2 == '':
        category_id_2 = "All"

    if category_id_2 == "All":
        if category_id == "All":
            course_list = Courses.objects.all()
            course_free_list = Courses.objects.filter(type=1)
            course_paid_list = Courses.objects.filter(type=0)
            for course in course_list:
                rating_list = course_comments.objects.filter(course_id_id=course.id)
                course.rating = getRatingFunc(rating_list)
                course.video = getVideoCnt(course)
                course.stuCnt = student_register_courses.objects.filter(course_id_id=course.id).count()
            for course in course_free_list:
                rating_list = course_comments.objects.filter(course_id_id=course.id)
                course.rating = getRatingFunc(rating_list)
                course.video = getVideoCnt(course)
                course.stuCnt = student_register_courses.objects.filter(course_id_id=course.id).count()
            for course in course_paid_list:
                rating_list = course_comments.objects.filter(course_id_id=course.id)
                course.rating = getRatingFunc(rating_list)
                course.video = getVideoCnt(course)
                course.stuCnt = student_register_courses.objects.filter(course_id_id=course.id).count()
            if user_type == "student":
                rendered = render_to_string('filter_course_list.html', {'course_list': course_list, "user_id": user_id})
                rendered1 = render_to_string('filter_course_list.html',
                                             {'course_list': course_free_list, "user_id": user_id})
                rendered2 = render_to_string('filter_course_list.html',
                                             {'course_list': course_paid_list, "user_id": user_id})
            else:
                rendered = render_to_string('filter_course_list.html', {'course_list': course_list})
                rendered1 = render_to_string('filter_course_list.html', {'course_list': course_free_list})
                rendered2 = render_to_string('filter_course_list.html', {'course_list': course_paid_list})
            # return HttpResponse()
            return JsonResponse({"rendered": rendered, "rendered1": rendered1, "rendered2": rendered2})
        elif subcategories.objects.filter(categories_id=category_id).exists():
            sub_obj = subcategories.objects.filter(categories_id=category_id)
            for i in sub_obj:
                if Courses.objects.filter(scat_id=i.id).exists():
                    obj_course = Courses.objects.filter(scat_id=i.id)
                    obj_free_course = Courses.objects.filter(scat_id=i.id).filter(type=1)
                    obj_paid_course = Courses.objects.filter(scat_id=i.id).filter(type=0)

                    for course in obj_course:
                        rating_list = course_comments.objects.filter(course_id_id=course.id)
                        course.rating = getRatingFunc(rating_list)
                        course.video = getVideoCnt(course)
                        course.stuCnt = student_register_courses.objects.filter(course_id_id=course.id).count()
                    for course in obj_free_course:
                        rating_list = course_comments.objects.filter(course_id_id=course.id)
                        course.rating = getRatingFunc(rating_list)
                        course.video = getVideoCnt(course)
                        course.stuCnt = student_register_courses.objects.filter(course_id_id=course.id).count()
                    for course in obj_paid_course:
                        rating_list = course_comments.objects.filter(course_id_id=course.id)
                        course.rating = getRatingFunc(rating_list)
                        course.video = getVideoCnt(course)
                        course.stuCnt = student_register_courses.objects.filter(course_id_id=course.id).count()
                    if user_type == "student":
                        rendered = render_to_string('filter_course_list.html',
                                                    {'course_list': obj_course, "user_id": user_id})
                        rendered1 = render_to_string('filter_course_list.html',
                                                     {'course_list': obj_free_course, "user_id": user_id})
                        rendered2 = render_to_string('filter_course_list.html',
                                                     {'course_list': obj_paid_course, "user_id": user_id})
                    else:
                        rendered = render_to_string('filter_course_list.html', {'course_list': obj_course})
                        rendered1 = render_to_string('filter_course_list.html', {'course_list': obj_free_course})
                        rendered2 = render_to_string('filter_course_list.html', {'course_list': obj_paid_course})
                else:
                    return HttpResponse("error")
                return JsonResponse({"rendered": rendered, "rendered1": rendered1, "rendered2": rendered2})
        else:
            return HttpResponse("error")
    elif category_id_2 == '1':
        if category_id == "All":
            course_list = Courses.objects.all()
            course_free_list = Courses.objects.filter(type=1)
            course_paid_list = Courses.objects.filter(type=0)

            max_rating_course = []
            max_rating_free_course = []
            max_rating_paid_course = []
            for course in course_list:
                rating_list = course_comments.objects.filter(course_id_id=course.id)
                course.rating = getRatingFunc(rating_list)
                course.video = getVideoCnt(course)
                course.stuCnt = student_register_courses.objects.filter(course_id_id=course.id).count()
            max_rating = 0

            for course in course_list:
                if course.rating >= 4.5:
                    max_rating_course.append(course)

            for course in course_free_list:
                rating_list = course_comments.objects.filter(course_id_id=course.id)
                course.rating = getRatingFunc(rating_list)
                course.video = getVideoCnt(course)
                course.stuCnt = student_register_courses.objects.filter(course_id_id=course.id).count()

            max_rating = 0
            for course in course_free_list:
                if course.rating >= 4.5:
                    max_rating_free_course.append(course)

            for course in course_paid_list:
                rating_list = course_comments.objects.filter(course_id_id=course.id)
                course.rating = getRatingFunc(rating_list)
                course.video = getVideoCnt(course)
                course.stuCnt = student_register_courses.objects.filter(course_id_id=course.id).count()

            max_rating = 0
            for course in course_paid_list:
                if course.rating >= 4.5:
                    max_rating_paid_course.append(course)

            # course_list = []
            # course_free_list = []
            # course_paid_list = []
            # if max_rating_course != '':
            # 	course_list.append(max_rating_course)
            # if max_rating_free_course != '':
            # 	course_free_list.append(max_rating_free_course)
            # if max_rating_paid_course != '':
            # 	course_paid_list.append(max_rating_paid_course)

            if user_type == "student":
                rendered = render_to_string('filter_course_list.html',
                                            {'course_list': max_rating_course, "user_id": user_id})
                rendered1 = render_to_string('filter_course_list.html',
                                             {'course_list': max_rating_free_course, "user_id": user_id})
                rendered2 = render_to_string('filter_course_list.html',
                                             {'course_list': max_rating_paid_course, "user_id": user_id})
            else:
                rendered = render_to_string('filter_course_list.html', {'course_list': max_rating_course})
                rendered1 = render_to_string('filter_course_list.html', {'course_list': max_rating_free_course})
                rendered2 = render_to_string('filter_course_list.html', {'course_list': max_rating_paid_course})

            # return HttpResponse()
            return JsonResponse({"rendered": rendered, "rendered1": rendered1, "rendered2": rendered2})

        elif subcategories.objects.filter(categories_id=category_id).exists():
            sub_obj = subcategories.objects.filter(categories_id=category_id)
            for i in sub_obj:
                if Courses.objects.filter(scat_id=i.id).exists():
                    obj_course = Courses.objects.filter(scat_id=i.id)
                    obj_free_course = Courses.objects.filter(scat_id=i.id).filter(type=1)
                    obj_paid_course = Courses.objects.filter(scat_id=i.id).filter(type=0)

                    max_rating_course = ''
                    max_rating_free_course = ''
                    max_rating_paid_course = ''
                    for course in obj_course:
                        rating_list = course_comments.objects.filter(course_id_id=course.id)
                        course.rating = getRatingFunc(rating_list)
                        course.video = getVideoCnt(course)
                        course.stuCnt = student_register_courses.objects.filter(course_id_id=course.id).count()
                    max_rating = 0
                    for course in obj_course:
                        if course.rating > max_rating:
                            max_rating = course.rating
                            max_rating_course = course

                    for course in obj_free_course:
                        rating_list = course_comments.objects.filter(course_id_id=course.id)
                        course.rating = getRatingFunc(rating_list)
                        course.video = getVideoCnt(course)
                        course.stuCnt = student_register_courses.objects.filter(course_id_id=course.id).count()
                    max_rating = 0
                    for course in obj_free_course:
                        if course.rating > max_rating:
                            max_rating = course.rating
                            max_rating_free_course = course

                    for course in obj_paid_course:
                        rating_list = course_comments.objects.filter(course_id_id=course.id)
                        course.rating = getRatingFunc(rating_list)
                        course.video = getVideoCnt(course)
                        course.stuCnt = student_register_courses.objects.filter(course_id_id=course.id).count()
                    max_rating = 0
                    for course in obj_paid_course:
                        if course.rating > max_rating:
                            max_rating = course.rating
                            max_rating_paid_course = course

                    obj_course = []
                    obj_free_course = []
                    obj_paid_course = []

                    if max_rating_course != '':
                        obj_course.append(max_rating_course)
                    if max_rating_free_course != '':
                        obj_free_course.append(max_rating_free_course)

                    if max_rating_paid_course != '':
                        obj_paid_course.append(max_rating_paid_course)

                    if user_type == "student":
                        rendered = render_to_string('filter_course_list.html',
                                                    {'course_list': obj_course, "user_id": user_id})
                        rendered1 = render_to_string('filter_course_list.html',
                                                     {'course_list': obj_free_course, "user_id": user_id})
                        rendered2 = render_to_string('filter_course_list.html',
                                                     {'course_list': obj_paid_course, "user_id": user_id})
                    else:
                        rendered = render_to_string('filter_course_list.html', {'course_list': obj_course})
                        rendered1 = render_to_string('filter_course_list.html', {'course_list': obj_free_course})
                        rendered2 = render_to_string('filter_course_list.html', {'course_list': obj_paid_course})
                else:
                    return HttpResponse("error")
                return JsonResponse({"rendered": rendered, "rendered1": rendered1, "rendered2": rendered2})
        else:
            return HttpResponse("error")
    elif category_id_2 == '2':
        if category_id == "All":
            course_list = Courses.objects.all()
            course_free_list = Courses.objects.filter(type=1)
            course_paid_list = Courses.objects.filter(type=0)

            max_cnt_course = []
            max_cnt_free_course = []
            max_cnt_paid_course = []
            for course in course_list:
                rating_list = course_comments.objects.filter(course_id_id=course.id)
                course.stuCnt = student_register_courses.objects.filter(course_id_id=course.id).count()
                course.rating = getRatingFunc(rating_list)
                course.video = getVideoCnt(course)
            max_cnt = 0
            for course in course_list:
                if course.stuCnt > max_cnt:
                    max_cnt = course.stuCnt
                # max_cnt_course = course
            for course in course_list:
                if course.stuCnt == max_cnt:
                    max_cnt_course.append(course)

            for course in course_free_list:
                rating_list = course_comments.objects.filter(course_id_id=course.id)
                course.stuCnt = student_register_courses.objects.filter(course_id_id=course.id).count()
                course.rating = getRatingFunc(rating_list)
                course.video = getVideoCnt(course)

            max_cnt = 0
            for course in course_free_list:
                if course.stuCnt > max_cnt:
                    max_cnt = course.stuCnt
                # max_cnt_free_course = course
            for course in course_free_list:
                if course.stuCnt == max_cnt:
                    max_cnt_free_course.append(course)

            for course in course_paid_list:
                rating_list = course_comments.objects.filter(course_id_id=course.id)
                course.stuCnt = student_register_courses.objects.filter(course_id_id=course.id).count()
                course.rating = getRatingFunc(rating_list)
                course.video = getVideoCnt(course)

            max_cnt = 0
            for course in course_paid_list:
                if course.stuCnt > max_cnt:
                    max_cnt = course.stuCnt
                # max_cnt_paid_course = course

            for course in course_paid_list:
                if course.stuCnt == max_cnt:
                    max_cnt_paid_course.append(course)

            # course_list = []
            # course_free_list = []
            # course_paid_list = []
            # if max_cnt_course != '':
            # 	course_list.append(max_cnt_course)
            # if max_cnt_free_course != '':
            # 	course_free_list.append(max_cnt_free_course)
            #
            # if max_cnt_paid_course != '':
            # 	course_paid_list.append(max_cnt_paid_course)

            if user_type == "student":
                rendered = render_to_string('filter_course_list.html',
                                            {'course_list': max_cnt_course, "user_id": user_id})
                rendered1 = render_to_string('filter_course_list.html',
                                             {'course_list': max_cnt_free_course, "user_id": user_id})
                rendered2 = render_to_string('filter_course_list.html',
                                             {'course_list': max_cnt_paid_course, "user_id": user_id})
            else:
                rendered = render_to_string('filter_course_list.html', {'course_list': max_cnt_course})
                rendered1 = render_to_string('filter_course_list.html', {'course_list': max_cnt_free_course})
                rendered2 = render_to_string('filter_course_list.html', {'course_list': max_cnt_paid_course})

            # return HttpResponse()
            return JsonResponse({"rendered": rendered, "rendered1": rendered1, "rendered2": rendered2})

        elif subcategories.objects.filter(categories_id=category_id).exists():
            sub_obj = subcategories.objects.filter(categories_id=category_id)
            for i in sub_obj:
                if Courses.objects.filter(scat_id=i.id).exists():
                    obj_course = Courses.objects.filter(scat_id=i.id)
                    obj_free_course = Courses.objects.filter(scat_id=i.id).filter(type=1)
                    obj_paid_course = Courses.objects.filter(scat_id=i.id).filter(type=0)

                    max_cnt_course = ''
                    max_cnt_free_course = ''
                    max_cnt_paid_course = ''
                    for course in obj_course:
                        rating_list = course_comments.objects.filter(course_id_id=course.id)
                        course.stuCnt = student_register_courses.objects.filter(course_id_id=course.id).count()
                        course.rating = getRatingFunc(rating_list)
                        course.video = getVideoCnt(course)
                    max_cnt = 0
                    for course in obj_course:
                        if course.stuCnt > max_cnt:
                            max_cnt = course.stuCnt
                            max_cnt_course = course

                    for course in obj_free_course:
                        rating_list = course_comments.objects.filter(course_id_id=course.id)
                        course.stuCnt = student_register_courses.objects.filter(course_id_id=course.id).count()
                        course.rating = getRatingFunc(rating_list)
                        course.video = getVideoCnt(course)
                    max_cnt = 0
                    for course in obj_free_course:
                        if course.stuCnt > max_cnt:
                            max_cnt = course.stuCnt
                            max_cnt_free_course = course

                    for course in obj_paid_course:
                        rating_list = course_comments.objects.filter(course_id_id=course.id)
                        course.stuCnt = student_register_courses.objects.filter(course_id_id=course.id).count()
                        course.rating = getRatingFunc(rating_list)
                        course.video = getVideoCnt(course)
                    max_cnt = 0
                    for course in obj_paid_course:
                        if course.stuCnt > max_cnt:
                            max_cnt = course.stuCnt
                            max_cnt_paid_course = course

                    obj_course = []
                    obj_free_course = []
                    obj_paid_course = []
                    if max_cnt_course != '':
                        obj_course.append(max_cnt_course)
                    if max_cnt_free_course != '':
                        obj_free_course.append(max_cnt_free_course)
                    if max_cnt_paid_course != '':
                        obj_paid_course.append(max_cnt_paid_course)

                    if user_type == "student":
                        rendered = render_to_string('filter_course_list.html',
                                                    {'course_list': obj_course, "user_id": user_id})
                        rendered1 = render_to_string('filter_course_list.html',
                                                     {'course_list': obj_free_course, "user_id": user_id})
                        rendered2 = render_to_string('filter_course_list.html',
                                                     {'course_list': obj_paid_course, "user_id": user_id})
                    else:
                        rendered = render_to_string('filter_course_list.html', {'course_list': obj_course})
                        rendered1 = render_to_string('filter_course_list.html', {'course_list': obj_free_course})
                        rendered2 = render_to_string('filter_course_list.html', {'course_list': obj_paid_course})
                else:
                    return HttpResponse("error")
                return JsonResponse({"rendered": rendered, "rendered1": rendered1, "rendered2": rendered2})
        else:
            return HttpResponse("error")
    elif category_id_2 == '3':
        if category_id == "All":
            course_list = Courses.objects.all().order_by('-created_at')
            course_free_list = Courses.objects.filter(type=1).order_by('-created_at')
            course_paid_list = Courses.objects.filter(type=0).order_by('-created_at')
            if len(course_list) > 0:
                course = course_list[0]
                ratingList = course_comments.objects.filter(course_id_id=course.id)
                course.rating = getRatingFunc(ratingList)
                course.video = getVideoCnt(course)
                course.stuCnt = student_register_courses.objects.filter(course_id_id=course.id).count()
                course_list = []
                course_list.append(course)
            else:
                course_list = []

            if len(course_free_list) > 0:
                course = course_free_list[0]
                ratingList = course_comments.objects.filter(course_id_id=course.id)
                course.rating = getRatingFunc(ratingList)
                course.video = getVideoCnt(course)
                course.stuCnt = student_register_courses.objects.filter(course_id_id=course.id).count()
                course_free_list = []
                course_free_list.append(course)

            else:
                course_free_list = []

            if len(course_paid_list) > 0:
                course = course_paid_list[0]
                ratingList = course_comments.objects.filter(course_id_id=course.id)
                course.rating = getRatingFunc(ratingList)
                course.video = getVideoCnt(course)
                course.stuCnt = student_register_courses.objects.filter(course_id_id=course.id).count()
                course_paid_list = []
                course_paid_list.append(course)
            else:
                course_paid_list = []

            if user_type == "student":
                rendered = render_to_string('filter_course_list.html', {'course_list': course_list, "user_id": user_id})
                rendered1 = render_to_string('filter_course_list.html',
                                             {'course_list': course_free_list, "user_id": user_id})
                rendered2 = render_to_string('filter_course_list.html',
                                             {'course_list': course_paid_list, "user_id": user_id})
            else:
                rendered = render_to_string('filter_course_list.html', {'course_list': course_list})
                rendered1 = render_to_string('filter_course_list.html', {'course_list': course_free_list})
                rendered2 = render_to_string('filter_course_list.html', {'course_list': course_paid_list})

            # return HttpResponse()
            return JsonResponse({"rendered": rendered, "rendered1": rendered1, "rendered2": rendered2})
        elif subcategories.objects.filter(categories_id=category_id).exists():
            sub_obj = subcategories.objects.filter(categories_id=category_id)
            for i in sub_obj:
                if Courses.objects.filter(scat_id=i.id).exists():
                    obj_course = Courses.objects.filter(scat_id=i.id).order_by('-created_at')
                    obj_free_course = Courses.objects.filter(scat_id=i.id).filter(type=1).order_by('-created_at')
                    obj_paid_course = Courses.objects.filter(scat_id=i.id).filter(type=0).order_by('-created_at')

                    if len(obj_course) > 0:
                        course = obj_course[0]
                        ratingList = course_comments.objects.filter(course_id_id=course.id)
                        course.rating = getRatingFunc(ratingList)
                        course.video = getVideoCnt(course)
                        course.stuCnt = student_register_courses.objects.filter(course_id_id=course.id).count()
                        obj_course = []
                        obj_course.append(course)
                    else:
                        obj_course = []

                    if len(obj_free_course) > 0:
                        course = obj_free_course[0]
                        ratingList = course_comments.objects.filter(course_id_id=course.id)
                        course.rating = getRatingFunc(ratingList)
                        course.video = getVideoCnt(course)
                        course.stuCnt = student_register_courses.objects.filter(course_id_id=course.id).count()
                        obj_free_course = []
                        obj_free_course.append(course)
                    else:
                        obj_free_course = []

                    if len(obj_paid_course) > 0:
                        course = obj_paid_course[0]
                        ratingList = course_comments.objects.filter(course_id_id=course.id)
                        course.rating = getRatingFunc(ratingList)
                        course.video = getVideoCnt(course)
                        course.stuCnt = student_register_courses.objects.filter(course_id_id=course.id).count()
                        obj_paid_course = []
                        obj_paid_course.append(course)
                    else:
                        obj_paid_course = []

                    if user_type == "student":
                        rendered = render_to_string('filter_course_list.html',
                                                    {'course_list': obj_course, "user_id": user_id})
                        rendered1 = render_to_string('filter_course_list.html',
                                                     {'course_list': obj_free_course, "user_id": user_id})
                        rendered2 = render_to_string('filter_course_list.html',
                                                     {'course_list': obj_paid_course, "user_id": user_id})
                    else:
                        rendered = render_to_string('filter_course_list.html', {'course_list': obj_course})
                        rendered1 = render_to_string('filter_course_list.html', {'course_list': obj_free_course})
                        rendered2 = render_to_string('filter_course_list.html', {'course_list': obj_paid_course})
                else:
                    return HttpResponse("error")
                return JsonResponse({"rendered": rendered, "rendered1": rendered1, "rendered2": rendered2})
        else:
            return HttpResponse("error")


def becomeTeacher(request):
    id = request.POST.get('id')
    cat_id = request.POST.get('cat_id')
    sub_catid = request.POST.get('sub_catid')

    if user_become.objects.filter(user_id=id).exists():
        one = user_become.objects.filter(user_id=id)[0]
        one.cat_id = cat_id
        one.sub_catid = sub_catid
        one.save()

    else:
        one = user_become(
            user_id=id,
            cat_id=cat_id,
            sub_catid=sub_catid
        )
        one.save()
    ret = {'msg': 'success'}
    return JsonResponse(ret)


@csrf_exempt
def searching(request):
    searchkeyword = request.GET.get('searchkeyword')
    category_obj = categories.objects.all()
    user_type = request.session.get("user_type")
    user_id = request.session.get("user_id")

    favListShow, favCnt, alreadyinFavView, cartListShow, cartCnt, alreadyinCartView, cartTotalSum, noti_list, noti_cnt, msg_list, msg_cnt, stu_msg_list, stu_msg_cnt, total_msg_cnt = findheader(
        request.user.id)

    optionObj = Option.objects.filter(oname="main_host")[0]
    host_url = optionObj.oval

    type = request.POST.get('type')
    page = request.POST.get('page')
    order = request.POST.get('order')

    if type == '' or type == None:
        type = -1
    else:
        type = int(type)

    if page == '' or page == None:
        page = 1
    else:
        page = int(page)

    if order == '' or order == None:
        order = 0
    else:
        order = int(order)

    
    sehList = []

    if user_id == None:
        if type == -1:
            sehList = Courses.objects.filter(name__icontains=searchkeyword).filter(approval_status=2)
        else:
            sehList = Courses.objects.filter(name__icontains=searchkeyword).filter(approval_status=2).filter(type=type)
    else:
        register_course_ids = student_register_courses.objects.filter(student_id_id=user_id).values_list('course_id_id', flat=True)
        if type == -1:
            sehList = Courses.objects.filter(name__icontains=searchkeyword).filter(approval_status=2).exclude(id__in=register_course_ids)
        else:
            sehList = Courses.objects.filter(name__icontains=searchkeyword).filter(approval_status=2).filter(type=type).exclude(id__in=register_course_ids)

    totalsearchresult = len(sehList)

    discount = Discount.objects.all()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    for seh in sehList:
        course = Courses.objects.get(pk=seh.id)
        seh.videoCnt = getVideoCnt(course)
        seh.stuCnt = student_register_courses.objects.filter(course_id_id=seh.id).count()
        seh.link = courseUrlGenerator(course)
        seh.created_at = course.created_at
        if discount.count() == 0:
            discount_percent = 1
        else:
            if now > discount[0].expire_date:
                discount_percent = 1
            else:
                not_str = discount[0].not_apply_course
                not_list = not_str.split('.')
                if str(seh.id) in not_list:
                    discount_percent = 1
                else:
                    discount_percent = (100 - discount[0].discount) / 100
        seh.discount_price = round(seh.price * discount_percent, 2)

        if student_cart_courses.objects.filter(course_id_id=seh.id, student_id_id=user_id).exists():
            seh.is_cart = 1
        else:
            seh.is_cart = 0
        rating_list = course_comments.objects.filter(course_id_id=course.id).values_list('rating', flat=True)
        sum = 0
        count = 0
        for rating in rating_list:
            sum += rating
            count += 1
        if count == 0:
            seh.rating = 0
        else:
            seh.rating = round(sum / count, 1)
        seh.count = count

    seh_list = sehList
    if order == 1:
        seh_list = sorted(sehList, key=attrgetter('rating'), reverse=True)
    elif order == 2:
        seh_list = sorted(sehList, key=attrgetter('stuCnt'), reverse=True)
    elif order == 3:
        seh_list = sorted(sehList, key=attrgetter('created_at'), reverse=True)

    seh_list_paginator = Paginator(seh_list, 4)

    try:
        sehList = seh_list_paginator.page(page)
    except PageNotAnInteger:
        sehList = seh_list_paginator.page(1)
    except EmptyPage:
        sehList = seh_list_paginator.page(seh_list_paginator.num_pages)

    stu_courses = student_register_courses.objects.filter(student_id_id=request.user.id)
    return render(request, 'search.html', {'lang': getLanguage(request)[0],
                                           'searchkeyword': searchkeyword, 'stu_courses':stu_courses,
                                           'totalsearchresult': totalsearchresult, "category_obj": category_obj,
                                           'course_list': sehList, 'favList': favListShow,
                                           'cartList': cartListShow, 'favCnt': favCnt, 'cartCnt': cartCnt,
                                           'cartTotalSum': cartTotalSum, 'noti_cnt': noti_cnt, 'stu_msg_list': stu_msg_list, 'stu_msg_cnt': stu_msg_cnt, 'total_msg_cnt': total_msg_cnt,
                                           'noti_list': noti_list, 'msg_list': msg_list, 'msg_cnt': msg_cnt, 'page': page, 'type': type, 'order': order, 'host_url': host_url})


    # if (Courses.objects.filter(name__icontains=searchkeyword).exists()):
    #     # searchstatus = 1
    #     allsearchresult = Courses.objects.filter(name__icontains=searchkeyword)
    #     totalsearchresult = allsearchresult.count()

    #     course_list = allsearchresult
    #     course_free_list = Courses.objects.filter(name__icontains=searchkeyword, type=1)
    #     course_paid_list = Courses.objects.filter(name__icontains=searchkeyword, type=0)

    #     for course in course_list:
    #         course.link = courseUrlGenerator(course)

    #     for course in course_free_list:
    #         course.link = courseUrlGenerator(course)

    #     for course in course_paid_list:
    #         course.link = courseUrlGenerator(course)

    #     ## Pagination

    #     # number_of_courses_in_a_page = 1
    #     # course_list_page = request.GET.get('course_list_page',1)
    #     # course_list_paginator = Paginator(course_list,number_of_courses_in_a_page)

    #     # try:
    #     #     course_list = course_list_paginator.page(course_list_page)
    #     # except PageNotAnInteger:
    #     #     course_list = course_list_paginator.page(1)
    #     # except EmptyPage:
    #     #     course_list = course_list_paginator.page(course_list_paginator.num_pages)

    #     # course_paid_list_page = request.GET.get('course_paid_list_page',1)
    #     # course_paid_list_paginator = Paginator(course_paid_list,number_of_courses_in_a_page)

    #     # try:
    #     #     course_paid_list = course_paid_list_paginator.page(course_paid_list_page)
    #     # except PageNotAnInteger:
    #     #     course_paid_list = course_paid_list_paginator.page(1)
    #     # except EmptyPage:
    #     #     course_paid_list = course_paid_list_paginator.page(course_paid_list_paginator.num_pages)

    #     # course_free_list_page = request.GET.get('course_free_list_page',1)
    #     # course_free_list_paginator = Paginator(course_free_list,number_of_courses_in_a_page)

    #     # try:
    #     #     course_free_list = course_free_list_paginator.page(course_free_list_page)
    #     # except PageNotAnInteger:
    #     #     course_free_list = course_free_list_paginator.page(1)
    #     # except EmptyPage:
    #     #     course_free_list = course_free_list_paginator.page(course_free_list_paginator.num_pages)

    #     ## End Pagination

    #     if user_type == "student":
    #         favList = student_favourite_courses.objects.filter(student_id_id=request.user.id)
    #         alreadyinFav = student_favourite_courses.objects.values('course_id_id').filter(
    #             student_id_id=request.user.id)
    #         alreadyinFavView = []

    #         for value in range(len(alreadyinFav)):
    #             alreadyinFavView.append(alreadyinFav[value]['course_id_id'])

    #         favListShow = student_favourite_courses.objects.filter(student_id_id=request.user.id).order_by("-id")[:3]

    #         cartList = student_cart_courses.objects.filter(student_id_id=request.user.id)
    #         alreadyinCart = student_cart_courses.objects.values('course_id_id').filter(student_id_id=request.user.id)
    #         alreadyinCartView = []

    #         for value in range(len(alreadyinCart)):
    #             alreadyinCartView.append(alreadyinCart[value]['course_id_id'])

    #         cartListShow = student_cart_courses.objects.filter(student_id_id=request.user.id).order_by("-id")[:3]
    #         cartTotalSum = 0

    #         for cart in cartList:
    #             cartTotalSum += cart.course_id.price

    #         # show notification...
    #         noti_list = notifications.objects.filter(user_id=user_id, is_read=0).order_by("-id")[:3]
    #         noti_cnt = notifications.objects.filter(user_id=user_id, is_read=0).count()
    #         return render(request, 'search.html', {'lang': getLanguage(request)[0],
    #                                                'searchkeyword': searchkeyword,
    #                                                'totalsearchresult': totalsearchresult, "user_id": user_id,
    #                                                "category_obj": category_obj, 'favList': favListShow,
    #                                                'alreadyinFav': alreadyinFavView, 'cartList': cartListShow,
    #                                                'alreadyinCart': alreadyinCartView, 'favCnt': len(favList),
    #                                                'cartCnt': len(cartList), 'cartTotalSum': cartTotalSum,
    #                                                'noti_cnt': noti_cnt, 'noti_list': noti_list, 'msg_list': msg_list,
    #                                                'msg_cnt': msg_cnt,
    #                                                'course_list': course_list, 'course_free_list': course_free_list,
    #                                                'course_paid_list': course_paid_list})
    #     else:
    #         return render(request, 'search.html', {'lang': getLanguage(request)[0],
    #                                                'searchkeyword': searchkeyword,
    #                                                'totalsearchresult': totalsearchresult, "category_obj": category_obj,
    #                                                'course_list': course_list, 'course_free_list': course_free_list,
    #                                                'course_paid_list': course_paid_list, 'favList': favListShow,
    #                                                'cartList': cartListShow, 'favCnt': favCnt, 'cartCnt': cartCnt,
    #                                                'cartTotalSum': cartTotalSum, 'noti_cnt': noti_cnt,
    #                                                'noti_list': noti_list, 'msg_list': msg_list, 'msg_cnt': msg_cnt})

    # else:
    #     searchstatus = 0
    #     return render(request, 'search.html',
    #                   {'lang': getLanguage(request)[0], 'searchkeyword': searchkeyword,
    #                    'favList': favListShow,
    #                    'cartList': cartListShow, 'favCnt': favCnt, 'cartCnt': cartCnt,
    #                    'cartTotalSum': cartTotalSum, 'noti_cnt': noti_cnt, 'noti_list': noti_list, 'msg_list': msg_list,
    #                    'msg_cnt': msg_cnt})


def single_category(request, category_name, id):
    host_url = request.get_host()
    user_id = request.session.get("user_id")
    user_type = request.session.get("user_type")
    stu_courses = student_register_courses.objects.filter(student_id_id=request.user.id)
    type = request.POST.get('type')
    page = request.POST.get('page')
    order = request.POST.get('order')

    if page == None or page == '':
        page = 1
    else:
        page = int(page)

    if type == '' or type == None:
        type = -1
    else:
        type = int(type)

    if order == '' or order == None:
        order = 0
    else:
        order = int(order)

    # show fav page.., cart page...
    favList = student_favourite_courses.objects.filter(student_id_id=request.user.id)
    cartList = student_cart_courses.objects.filter(student_id_id=request.user.id)
    alreadyinCart = student_cart_courses.objects.values('course_id_id').filter(student_id_id=request.user.id)
    alreadyinCartView = []

    for value in range(len(alreadyinCart)):
        alreadyinCartView.append(alreadyinCart[value]['course_id_id'])

    favListShow, favCnt, alreadyinFavView, cartListShow, cartCnt, alreadyinCartView, cartTotalSum, noti_list, noti_cnt, msg_list, msg_cnt, stu_msg_list, stu_msg_cnt, total_msg_cnt = findheader(
        request.user.id)

    for cart in cartList:
        cartTotalSum += cart.course_id.price

    if getLanguage(request)[1] == None:
        l = ""
    else:
        ur = getLanguage(request)[1].split('/')
        l = ur[3]
        if l == "ar":
            l = "ar/"
        else:
            l = "en/"

    category = categories.objects.get(pk=id)
    if user_id == None:
        if type == -1:
            course_list = Courses.objects.filter(scat_id=id).filter(approval_status=2).order_by('-created_at')
        else:
            course_list = Courses.objects.filter(scat_id=id).filter(type=type).filter(approval_status=2).order_by('created_at')
    else:
        register_course_ids = student_register_courses.objects.filter(student_id_id=user_id).values_list('course_id_id', flat=True)
        if type == -1:
            course_list = Courses.objects.filter(scat_id=id).filter(approval_status=2).exclude(id__in=register_course_ids).order_by('-created_at')
        else:
            course_list = Courses.objects.filter(scat_id=id).filter(type=type).filter(approval_status=2).exclude(id__in=register_course_ids).order_by('created_at')

    # get discount information
    discount = Discount.objects.all()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    for course in course_list:
        rating_list = course_comments.objects.filter(course_id_id=course.id)
        course.stuCnt = student_register_courses.objects.filter(course_id_id=course.id).count()
        course.ratingCnt = course_comments.objects.filter(course_id_id=course.id).count()
        course.rating = getRatingFunc(rating_list)
        course.video = getVideoCnt(course)

        if discount.count() == 0:
            discount_percent = 1
        else:
            if now > discount[0].expire_date:
                discount_percent = 1
            else:
                not_str = discount[0].not_apply_course
                not_list = not_str.split('.')
                if str(course.id) in not_list:
                    discount_percent = 1
                else:
                    discount_percent = (100 - discount[0].discount) / 100
        course.discount_price = round(course.price * discount_percent, 2)

    count = course_list.count()
    course_list_tmp = course_list
    if order == 1:
        course_list = sorted(course_list_tmp, key=attrgetter('rating'), reverse=True)
    elif order == 2:
        course_list = sorted(course_list_tmp, key=attrgetter('stuCnt'), reverse=True)

    course_list_paginator = Paginator(course_list, 10)
    try:
        course_list = course_list_paginator.page(page)
    except PageNotAnInteger:
        course_list = course_list_paginator.page(1)
    except EmptyPage:
        course_list = course_list_paginator.page(course_list_paginator.num_pages)
    for course in course_list:
        course.link = courseUrlGenerator(course)

    if l != getLanguage(request)[0]:
        rl = getLanguage(request)[0].split('/')
        return render(request, 'single_category.html',
                      {'lang': getLanguage(request)[0], 'course_list': course_list, 'host_url':host_url,
                       "course_cnt": str(count), "user_id": user_id,
                       'category': category, 'favList': favListShow, 'alreadyinFav': alreadyinFavView,
                       'alreadyinCart': alreadyinCartView, 'stu_courses':stu_courses,
                       'cartList': cartListShow, 'favCnt': len(favList), 'cartCnt': len(cartList),
                       'cartTotalSum': cartTotalSum, 'noti_cnt': noti_cnt, 'noti_list': noti_list,
                       'msg_list': msg_list, 'msg_cnt': msg_cnt, 'type': type, 'page': page,
                       'order': order, 'stu_msg_list': stu_msg_list, 'stu_msg_cnt': stu_msg_cnt, 'total_msg_cnt': total_msg_cnt})

    else:
        return render(request, 'single_category.html',
                      {'lang': getLanguage(request)[0], 'course_list': course_list, 'host_url':host_url,
                       "course_cnt": str(count), "user_id": user_id,
                       'category': category, 'favList': favListShow, 'alreadyinFav': alreadyinFavView,
                       'alreadyinCart': alreadyinCartView, 'stu_courses':stu_courses,
                       'cartList': cartListShow, 'favCnt': len(favList), 'cartCnt': len(cartList),
                       'cartTotalSum': cartTotalSum, 'noti_cnt': noti_cnt, 'noti_list': noti_list,
                       'msg_list': msg_list, 'msg_cnt': msg_cnt, 'type': type, 'page': page,
                       'order': order, 'stu_msg_list': stu_msg_list, 'stu_msg_cnt': stu_msg_cnt, 'total_msg_cnt': total_msg_cnt})

def getPromoData(request):
    course_id = request.POST.get('course_id')
    url = request.POST.get('url')
    if url == None:
        url = ''
    course = Courses.objects.get(pk=course_id)
    rateList = course_comments.objects.filter(course_id_id=course_id)
    cnt = 0
    sum = 0
    for rate in rateList:
        sum += rate.rating
        cnt += 1
    if cnt == 0:
        rating = 0
    else:
        rating = sum / cnt
    course.rating = rating
    ssss = Sections.objects.filter(course_id=course.id).values_list("id", flat=True)
    ssss = list(ssss)

    promoVideo = []
    for s in ssss:
        if VideoUploads.objects.filter(section_id=s).filter(~Q(promo=0)).exists():
            videos = VideoUploads.objects.filter(section_id=s).filter(~Q(promo=0))
            for video in videos:
                promoVideo.append(video)
    if len(promoVideo) > 0:
        curVideo = promoVideo[0].url
    else:
        curVideo = ''
    course.curVideo = curVideo
    course.video = promoVideo
    user = User.objects.get(pk=course.user_id)
    course.user = user

    myUserList = student_register_courses.objects.filter(course_id_id=course.id)
    for one in myUserList:
        if request.user.id == one.student_id_id:
            permit = 1
            pass
    lender = render_to_string('video_modal.html',
                              {'course': course, 'user': request.user, 'studentCnt': len(myUserList), 'url': url})
    return JsonResponse({"lender": lender, "msg": "success"})


@csrf_exempt
def getCourseDetailForPromo(request):
    course_id = request.POST.get('id')
    url = request.POST.get('url')
    if url == None:
        url = ''
    course = Courses.objects.get(pk=course_id)
    rateList = course_comments.objects.filter(course_id_id=course_id).values_list('rating', flat=True)
    cnt = 0
    sum = 0
    for rate in rateList:
        sum += rate
        cnt += 1
    if cnt == 0:
        rating = 0
    else:
        rating = sum / cnt
    ssss = Sections.objects.filter(course_id=course.id, type='video')
    promoVideo = []
    # for s in ssss:
    #     if VideoUploads.objects.filter(section_id=s).filter(~Q(promo=0)).exists():
    #         videos = VideoUploads.objects.filter(section_id=s).filter(~Q(promo=0))
    #         for video in videos:
    #             promoVideo.append(video)
    # if len(promoVideo) > 0:
    #     curVideo = promoVideo[0].url
    # else:
    #     curVideo = ''
    # course.curVideo = curVideo
    # course.video = promoVideo
    user = User.objects.get(pk=course.user_id)
    course.user = user
    myUserList = student_register_courses.objects.filter(course_id_id=course.id)
    dict = {}
    dict1 = {}
    sections = []
    video_list = []
    for ele in ssss:
        videos = VideoUploads.objects.filter(section_id=ele.id)
        for video in videos:
            dict['name'] = video.name
            dict['url'] = video.url
            dict['duration'] = video.duration
            dict['lock'] = video.lock
            video_list.append(dict)
            dict = {}
        dict1['video_list'] = video_list
        video_list = []
        dict1['name'] = ele.name
        sections.append(dict1)
        dict1 = {}
    print("test:::", sections)
    ret = {
        'course': serializers.serialize('json', [course]),
        'user_count': len(myUserList),
        'user_name': user.first_name + ' ' + user.last_name,
        'rating': rating,
        'sections': json.dumps(sections),
        'user_img': user.image,
    }
    return JsonResponse(ret)


def showCartList(request):
    page = request.POST.get('page')
    if page == None or page == '':
        page = 1
    else:
        page = int(page)

    if request.session.get('user_id') == None:
        return redirect('/')
    user_id = request.user.id
    cartList = student_cart_courses.objects.filter(student_id_id=user_id)
    tax = 0
    
    if Admincontrol.objects.filter(id=1).exists():
        tax = Admincontrol.objects.get(pk=1).student_tax

    not_list = []

    subTotal = 0
    subDiscount = 0
    subTax = 0
    
    # get discount information
    discount = Discount.objects.all()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if discount.count() == 0:
        discount_percent = 0
    else:
        if now > discount[0].expire_date:
            discount_percent = 0
        else:
            not_str = discount[0].not_apply_course
            not_list = not_str.split(',')

    for cart in cartList:
        # cartCourseIds.append(cart.course_id.id)
        subTotal += cart.course_id.price
        if student_favourite_courses.objects.filter(course_id_id=cart.course_id_id, student_id_id=user_id).exists():
            cart.is_fav = 1
        else:
            cart.is_fav = 0

        if str(cart.course_id.id) in not_list:
            discount_percent = 0
        else:
            discount_percent = discount[0].discount / 100
                
        subDiscount += cart.course_id.price * discount_percent
        subTax += cart.course_id.price * (tax / 100)
    
    subDiscount = round(subDiscount, 2)
    subTax = round(subTax, 2)
        
    cartListTmp = Paginator(cartList, 2)

    try:
        cartList = cartListTmp.page(page)
    except PageNotAnInteger:
        cartList = cartListTmp.page(1)
    except EmptyPage:
        cartList = cartListTmp.page(cartListTmp.num_pages)

    cartTotalSumPrice = round(subTotal + subTax - subDiscount, 2)

    favListShow, favCnt, alreadyinFavView, cartListShow, cartCnt, alreadyinCartView, cartTotalSum, noti_list, noti_cnt, msg_list, msg_cnt, stu_msg_list, stu_msg_cnt, total_msg_cnt = findheader(
        request.user.id)

    user_type = request.session.get("user_type")
    stu_courses = student_register_courses.objects.filter(student_id_id=request.user.id)
    return render(request, 'cart.html',
                  {'cartList': cartListShow, 'lang': getLanguage(request)[0], 'favList': favListShow,
                   'cartList1': cartList, 'favCnt': favCnt, 'stu_courses':stu_courses,
                   'cartCnt': cartCnt, 'subtotal': subTotal, 'subDiscount': subDiscount,'cartTotalSum': cartTotalSumPrice,
                   'noti_cnt': noti_cnt, 'page': page, 'tax': subTax,
                   'noti_list': noti_list, 'msg_list': msg_list, 'msg_cnt': msg_cnt, 'stu_msg_list': stu_msg_list, 'stu_msg_cnt': stu_msg_cnt, 'total_msg_cnt': total_msg_cnt})


##### PAYMENT #####
def ecommerce_cart(request):
    if request.session.get('user_id') == None:
        return redirect('/')
    return render(request, 'ecommerce_cart.html', {'lang': getLanguage(request)[0]})


def getcardinfo(request, id):
    cardid = request.POST.get('cardid')
    cardinfo = payment.objects.filter(id=cardid).all()
    cardinfodata = serializers.serialize('json', cardinfo)
    # cardinfo = serializers.serialize('json', cardinfoqueryset)
    return HttpResponse(cardinfodata, content_type='application/json')


@csrf_exempt
def ecommerce_payment(request, teacher_id, id, course_url):
    if request.session.get('user_id') == None:
        return redirect('/')
    user_id = request.session.get("user_id")
    user_type = request.session.get("user_type")
    course = Courses.objects.get(id=id)

    subtotalmoney = request.POST.get('subtotalmoney')
    discountmoney = request.POST.get('discomontmoney')
    taxmoney = request.POST.get('taxmoney')
    totalmoney = request.POST.get('totalmoney')

    orderid = generateRandomChar()

    request.session['order_id'] = orderid,
    request.session['amount'] = float(totalmoney or 0)
    favListShow, favCnt, alreadyinFavView, cartListShow, cartCnt, alreadyinCartView, cartTotalSum, noti_list, noti_cnt, msg_list, msg_cnt, stu_msg_list, stu_msg_cnt, total_msg_cnt = findheader(
        request.user.id)

    # if user_type == "student":
    savedcard = payment.objects.filter(student_id=user_id)
    counter = 0
    for i in savedcard:
        i.cardnoending = i.card_no[-4:]
        i.cardssr = counter
        counter += 1

    order_id = orderid
    amount = float(totalmoney or 0)
    host = request.get_host()
    paypal_dict = {
        'business': settings.PAYPAL_RECEIVER_EMAIL,
        'amount': '%.2f' % amount,
        'item_name': 'Order {}',
        'invoice': str(order_id),
        'currency_code': 'USD',
        'notify_url': 'http://{}{}'.format(host,
                                           reverse('paypal-ipn')),
        'return_url': 'http://{}{}'.format(host,
                                           reverse('payment_done', args=[course.id, request.user.id])),
        'cancel_return': 'http://{}{}'.format(host,
                                              reverse('payment_cancelled')),
    }

    form = PayPalPaymentsForm(initial=paypal_dict)

    stu_courses = student_register_courses.objects.filter(student_id_id=request.user.id)
    return render(request, 'ecommerce_payment.html',
                  {'form': form, 'orderid': orderid, 'totalmoney': totalmoney, 'subtotalmoney': subtotalmoney,
                   'discountmoney': discountmoney, 'taxmoney': taxmoney, 'lang': getLanguage(request)[0], 'savedcard': list(savedcard),
                   "course": course, "user_id": user_id, 'favList': favListShow, 'favCnt': favCnt, 'alreadyinFav': alreadyinFavView,
                   'cartList': cartListShow, 'cartCnt': cartCnt, 'alreadyinCart': alreadyinCartView, 'cartTotalSum': cartTotalSum, 'noti_list': noti_list,
                   'noti_cnt': noti_cnt, 'msg_list': msg_list, 'msg_cnt': msg_cnt, 'stu_courses': stu_courses, 'stu_msg_list': stu_msg_list, 'stu_msg_cnt': stu_msg_cnt, 'total_msg_cnt': total_msg_cnt})
    # else:
    #     return redirect("/")


def makeInvoice(request):
    html = "<html><body>It is now </body></html>"
    url = settings.STATICFILES_DIRS[0] + '/invoices/en.jpg'
    img = Image.open(url)
    draw = ImageDraw.Draw(img)
    fonturl = settings.STATICFILES_DIRS[0] + '/invoices/font.ttf'
    font = ImageFont.truetype(fonturl, 110)
    smallfont = ImageFont.truetype(fonturl, 60)

    # drawing name to the img...
    name = request.user.first_name + " " + request.user.last_name
    namePos = [437, 655]
    draw.text(namePos, name, (0, 0, 0), font=font)  # this will draw text with Blackcolor and 16 size

    co = ["HTML", "10$", "5$", "5$"]
    co1 = ["HTML", "10$", "5$", "5$"]
    co2 = ["HTML", "10$", "5$", "5$"]
    co3 = ["HTML", "10$", "5$", "5$"]
    co4 = ["HTML", "10$", "5$", "5$"]
    co5 = ["HTML", "10$", "5$", "5$"]
    co6 = ["HTML", "10$", "5$", "5$"]
    co7 = ["HTML", "10$", "5$", "5$"]

    cofinal = [co, co1, co2, co3, co4, co5, co6, co7]

    course_sl_x = 210
    course_sl_y = 1120

    for i in range(len(cofinal)):
        slno = str(i + 1)
        namePos = [course_sl_x, course_sl_y]
        draw.text(namePos, slno, (0, 0, 0), font=font)  # this will draw text with Blackcolor and 16 size
        course_sl_y = course_sl_y + 100

    # drawing name to the img...
    invoicenumber = "#134464646"
    namePos = [2020, 800]
    draw.text(namePos, invoicenumber, (0, 0, 0), font=smallfont)  # this will draw text with Blackcolor and 16 size

    # drawing name to the img...
    invoicedate = str(datetime.now().strftime("%d %b, %Y"))
    namePos = [2000, 850]
    draw.text(namePos, invoicedate, (0, 0, 0), font=smallfont)  # this will draw text with Blackcolor and 16 size

    # drawing name to the img...
    subtotal = "20$"
    namePos = [2040, 1955]
    draw.text(namePos, subtotal, (0, 0, 0), font=smallfont)  # this will draw text with Blackcolor and 16 size

    discount = "20$"
    namePos = [2040, 2020]
    draw.text(namePos, discount, (0, 0, 0), font=smallfont)  # this will draw text with Blackcolor and 16 size

    tax = "20$"
    namePos = [2040, 2080]
    draw.text(namePos, tax, (0, 0, 0), font=smallfont)  # this will draw text with Blackcolor and 16 size

    total = "20$"
    namePos = [2040, 2175]
    draw.text(namePos, tax, (0, 0, 0), font=font)  # this will draw text with Blackcolor and 16 size

    ## Saving the file
    saveurl = settings.STATICFILES_DIRS[0] + '/invoices/' + "1111" + '_' + "1111" + '.jpg'
    saveurl1 = settings.STATICFILES_DIRS[0] + '/invoices/' + "1111" + '_' + "1111" + '.pdf'
    src = '/certificates/' + "1111" + '_' + "1111" + '.jpg'
    src1 = '/certificates/' + "1111" + '_' + "1111" + '.pdf'
    file = open(saveurl1, "wb")
    img.save(saveurl)
    img2 = Image.open(saveurl)
    pdf_bytes = img2pdf.convert(img2.filename)
    file.write(pdf_bytes)

    return HttpResponse(html)


def generateRandomChar():
    x = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(8))
    return x


@csrf_exempt
def checkout(request):
    # cartcourseids = request.POST.get('cartcourseids')
    subtotalmoney = request.POST.get('subtotalmoney')
    discountmoney = request.POST.get('discomontmoney')
    taxmoney = request.POST.get('taxmoney')
    totalmoney = request.POST.get('totalmoney')
    orderid = generateRandomChar()
    request.session['order_id'] = orderid,
    request.session['amount'] = float(totalmoney or 0)

    user_id = request.session.get("user_id")
    savedcard = payment.objects.filter(student_id=user_id)

    favListShow, favCnt, alreadyinFavView, cartListShow, cartCnt, alreadyinCartView, cartTotalSum, noti_list, noti_cnt, msg_list, msg_cnt, stu_msg_list, stu_msg_cnt, total_msg_cnt = findheader(
        request.user.id)

    orderid = generateRandomChar()
    host = request.get_host()

    paypal_dict = {
        'business': settings.PAYPAL_RECEIVER_EMAIL,
        'amount': '%.2f' % float(totalmoney or 0),
        'item_name': 'Order {}',
        'invoice': str(orderid),
        'currency_code': 'USD',
        'notify_url': 'http://{}{}'.format(host,
                                           reverse('paypal-ipn')),
        'return_url': 'http://{}{}'.format(host,
                                           reverse('process_payment')),
        'cancel_return': 'http://{}{}'.format(host,
                                              reverse('payment_cancelled')),
    }

    form = PayPalPaymentsForm(initial=paypal_dict)

    user_type = request.session.get("user_type")
    stu_courses = student_register_courses.objects.filter(student_id_id=request.user.id)

    return render(request, 'ecommerce_payment.html',
                  {'form': form, 'orderid': orderid, 'totalmoney': totalmoney, 'subtotalmoney': subtotalmoney,
                   'discountmoney': discountmoney, 'taxmoney':taxmoney, 'lang': getLanguage(request)[0], 'savedcard': list(savedcard),
                   "user_id": user_id, 'favList': favListShow, 'favCnt': favCnt, 'alreadyinFav': alreadyinFavView,
                   'cartList': cartListShow, 'cartCnt': cartCnt, 'alreadyinCart': alreadyinCartView, 'cartTotalSum': cartTotalSum, 'noti_list': noti_list,
                   'noti_cnt': noti_cnt, 'msg_list': msg_list, 'msg_cnt': msg_cnt, 'stu_courses': stu_courses, 'stu_msg_list': stu_msg_list, 'stu_msg_cnt': stu_msg_cnt, 'total_msg_cnt': total_msg_cnt})

@csrf_exempt
def process_payment(request):
    x1, x2, x3, y1, y2, purchase_course_ids, y4, z1, z2, msg_list, msg_cnt, stu_msg_list, stu_msg_cnt, total_msg_cnt = findheader(request.user.id)
    student_cart_courses.objects.filter(student_id_id=request.user.id).delete()
    purchase_courses = []
    for course_id in purchase_course_ids:
        course = Courses.objects.get(id=course_id)
        purchase_courses.append(course)

    for course_id in purchase_course_ids:
        import uuid
        import datetime
        invoice_time = datetime.datetime.now()
        invoice_number = f"{uuid.uuid4()}-{str(invoice_time)}"

        register_course = student_register_courses.objects.filter(student_id_id=request.user.id).filter(course_id_id=course_id)
        if not register_course:
            invoice = Invoices(invoice_number=invoice_number, course_id=course_id, student_id=request.user.id)
            invoice.save()

            obj = student_register_courses(student_id_id=request.user.id, course_id_id=course_id, date_created=invoice_time.strftime("%Y-%m-%d %H:%M:%S"))
            obj.save()

    # removing favorite courses if payed courses are in favorite list
    register_course_ids = student_register_courses.objects.filter(student_id_id=request.user.id).values_list('course_id_id', flat=True)
    student_favourite_courses.objects.filter(student_id_id=request.user.id, course_id_id__in=register_course_ids).delete()

    # if user's type is teacher then change his account to stu&teach
    user_id = request.session.get("user_id")
    user_type = request.session.get("user_type")
    if user_type == "teacher":
        user = User.objects.get(id=user_id)
        user.group_id = 4
        user.save()
        request.session['user_type'] = "stuteach"

    # Sending to the creator of this course
    teacher_id = Courses.objects.get(pk=purchase_course_ids[0]).user_id
    teacher = User.objects.get(pk=teacher_id)
    to = teacher.email
    student = User.objects.get(pk=user_id)
    to1 = student.email
    imageLink = f"https://booctep.herokuapp.com/static/assets/img/favicon.png"
    link = ""
    lang = getLanguage(request)[0]
    domain = request.META['HTTP_HOST']
    if lang == 'ar/':
        link = "http://" + domain + "/" + lang + "courses/"
    else:
        link = "http://" + domain + "/en/courses/"
    
    
    text = '<!DOCTYPE HTML PUBLIC "-//W3C//DTD XHTML 1.0 Transitional //EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">'
    text +='<html xmlns="http://www.w3.org/1999/xhtml" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">'
    text +='<head><!--[if gte mso 9]><xml><o:OfficeDocumentSettings><o:AllowPNG/><o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings></xml><![endif]-->'
    text +='<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">'
    text +='<meta name="viewport" content="width=device-width, initial-scale=1.0"><meta name="x-apple-disable-message-reformatting"><!--[if !mso]><!--><meta http-equiv="X-UA-Compatible" content="IE=edge"><!--<![endif]-->'
    text +='<title></title>'
    text +='<style type="text/css">table, td { color: #000000; } a { color: #0000ee; text-decoration: underline; } @media (max-width: 480px) { #u_content_button_4 .v-padding { padding: 20px 50px !important; } }@media only screen and (min-width: 620px) {.u-row { width: 600px !important;}.u-row .u-col {vertical-align: top;}.u-row .u-col-100 {width: 600px !important;}}@media (max-width: 620px) {.u-row-container {max-width: 100% !important;padding-left: 0px !important;padding-right: 0px !important;}.u-row .u-col {min-width: 320px !important;max-width: 100% !important;display: block !important;}.u-row {width: calc(100% - 40px) !important;}.u-col {width: 100% !important;}.u-col > div {margin: 0 auto;}}body {margin: 0;padding: 0;}table,tr,td {vertical-align: top;border-collapse: collapse;}p {margin: 0;}.ie-container table,.mso-container table {table-layout: fixed;}* {line-height: inherit;}a[x-apple-data-detectors="true"] {color: inherit !important;text-decoration: none !important;}</style><!--[if !mso]><!-->'
    text +='<link href="https://fonts.googleapis.com/css?family=Lato:400,700&display=swap" rel="stylesheet" type="text/css">'
    text +='<link href="https://fonts.googleapis.com/css?family=Open+Sans:400,700&display=swap" rel="stylesheet" type="text/css">'
    text +='<link href="https://fonts.googleapis.com/css?family=Raleway:400,700&display=swap" rel="stylesheet" type="text/css"><!--<![endif]--></head><body class="clean-body" style="margin: 0;padding: 0;-webkit-text-size-adjust: 100%;background-color: #efefef;color: #000000"><!--[if IE]><div class="ie-container"><![endif]--><!--[if mso]><div class="mso-container"><![endif]--><table style="border-collapse: collapse;table-layout: fixed;border-spacing: 0;mso-table-lspace: 0pt;mso-table-rspace: 0pt;vertical-align: top;min-width: 320px;Margin: 0 auto;background-color: #efefef;width:100%" cellpadding="0" cellspacing="0"><tbody><tr style="vertical-align: top"><td style="word-break: break-word;border-collapse: collapse !important;vertical-align: top"><!--[if (mso)|(IE)]><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td align="center" style="background-color: #efefef;"><![endif]--><div class="u-row-container" style="padding: 0px;background-color: transparent"><div class="u-row" style="Margin: 0 auto;min-width: 320px;max-width: 600px;overflow-wrap: break-word;word-wrap: break-word;word-break: break-word;background-color:   #d7dbf5;"><div style="border-collapse: collapse;display: table;width: 100%;background-color: transparent;"><!--[if (mso)|(IE)]><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td style="padding: 0px;background-color: transparent;" align="center"><table cellpadding="0" cellspacing="0" border="0" style="width:600px;"><tr style="background-color: #0000ff;"><![endif]--><!--[if (mso)|(IE)]><td align="center" width="600" style="width: 600px;padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;" valign="top"><![endif]--><div class="u-col u-col-100" style="max-width: 320px;min-width: 600px;display: table-cell;vertical-align: top;"><div style="width: 100% !important;"><!--[if (!mso)&(!IE)]><!--><div style="padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;"><!--<![endif]--><table style="font-family:Open Sans,sans-serif;" role="presentation" cellpadding="0" cellspacing="0" width="100%" border="0"><tbody><tr><td style="overflow-wrap:break-word;word-break:break-word;padding:10px;font-family:Open Sans,sans-serif;" align="left"><table width="100%" cellpadding="0" cellspacing="0" border="0" ><tr><td style="padding-right: 0px;padding-left: 0px;" align="center">'
    text +='<img align="center" border="0" src="' + imageLink + '" alt="Image" title="Image" style="outline: none;text-decoration: none;-ms-interpolation-mode: bicubic;clear: both;display: inline-block !important;border: none;height: auto;float: none;width: 100%;max-width: 80px;" width="80"></td></tr></table></td></tr></tbody></table><!--[if (!mso)&(!IE)]><!--></div><!--<![endif]--></div></div><!--[if (mso)|(IE)]></td><![endif]--><!--[if (mso)|(IE)]></tr></table></td></tr></table><![endif]--></div></div></div><div class="u-row-container" style="padding: 0px;background-color: transparent"><div class="u-row" style="Margin: 0 auto;min-width: 320px;max-width: 600px;overflow-wrap: break-word;word-wrap: break-word;word-break: break-word;background-color: #ffffff;"><div style="border-collapse: collapse;display: table;width: 100%;background-color: transparent;"><!--[if (mso)|(IE)]><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td style="padding: 0px;background-color: transparent;" align="center"><table cellpadding="0" cellspacing="0" border="0" style="width:600px;"><tr style="background-color: #ffffff;"><![endif]--><!--[if (mso)|(IE)]><td align="center" width="600" style="width: 600px;padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;" valign="top"><![endif]--><div class="u-col u-col-100" style="max-width: 320px;min-width: 600px;display: table-cell;vertical-align: top;"><div style="width: 100% !important;"><!--[if (!mso)&(!IE)]><!--><div style="padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;"><!--<![endif]--><table style="font-family:Open Sans,sans-serif;" role="presentation" cellpadding="0" cellspacing="0" width="100%" border="0" ><tbody><tr><td style="overflow-wrap:break-word;word-break:break-word;padding:18px 10px 12px;font-family:Open Sans,sans-serif;" align="left"><div style="color: #333333; line-height: 140%; text-align: center; word-wrap: break-word;"><p style="font-size: 14px; line-height: 140%;"><span style="font-size: 22px; line-height: 30.8px;"><strong>تم الانضمام بنجاح</strong></span></p></div></td></tr></tbody></table><!--[if (!mso)&(!IE)]><!--></div><!--<![endif]--></div></div><!--[if (mso)|(IE)]></td><![endif]--><!--[if (mso)|(IE)]></tr></table></td></tr></table><![endif]--></div></div></div><div class="u-row-container" style="padding: 0px;background-color: transparent"><div class="u-row" style="Margin: 0 auto;min-width: 320px;max-width: 600px;overflow-wrap: break-word;word-wrap: break-word;word-break: break-word;background-color: #ffffff;"><div style="border-collapse: collapse;display: table;width: 100%;background-color: transparent;"><!--[if (mso)|(IE)]><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td style="padding: 0px;background-color: transparent;" align="center"><table cellpadding="0" cellspacing="0" border="0" style="width:600px;"><tr style="background-color: #ffffff;"><![endif]--><!--[if (mso)|(IE)]><td align="center" width="600" style="width: 600px;padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;" valign="top"><![endif]--><div class="u-col u-col-100" style="max-width: 320px;min-width: 600px;display: table-cell;vertical-align: top;"><div style="width: 100% !important;"><!--[if (!mso)&(!IE)]><!--><div style="padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;"><!--<![endif]--><table style="font-family:Open Sans,sans-serif;" role="presentation" cellpadding="0" cellspacing="0" width="100%" border="0" ><tbody><tr><td style="overflow-wrap:break-word;word-break:break-word;padding:0px 25px 10px;font-family:Open Sans,sans-serif;" align="left"><div style="color: #333333; line-height: 160%; text-align: center; word-wrap: break-word;"><p style="font-size: 14px; line-height: 160%; text-align: right;">لقد قمت بإتمام عملية الشراء بنجاح, الان هو وقت البدء بزيادة قدراتك</p></div></td></tr></tbody></table><!--[if (!mso)&(!IE)]><!--></div><!--<![endif]--></div></div><!--[if (mso)|(IE)]></td><![endif]--><!--[if (mso)|(IE)]></tr></table></td></tr></table><![endif]--></div></div></div><div class="u-row-container" style="padding: 0px;background-color: transparent"><div class="u-row" style="Margin: 0 auto;min-width: 320px;max-width: 600px;overflow-wrap: break-word;word-wrap: break-word;word-break: break-word;background-color: #ffffff;"><div style="border-collapse: collapse;display: table;width: 100%;background-color: transparent;"><!--[if (mso)|(IE)]><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td style="padding: 0px;background-color: transparent;" align="center"><table cellpadding="0" cellspacing="0" border="0" style="width:600px;"><tr style="background-color: #ffffff;"><![endif]--><!--[if (mso)|(IE)]><td align="center" width="600" style="width: 600px;padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;" valign="top"><![endif]--><div class="u-col u-col-100" style="max-width: 320px;min-width: 600px;display: table-cell;vertical-align: top;"><div style="width: 100% !important;"><!--[if (!mso)&(!IE)]><!--><div style="padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;"><!--<![endif]--><table id="u_content_button_4" style="font-family:Open Sans,sans-serif;" role="presentation" cellpadding="0" cellspacing="0" width="100%" border="0"><tbody><tr><td style="overflow-wrap:break-word;word-break:break-word;padding:10px;font-family:Open Sans,sans-serif;" align="left"><div align="center"><!--[if mso]><table width="100%" cellpadding="0" cellspacing="0" border="0" style="border-spacing: 0; border-collapse: collapse; mso-table-lspace:0pt; mso-table-rspace:0pt;font-family:Open Sans,sans-serif;"><tr><td style="font-family:Open Sans,sans-serif;" align="center"><v:roundrect xmlns:v="urn:schemas-microsoft-com:vml" xmlns:w="urn:schemas-microsoft-com:office:word" href="" style="height:38px; v-text-anchor:middle; width:274px;" arcsize="92%" stroke="f" fillcolor="#1b36ab"><w:anchorlock/><center style="color:#FFFFFF;font-family:Open Sans,sans-serif;"><![endif]-->'
    text +='<a href="' + link + '" target="_blank" style="box-sizing: border-box;display: inline-block;font-family:Open Sans,sans-serif;text-decoration: none;-webkit-text-size-adjust: none;text-align: center;color: #FFFFFF; background-color: #1b36ab; border-radius: 35px; -webkit-border-radius: 35px; -moz-border-radius: 35px; width:auto; max-width:100%; overflow-wrap: break-word; word-break: break-word; word-wrap:break-word; mso-border-alt: none;"><span class="v-padding" style="display:block;padding:12px 40px 10px;line-height:120%;"><span style="font-size: 14px; line-height: 16.8px;"><strong><span style="line-height: 16.8px; font-size: 14px;">الذهاب الى لوحة التحكم</span></strong></span></span></a><!--[if mso]></center></v:roundrect></td></tr></table><![endif]--></div></td></tr></tbody></table><!--[if (!mso)&(!IE)]><!--></div><!--<![endif]--></div></div><!--[if (mso)|(IE)]></td><![endif]--><!--[if (mso)|(IE)]></tr></table></td></tr></table><![endif]--></div></div></div><div class="u-row-container" style="padding: 0px;background-color: transparent"><div class="u-row" style="Margin: 0 auto;min-width: 320px;max-width: 600px;overflow-wrap: break-word;word-wrap: break-word;word-break: break-word;background-color: #ffffff;"><div style="border-collapse: collapse;display: table;width: 100%;background-color: transparent;"><!--[if (mso)|(IE)]><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td style="padding: 0px;background-color: transparent;" align="center"><table cellpadding="0" cellspacing="0" border="0" style="width:600px;"><tr style="background-color: #ffffff;"><![endif]--><!--[if (mso)|(IE)]><td align="center" width="600" style="width: 600px;padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;" valign="top"><![endif]--><div class="u-col u-col-100" style="max-width: 320px;min-width: 600px;display: table-cell;vertical-align: top;"><div style="width: 100% !important;"><!--[if (!mso)&(!IE)]><!--><div style="padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;"><!--<![endif]--><table style="font-family:Open Sans,sans-serif;" role="presentation" cellpadding="0" cellspacing="0" width="100%" border="0"><tbody><tr><td style="overflow-wrap:break-word;word-break:break-word;padding:15px 10px 9px;font-family:Open Sans,sans-serif;" align="left"><table height="0px" align="center" border="0" cellpadding="0" cellspacing="0" width="72%" style="border-collapse: collapse;table-layout: fixed;border-spacing: 0;mso-table-lspace: 0pt;mso-table-rspace: 0pt;vertical-align: top;border-top: 1px solid #DFF2F5;-ms-text-size-adjust: 100%;-webkit-text-size-adjust: 100%"><tbody><tr style="vertical-align: top"><td style="word-break: break-word;border-collapse: collapse !important;vertical-align: top;font-size: 0px;line-height: 0px;mso-line-height-rule: exactly;-ms-text-size-adjust: 100%;-webkit-text-size-adjust: 100%"><span>&#160;</span></td></tr></tbody></table></td></tr></tbody></table><table style="font-family:Open Sans,sans-serif;" role="presentation" cellpadding="0" cellspacing="0" width="100%" border="0"><tbody><tr><td style="overflow-wrap:break-word;word-break:break-word;padding:10px;font-family:Open Sans,sans-serif;" align="left"><div style="color: #7e7e81; line-height: 150%; text-align: center; word-wrap: break-word;"><p style="font-size: 14px; line-height: 150%;"><span style="font-size: 12px; line-height: 18px;">هذه الرسالة تلقائية من فريق دعم منصة بوستيب, نتمنى لك يوما سعيد</span><span style="font-size: 12px; line-height: 18px;"></span></p></div></td></tr></tbody></table><!--[if (!mso)&(!IE)]><!--></div><!--<![endif]--></div></div><!--[if (mso)|(IE)]></td><![endif]--><!--[if (mso)|(IE)]></tr></table></td></tr></table><![endif]--></div></div></div><!--[if (mso)|(IE)]></td></tr></table><![endif]--></td></tr></tbody></table><!--[if mso]></div><![endif]--><!--[if IE]></div><![endif]--></body>'
    text +='</html>'
    
    subject = 'Joined to courses'
    msg = EmailMultiAlternatives(subject, '...', 'support@booctep.com', [to, to1])
    msg.attach_alternative(text, "text/html")
    msg.send()
        
    course_ids = json.dumps(purchase_course_ids)
    return redirect(reverse('student enrollments', kwargs={"course_ids": course_ids}))
    # return render(request, 'payment_done.html', {'purchase_courses': purchase_courses, 'student_id': request.user.id})

@csrf_exempt
def payment_done(request, course_id, student_id):
    import uuid
    import datetime
    invoice_time = datetime.datetime.now()
    invoice_number = f"{uuid.uuid4()}-{str(invoice_time)}"

    register_course = student_register_courses.objects.filter(student_id_id=student_id).filter(course_id_id=course_id)
    if not register_course:
        invoice = Invoices(invoice_number=invoice_number, course_id=course_id, student_id=student_id)
        invoice.save()

        obj = student_register_courses(student_id_id=student_id, course_id_id=course_id, date_created=invoice_time.strftime("%Y-%m-%d %H:%M:%S"))
        obj.save()

    # if course is in favorite list, then remove it from favorite list
    student_favourite_courses.objects.filter(course_id_id=course_id, student_id_id=student_id).delete()
    student_cart_courses.objects.filter(course_id_id=course_id, student_id_id=student_id).delete()
    # if student_favourite_courses.objects.filter(course_id_id=course_id, student_id_id=student_id).exists():
    #     favorite_course.delete()

    # if user's type is teacher then change his account to stu&teach
    user_id = request.session.get("user_id")
    user_type = request.session.get("user_type")
    if user_type == "teacher":
        user = User.objects.get(id=user_id)
        user.group_id = 4
        user.save()
        request.session['user_type'] = "stuteach"

    # Sending to the creator of this course
    teacher_id = Courses.objects.get(pk=course_id).user_id
    teacher = User.objects.get(pk=teacher_id)
    to = teacher.email
    student = User.objects.get(pk=student_id)
    to1 = student.email
    imageLink = f"https://booctep.herokuapp.com/static/assets/img/favicon.png"
    link = ""
    lang = getLanguage(request)[0]
    domain = request.META['HTTP_HOST']
    if lang == 'ar/':
        link = "http://" + domain + "/" + lang + "courses/"
    else:
        link = "http://" + domain + "/en/courses/"
    
    
    text = '<!DOCTYPE HTML PUBLIC "-//W3C//DTD XHTML 1.0 Transitional //EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">'
    text +='<html xmlns="http://www.w3.org/1999/xhtml" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">'
    text +='<head><!--[if gte mso 9]><xml><o:OfficeDocumentSettings><o:AllowPNG/><o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings></xml><![endif]-->'
    text +='<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">'
    text +='<meta name="viewport" content="width=device-width, initial-scale=1.0"><meta name="x-apple-disable-message-reformatting"><!--[if !mso]><!--><meta http-equiv="X-UA-Compatible" content="IE=edge"><!--<![endif]-->'
    text +='<title></title>'
    text +='<style type="text/css">table, td { color: #000000; } a { color: #0000ee; text-decoration: underline; } @media (max-width: 480px) { #u_content_button_4 .v-padding { padding: 20px 50px !important; } }@media only screen and (min-width: 620px) {.u-row { width: 600px !important;}.u-row .u-col {vertical-align: top;}.u-row .u-col-100 {width: 600px !important;}}@media (max-width: 620px) {.u-row-container {max-width: 100% !important;padding-left: 0px !important;padding-right: 0px !important;}.u-row .u-col {min-width: 320px !important;max-width: 100% !important;display: block !important;}.u-row {width: calc(100% - 40px) !important;}.u-col {width: 100% !important;}.u-col > div {margin: 0 auto;}}body {margin: 0;padding: 0;}table,tr,td {vertical-align: top;border-collapse: collapse;}p {margin: 0;}.ie-container table,.mso-container table {table-layout: fixed;}* {line-height: inherit;}a[x-apple-data-detectors="true"] {color: inherit !important;text-decoration: none !important;}</style><!--[if !mso]><!-->'
    text +='<link href="https://fonts.googleapis.com/css?family=Lato:400,700&display=swap" rel="stylesheet" type="text/css">'
    text +='<link href="https://fonts.googleapis.com/css?family=Open+Sans:400,700&display=swap" rel="stylesheet" type="text/css">'
    text +='<link href="https://fonts.googleapis.com/css?family=Raleway:400,700&display=swap" rel="stylesheet" type="text/css"><!--<![endif]--></head><body class="clean-body" style="margin: 0;padding: 0;-webkit-text-size-adjust: 100%;background-color: #efefef;color: #000000"><!--[if IE]><div class="ie-container"><![endif]--><!--[if mso]><div class="mso-container"><![endif]--><table style="border-collapse: collapse;table-layout: fixed;border-spacing: 0;mso-table-lspace: 0pt;mso-table-rspace: 0pt;vertical-align: top;min-width: 320px;Margin: 0 auto;background-color: #efefef;width:100%" cellpadding="0" cellspacing="0"><tbody><tr style="vertical-align: top"><td style="word-break: break-word;border-collapse: collapse !important;vertical-align: top"><!--[if (mso)|(IE)]><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td align="center" style="background-color: #efefef;"><![endif]--><div class="u-row-container" style="padding: 0px;background-color: transparent"><div class="u-row" style="Margin: 0 auto;min-width: 320px;max-width: 600px;overflow-wrap: break-word;word-wrap: break-word;word-break: break-word;background-color:   #d7dbf5;"><div style="border-collapse: collapse;display: table;width: 100%;background-color: transparent;"><!--[if (mso)|(IE)]><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td style="padding: 0px;background-color: transparent;" align="center"><table cellpadding="0" cellspacing="0" border="0" style="width:600px;"><tr style="background-color: #0000ff;"><![endif]--><!--[if (mso)|(IE)]><td align="center" width="600" style="width: 600px;padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;" valign="top"><![endif]--><div class="u-col u-col-100" style="max-width: 320px;min-width: 600px;display: table-cell;vertical-align: top;"><div style="width: 100% !important;"><!--[if (!mso)&(!IE)]><!--><div style="padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;"><!--<![endif]--><table style="font-family:Open Sans,sans-serif;" role="presentation" cellpadding="0" cellspacing="0" width="100%" border="0"><tbody><tr><td style="overflow-wrap:break-word;word-break:break-word;padding:10px;font-family:Open Sans,sans-serif;" align="left"><table width="100%" cellpadding="0" cellspacing="0" border="0" ><tr><td style="padding-right: 0px;padding-left: 0px;" align="center">'
    text +='<img align="center" border="0" src="' + imageLink + '" alt="Image" title="Image" style="outline: none;text-decoration: none;-ms-interpolation-mode: bicubic;clear: both;display: inline-block !important;border: none;height: auto;float: none;width: 100%;max-width: 80px;" width="80"></td></tr></table></td></tr></tbody></table><!--[if (!mso)&(!IE)]><!--></div><!--<![endif]--></div></div><!--[if (mso)|(IE)]></td><![endif]--><!--[if (mso)|(IE)]></tr></table></td></tr></table><![endif]--></div></div></div><div class="u-row-container" style="padding: 0px;background-color: transparent"><div class="u-row" style="Margin: 0 auto;min-width: 320px;max-width: 600px;overflow-wrap: break-word;word-wrap: break-word;word-break: break-word;background-color: #ffffff;"><div style="border-collapse: collapse;display: table;width: 100%;background-color: transparent;"><!--[if (mso)|(IE)]><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td style="padding: 0px;background-color: transparent;" align="center"><table cellpadding="0" cellspacing="0" border="0" style="width:600px;"><tr style="background-color: #ffffff;"><![endif]--><!--[if (mso)|(IE)]><td align="center" width="600" style="width: 600px;padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;" valign="top"><![endif]--><div class="u-col u-col-100" style="max-width: 320px;min-width: 600px;display: table-cell;vertical-align: top;"><div style="width: 100% !important;"><!--[if (!mso)&(!IE)]><!--><div style="padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;"><!--<![endif]--><table style="font-family:Open Sans,sans-serif;" role="presentation" cellpadding="0" cellspacing="0" width="100%" border="0" ><tbody><tr><td style="overflow-wrap:break-word;word-break:break-word;padding:18px 10px 12px;font-family:Open Sans,sans-serif;" align="left"><div style="color: #333333; line-height: 140%; text-align: center; word-wrap: break-word;"><p style="font-size: 14px; line-height: 140%;"><span style="font-size: 22px; line-height: 30.8px;"><strong>تم الانضمام بنجاح</strong></span></p></div></td></tr></tbody></table><!--[if (!mso)&(!IE)]><!--></div><!--<![endif]--></div></div><!--[if (mso)|(IE)]></td><![endif]--><!--[if (mso)|(IE)]></tr></table></td></tr></table><![endif]--></div></div></div><div class="u-row-container" style="padding: 0px;background-color: transparent"><div class="u-row" style="Margin: 0 auto;min-width: 320px;max-width: 600px;overflow-wrap: break-word;word-wrap: break-word;word-break: break-word;background-color: #ffffff;"><div style="border-collapse: collapse;display: table;width: 100%;background-color: transparent;"><!--[if (mso)|(IE)]><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td style="padding: 0px;background-color: transparent;" align="center"><table cellpadding="0" cellspacing="0" border="0" style="width:600px;"><tr style="background-color: #ffffff;"><![endif]--><!--[if (mso)|(IE)]><td align="center" width="600" style="width: 600px;padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;" valign="top"><![endif]--><div class="u-col u-col-100" style="max-width: 320px;min-width: 600px;display: table-cell;vertical-align: top;"><div style="width: 100% !important;"><!--[if (!mso)&(!IE)]><!--><div style="padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;"><!--<![endif]--><table style="font-family:Open Sans,sans-serif;" role="presentation" cellpadding="0" cellspacing="0" width="100%" border="0" ><tbody><tr><td style="overflow-wrap:break-word;word-break:break-word;padding:0px 25px 10px;font-family:Open Sans,sans-serif;" align="left"><div style="color: #333333; line-height: 160%; text-align: center; word-wrap: break-word;"><p style="font-size: 14px; line-height: 160%; text-align: right;">لقد قمت بإتمام عملية الشراء بنجاح, الان هو وقت البدء بزيادة قدراتك</p></div></td></tr></tbody></table><!--[if (!mso)&(!IE)]><!--></div><!--<![endif]--></div></div><!--[if (mso)|(IE)]></td><![endif]--><!--[if (mso)|(IE)]></tr></table></td></tr></table><![endif]--></div></div></div><div class="u-row-container" style="padding: 0px;background-color: transparent"><div class="u-row" style="Margin: 0 auto;min-width: 320px;max-width: 600px;overflow-wrap: break-word;word-wrap: break-word;word-break: break-word;background-color: #ffffff;"><div style="border-collapse: collapse;display: table;width: 100%;background-color: transparent;"><!--[if (mso)|(IE)]><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td style="padding: 0px;background-color: transparent;" align="center"><table cellpadding="0" cellspacing="0" border="0" style="width:600px;"><tr style="background-color: #ffffff;"><![endif]--><!--[if (mso)|(IE)]><td align="center" width="600" style="width: 600px;padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;" valign="top"><![endif]--><div class="u-col u-col-100" style="max-width: 320px;min-width: 600px;display: table-cell;vertical-align: top;"><div style="width: 100% !important;"><!--[if (!mso)&(!IE)]><!--><div style="padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;"><!--<![endif]--><table id="u_content_button_4" style="font-family:Open Sans,sans-serif;" role="presentation" cellpadding="0" cellspacing="0" width="100%" border="0"><tbody><tr><td style="overflow-wrap:break-word;word-break:break-word;padding:10px;font-family:Open Sans,sans-serif;" align="left"><div align="center"><!--[if mso]><table width="100%" cellpadding="0" cellspacing="0" border="0" style="border-spacing: 0; border-collapse: collapse; mso-table-lspace:0pt; mso-table-rspace:0pt;font-family:Open Sans,sans-serif;"><tr><td style="font-family:Open Sans,sans-serif;" align="center"><v:roundrect xmlns:v="urn:schemas-microsoft-com:vml" xmlns:w="urn:schemas-microsoft-com:office:word" href="" style="height:38px; v-text-anchor:middle; width:274px;" arcsize="92%" stroke="f" fillcolor="#1b36ab"><w:anchorlock/><center style="color:#FFFFFF;font-family:Open Sans,sans-serif;"><![endif]-->'
    text +='<a href="' + link + '" target="_blank" style="box-sizing: border-box;display: inline-block;font-family:Open Sans,sans-serif;text-decoration: none;-webkit-text-size-adjust: none;text-align: center;color: #FFFFFF; background-color: #1b36ab; border-radius: 35px; -webkit-border-radius: 35px; -moz-border-radius: 35px; width:auto; max-width:100%; overflow-wrap: break-word; word-break: break-word; word-wrap:break-word; mso-border-alt: none;"><span class="v-padding" style="display:block;padding:12px 40px 10px;line-height:120%;"><span style="font-size: 14px; line-height: 16.8px;"><strong><span style="line-height: 16.8px; font-size: 14px;">الذهاب الى لوحة التحكم</span></strong></span></span></a><!--[if mso]></center></v:roundrect></td></tr></table><![endif]--></div></td></tr></tbody></table><!--[if (!mso)&(!IE)]><!--></div><!--<![endif]--></div></div><!--[if (mso)|(IE)]></td><![endif]--><!--[if (mso)|(IE)]></tr></table></td></tr></table><![endif]--></div></div></div><div class="u-row-container" style="padding: 0px;background-color: transparent"><div class="u-row" style="Margin: 0 auto;min-width: 320px;max-width: 600px;overflow-wrap: break-word;word-wrap: break-word;word-break: break-word;background-color: #ffffff;"><div style="border-collapse: collapse;display: table;width: 100%;background-color: transparent;"><!--[if (mso)|(IE)]><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td style="padding: 0px;background-color: transparent;" align="center"><table cellpadding="0" cellspacing="0" border="0" style="width:600px;"><tr style="background-color: #ffffff;"><![endif]--><!--[if (mso)|(IE)]><td align="center" width="600" style="width: 600px;padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;" valign="top"><![endif]--><div class="u-col u-col-100" style="max-width: 320px;min-width: 600px;display: table-cell;vertical-align: top;"><div style="width: 100% !important;"><!--[if (!mso)&(!IE)]><!--><div style="padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;"><!--<![endif]--><table style="font-family:Open Sans,sans-serif;" role="presentation" cellpadding="0" cellspacing="0" width="100%" border="0"><tbody><tr><td style="overflow-wrap:break-word;word-break:break-word;padding:15px 10px 9px;font-family:Open Sans,sans-serif;" align="left"><table height="0px" align="center" border="0" cellpadding="0" cellspacing="0" width="72%" style="border-collapse: collapse;table-layout: fixed;border-spacing: 0;mso-table-lspace: 0pt;mso-table-rspace: 0pt;vertical-align: top;border-top: 1px solid #DFF2F5;-ms-text-size-adjust: 100%;-webkit-text-size-adjust: 100%"><tbody><tr style="vertical-align: top"><td style="word-break: break-word;border-collapse: collapse !important;vertical-align: top;font-size: 0px;line-height: 0px;mso-line-height-rule: exactly;-ms-text-size-adjust: 100%;-webkit-text-size-adjust: 100%"><span>&#160;</span></td></tr></tbody></table></td></tr></tbody></table><table style="font-family:Open Sans,sans-serif;" role="presentation" cellpadding="0" cellspacing="0" width="100%" border="0"><tbody><tr><td style="overflow-wrap:break-word;word-break:break-word;padding:10px;font-family:Open Sans,sans-serif;" align="left"><div style="color: #7e7e81; line-height: 150%; text-align: center; word-wrap: break-word;"><p style="font-size: 14px; line-height: 150%;"><span style="font-size: 12px; line-height: 18px;">هذه الرسالة تلقائية من فريق دعم منصة بوستيب, نتمنى لك يوما سعيد</span><span style="font-size: 12px; line-height: 18px;"></span></p></div></td></tr></tbody></table><!--[if (!mso)&(!IE)]><!--></div><!--<![endif]--></div></div><!--[if (mso)|(IE)]></td><![endif]--><!--[if (mso)|(IE)]></tr></table></td></tr></table><![endif]--></div></div></div><!--[if (mso)|(IE)]></td></tr></table><![endif]--></td></tr></tbody></table><!--[if mso]></div><![endif]--><!--[if IE]></div><![endif]--></body>'
    text +='</html>'
    
    subject = 'Joined to courses'
    msg = EmailMultiAlternatives(subject, '...', 'support@booctep.com', [to, to1])
    msg.attach_alternative(text, "text/html")
    msg.send()
    
    return redirect(reverse('student enrollment', kwargs={"course_id": course_id}))
    # return render(request, 'payment_done.html')


@csrf_exempt
def payment_canceled(request):
    return render(request, 'payment_cancelled.html')


##### PAYMENT ####

@csrf_exempt
def checkdiscountcode(request):
    discount_code = request.POST.get('promoinput')

    user_id = request.user.id
    cartList = student_cart_courses.objects.filter(student_id_id=user_id)

    tax = 0
    if Admincontrol.objects.filter(id=1).exists():
        tax = Admincontrol.objects.get(pk=1).student_tax

    not_list = []
    # get discount information
    admin_discount = Discount.objects.all()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if admin_discount.count() == 0:
        discount_percent = 0
    else:
        if now > admin_discount[0].expire_date:
            discount_percent = 0
        else:
            not_str = admin_discount[0].not_apply_course
            not_list = not_str.split(',')

    for cart in cartList:
        if str(cart.course_id.id) in not_list:
            cart.discount_percent = 0
        else:
            cart.discount_percent = admin_discount[0].discount / 100

        discount_courses = discount.objects.filter(course_id=cart.course_id_id).filter(promo_code=discount_code)
        if len(discount_courses) > 0:
            discount_course = discount_courses[0]
            expire_date = datetime.strptime(discount_course.expire + " 00:00:00", '%Y-%m-%d %H:%M:%S')
            expire_date = pytz.utc.localize(expire_date)
            nowtime = datetime.today()
            nowtime = pytz.utc.localize(nowtime)
            if expire_date >= nowtime:
                cart.promo_discount = discount_course.discount_percent / 100
            else:
                cart.promo_discount = 0
        else:
            cart.promo_discount = 0

    subTotal = 0
    subDiscount = 0
    subPromoDiscount = 0
    subTax = 0
    promoError = 0
    for cart in cartList:
        subTotal += cart.course_id.price
        
        subDiscount += cart.course_id.price * cart.discount_percent

        subTax += cart.course_id.price * (tax / 100)

        subPromoDiscount += (cart.course_id.price - cart.course_id.price * cart.discount_percent + cart.course_id.price * (tax / 100)) * cart.promo_discount
        

    print("subTotal:::", subTotal)
    print("subDiscount:::", subDiscount)
    print("subPromoDiscount:::", subPromoDiscount)
    print("subTax:::", subTax)

    cartTotalSumPrice = subTotal + subTax - subDiscount - subPromoDiscount

    if subPromoDiscount == 0:
        promoError = 1

    responseData = {
        'cartTotalSumPrice': round(cartTotalSumPrice, 2),
        'subDiscount': round(subDiscount + subPromoDiscount, 2),
        'promoError': promoError
    }
    
    return JsonResponse(responseData)

@csrf_exempt
def checkdiscountcodewithid(request, teacher_id, course_url):
    discount_code = request.POST.get('promoinput')
    course_id = request.POST.get('courseid')

    discount_courses = discount.objects.filter(course_id=course_id).filter(promo_code=discount_code)

    if len(discount_courses) > 0:
        discount_course = discount_courses[0]
        expire_date = datetime.strptime(discount_course.expire + " 00:00:00", '%Y-%m-%d %H:%M:%S')
        expire_date = pytz.utc.localize(expire_date)
        nowtime = datetime.today()
        nowtime = pytz.utc.localize(nowtime)

        if expire_date >= nowtime:
            return HttpResponse(discount_course.discount_percent)
        else:
            return HttpResponse("failed")
    
    return HttpResponse("failed")


def showFavList(request):
    if request.session.get('user_id') == None:
        return redirect('/')

    type = request.POST.get('type')
    page = request.POST.get('page')
    order = request.POST.get('order')

    if type == '' or type == None:
        type = -1
    else:
        type = int(type)

    if page == '' or page == None:
        page = 1
    else:
        page = int(page)

    if order == '' or order == None:
        order = 0
    else:
        order = int(order)

    # show fav page.., cart page...
    category_obj = categories.objects.all()
    favListShow, favCnt, alreadyinFavView, cartListShow, cartCnt, alreadyinCartView, cartTotalSum, noti_list, noti_cnt, msg_list, msg_cnt, stu_msg_list, stu_msg_cnt, total_msg_cnt = findheader(
        request.user.id)

    user_id = request.user.id
    favListTmp = student_favourite_courses.objects.filter(student_id_id=user_id)
    favList = []
    for fav in favListTmp:
        if type == -1:
            favList.append(fav)
        else:
            if Courses.objects.filter(id=fav.course_id_id, type=type).exists():
                favList.append(fav)

    discount = Discount.objects.all()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    for fav in favList:
        course = Courses.objects.get(pk=fav.course_id_id)
        fav.videoCnt = getVideoCnt(course)
        fav.stuCnt = student_register_courses.objects.filter(course_id_id=fav.course_id_id).count()
        fav.link = courseUrlGenerator(course)
        fav.created_at = course.created_at
        if discount.count() == 0:
            discount_percent = 1
        else:
            if now > discount[0].expire_date:
                discount_percent = 1
            else:
                not_str = discount[0].not_apply_course
                not_list = not_str.split('.')
                if str(fav.course_id_id) in not_list:
                    discount_percent = 1
                else:
                    discount_percent = (100 - discount[0].discount) / 100
        fav.discount_price = round(fav.course_id.price * discount_percent, 2)

        if student_cart_courses.objects.filter(course_id_id=fav.course_id_id, student_id_id=user_id).exists():
            fav.is_cart = 1
        else:
            fav.is_cart = 0
        rating_list = course_comments.objects.filter(course_id_id=course.id).values_list('rating', flat=True)
        sum = 0
        count = 0
        for rating in rating_list:
            sum += rating
            count += 1
        if count == 0:
            fav.rating = 0
        else:
            fav.rating = round(sum / count, 1)

    fav_list = favList
    if order == 1:
        fav_list = sorted(favList, key=attrgetter('rating'), reverse=True)
    elif order == 2:
        fav_list = sorted(favList, key=attrgetter('stuCnt'), reverse=True)
    elif order == 3:
        fav_list = sorted(favList, key=attrgetter('created_at'), reverse=True)

    wish_list_paginator = Paginator(fav_list, 4)

    try:
        favList = wish_list_paginator.page(page)
    except PageNotAnInteger:
        favList = wish_list_paginator.page(1)
    except EmptyPage:
        favList = wish_list_paginator.page(wish_list_paginator.num_pages)

    user_type = request.session.get("user_type")
    stu_courses = student_register_courses.objects.filter(student_id_id=request.user.id)
    return render(request, 'wishlist.html',
                  {'stu_courses': stu_courses, 'category_obj': category_obj, 'lang': getLanguage(request)[0], 'favList1': favList,
                   'cartList': cartListShow, 'favCnt': favCnt, 'favList': favListShow,
                   'cartCnt': cartCnt, 'cartTotalSum': cartTotalSum, 'noti_cnt': noti_cnt, 'page': page, 'type': type,
                   'noti_list': noti_list, 'msg_list': msg_list, 'msg_cnt': msg_cnt, 'order': order, 'stu_msg_list': stu_msg_list, 'stu_msg_cnt': stu_msg_cnt, 'total_msg_cnt': total_msg_cnt})


def viewProfile(request, id, pname):
    user = User.objects.get(pk=id)
    page = request.POST.get('page')
    page1 = request.POST.get('page1')
    order = request.POST.get('order')
    tab = request.POST.get('tab')
    if page == None or page == '':
        page = 1
    else:
        page = int(page)

    if page1 == None or page1 == '':
        page1 = 1
    else:
        page1 = int(page1)

    if order == None or order == '':
        order = 1
    else:
        order = int(order)

    if tab == None or tab == '':
        tab = 1
    else:
        tab = int(tab)
    print("order::", order)

    # show fav page.., cart page...
    favList = student_favourite_courses.objects.filter(student_id_id=request.user.id)
    favListShow = student_favourite_courses.objects.filter(student_id_id=request.user.id).order_by("-id")[:3]
    cartList = student_cart_courses.objects.filter(student_id_id=request.user.id)
    cartListShow = student_cart_courses.objects.filter(student_id_id=request.user.id).order_by("-id")[:3]
    cartTotalSum = 0

    # show notification...
    noti_list = notifications.objects.filter(user_id=request.user.id, is_read=0).order_by("-id")[:3]
    noti_cnt = notifications.objects.filter(user_id=request.user.id, is_read=0).count()

    if user_profile.objects.filter(user_id=id).exists():
        profile = user_profile.objects.filter(user_id=id)[0]
        catIds = profile.subcat_ids
        subCatStr1 = subcategories.objects.extra(where=["find_in_set(id,'" + catIds + "')"]).values_list('name',
                                                                                                         flat=True)
        subCatStr1 = map(str, subCatStr1)
        subCatStr = ','.join(subCatStr1)
        profile.subCatStr = subCatStr
        user.profile = profile

    discount = Discount.objects.all()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    courses = Courses.objects.filter(user_id=id, approval_status=2)
    for course in courses:
        course.link = courseUrlGenerator(course)
        rating_list = course_comments.objects.filter(course_id_id=course.id)
        course.rating = getRatingFunc(rating_list)
        if discount.count() == 0:
            discount_percent = 1
        else:
            if now > discount[0].expire_date:
                discount_percent = 1
            else:
                not_str = discount[0].not_apply_course
                not_list = not_str.split('.')
                if str(course.id) in not_list:
                    discount_percent = 1
                else:
                    discount_percent = (100 - discount[0].discount) / 100
        course.discount_price = round(course.price * discount_percent, 2)

    course_list_paginator = Paginator(courses, 3)
    try:
        course_list = course_list_paginator.page(page)
    except PageNotAnInteger:
        course_list = course_list_paginator.page(1)
    except EmptyPage:
        course_list = course_list_paginator.page(course_list_paginator.num_pages)

    favListShow, favCnt, alreadyinFavView, cartListShow, cartCnt, alreadyinCartView, cartTotalSum, noti_list, noti_cnt, msg_list, msg_cnt, stu_msg_list, stu_msg_cnt, total_msg_cnt = findheader(
        request.user.id)

    user.courses = course_list
    coursesID = Courses.objects.filter(user_id=id).values_list('id', flat=True)
    courseIDStr = map(str, coursesID)
    mystr = ','.join(courseIDStr)
    if order == 1:
        review = course_comments.objects.extra(where=["find_in_set(course_id_id,'" + mystr + "')"]).filter(
            approved_by_teacher=1).order_by('date')
    else:
        review = course_comments.objects.extra(where=["find_in_set(course_id_id,'" + mystr + "')"]).filter(
            approved_by_teacher=1).order_by('-date')
    user.review = review

    review_list_paginator = Paginator(review, 4)
    try:
        review = review_list_paginator.page(page1)
    except PageNotAnInteger:
        review = review_list_paginator.page(1)
    except EmptyPage:
        review = review_list_paginator.page(review_list_paginator.num_pages)

    course_id_arr = Courses.objects.filter(user_id=id).values_list('id', flat=True)
    course_id_arr = map(str, course_id_arr)
    course_id_str = ','.join(course_id_arr)
    ratings = course_comments.objects.extra(where=['find_in_set(course_id_id,"' + course_id_str + '")']).values_list(
        'rating', flat=True)
    sum = 0
    count = 0
    for rating in ratings:
        sum += rating
        count += 1
    if count == 0:
        user.total_rating = 0
    else:
        user.total_rating = round((sum / count), 2)
    user.reviewCnt = count
    stu_courses = student_register_courses.objects.filter(student_id_id=request.user.id)
    return render(request, 'profile.html',
                  {'teacher': user, 'favList': favListShow, 'lang': getLanguage(request)[0], 'cartList': cartListShow,
                   'favCnt': len(favList), "stu_courses": stu_courses,
                   'cartCnt': len(cartList), 'cartTotalSum': cartTotalSum, 'noti_cnt': noti_cnt, 'page': page,
                   'page1': page1, 'stu_msg_list': stu_msg_list, 'stu_msg_cnt': stu_msg_cnt, 'total_msg_cnt': total_msg_cnt,
                   'noti_list': noti_list, 'order': order, 'tab': tab, 'msg_list': msg_list, 'msg_cnt': msg_cnt})


def teacherProfile(request):
    id = request.POST.get('id')
    user = User.objects.get(pk=id)
    if user_profile.objects.filter(user_id=id).exists():
        profile = user_profile.objects.filter(user_id=id)[0]
        user.profile = profile
    return render(request, 'teacherProfile.html', {'user': user})


def deleteAccount(request):
    user_id = request.POST.get('id')

    User.objects.get(pk=user_id).delete()

    return JsonResponse({'msg': 'success'})


def deleteCourse(request):
    course_id = request.POST.get("id")
    deletec = Courses.objects.get(pk=course_id).delete()
    return JsonResponse({'msg': 'success'})


def sendResetPasswordEmail(request):
    email = request.POST.get('email')
    
    connection = get_connection()  # uses SMTP server specified in settings.py
    connection.open()  # If you don't open the connection manually, Django will automatically open, then tear down the connection in msg.send()
    imageLink = f"https://booctep.herokuapp.com/static/assets/img/favicon.png"
    text = '<!DOCTYPE HTML PUBLIC "-//W3C//DTD XHTML 1.0 Transitional //EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">'
    text += '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">'
    text += '<head><!--[if gte mso 9]><xml><o:OfficeDocumentSettings><o:AllowPNG/><o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings></xml><![endif]--><meta http-equiv="Content-Type" content="text/html; charset=UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><meta name="x-apple-disable-message-reformatting"><!--[if !mso]><!-->'
    text += '<meta http-equiv="X-UA-Compatible" content="IE=edge"><!--<![endif]--><title></title><style type="text/css">table, td { color: #000000; } a { color: #0000ee; text-decoration: underline; } @media (max-width: 480px) { #u_content_button_4 .v-padding { padding: 20px 50px !important; } }'
    text += '@media only screen and (min-width: 620px) {.u-row { width: 600px !important;}.u-row .u-col {vertical-align: top;}.u-row .u-col-100 {width: 600px !important;}}'
    text += '@media (max-width: 620px) {.u-row-container {max-width: 100% !important;padding-left: 0px !important;padding-right: 0px !important;}.u-row .u-col {min-width: 320px !important;max-width: 100% !important;display: block !important;}'
    text += '.u-row {width: calc(100% - 40px) !important;}.u-col {width: 100% !important;}.u-col > div {margin: 0 auto;}}body {margin: 0;padding: 0;}table,tr,td {vertical-align: top;border-collapse: collapse;}p {margin: 0;}'
    text += '.ie-container table,.mso-container table {table-layout: fixed;}* {line-height: inherit;}a[x-apple-data-detectors="true"] {color: inherit !important;text-decoration: none !important;}</style>'
    text += '<!--[if !mso]><!--><link href="https://fonts.googleapis.com/css?family=Lato:400,700&display=swap" rel="stylesheet" type="text/css"><link href="https://fonts.googleapis.com/css?family=Open+Sans:400,700&display=swap" rel="stylesheet" type="text/css"><link href="https://fonts.googleapis.com/css?family=Raleway:400,700&display=swap" rel="stylesheet" type="text/css"><!--<![endif]--></head>'
    text += '<body class="clean-body" style="margin: 0;padding: 0;-webkit-text-size-adjust: 100%;background-color: #efefef;color: #000000"><!--[if IE]><div class="ie-container"><![endif]--><!--[if mso]><div class="mso-container"><![endif]--><table style="border-collapse: collapse;table-layout: fixed;border-spacing: 0;mso-table-lspace: 0pt;mso-table-rspace: 0pt;vertical-align: top;min-width: 320px;Margin: 0 auto;background-color: #efefef;width:100%" cellpadding="0" cellspacing="0"><tbody><tr style="vertical-align: top"><td style="word-break: break-word;border-collapse: collapse !important;vertical-align: top"><!--[if (mso)|(IE)]><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td align="center" style="background-color: #efefef;"><![endif]--><div class="u-row-container" style="padding: 0px;background-color: transparent"><div class="u-row" style="Margin: 0 auto;min-width: 320px;max-width: 600px;overflow-wrap: break-word;word-wrap: break-word;word-break: break-word;background-color:   #d7dbf5;"><div style="border-collapse: collapse;display: table;width: 100%;background-color: transparent;"><!--[if (mso)|(IE)]><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td style="padding: 0px;background-color: transparent;" align="center"><table cellpadding="0" cellspacing="0" border="0" style="width:600px;"><tr style="background-color: #0000ff;"><![endif]--><!--[if (mso)|(IE)]><td align="center" width="600" style="width: 600px;padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;" valign="top"><![endif]--><div class="u-col u-col-100" style="max-width: 320px;min-width: 600px;display: table-cell;vertical-align: top;"><div style="width: 100% !important;"><!--[if (!mso)&(!IE)]><!--><div style="padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;"><!--<![endif]-->'
    text += '<table style="font-family:Open Sans,sans-serif;" role="presentation" cellpadding="0" cellspacing="0" width="100%" border="0"><tbody><tr><td style="overflow-wrap:break-word;word-break:break-word;padding:10px;font-family:Open Sans,sans-serif;" align="right"><table width="100%" cellpadding="0" cellspacing="0" border="0" ><tr>'
    text += '<td style="padding-right: 0px;padding-left: 0px;" align="center"><img align="center" border="0" src="{imageLink}" alt="Image" title="Image" style="outline: none;text-decoration: none;-ms-interpolation-mode: bicubic;clear: both;display: inline-block !important;border: none;height: auto;float: none;width: 100%;max-width: 80px;" width="80">'
    text += '</td></tr></table></td></tr></tbody></table><!--[if (!mso)&(!IE)]><!--></div><!--<![endif]--></div></div><!--[if (mso)|(IE)]></td><![endif]--><!--[if (mso)|(IE)]></tr></table></td></tr></table><![endif]--></div></div></div>'
    text += '<div class="u-row-container" style="padding: 0px;background-color: transparent"><div class="u-row" style="Margin: 0 auto;min-width: 320px;max-width: 600px;overflow-wrap: break-word;word-wrap: break-word;word-break: break-word;background-color: #ffffff;"><div style="border-collapse: collapse;display: table;width: 100%;background-color: transparent;">'
    text += '<!--[if (mso)|(IE)]><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td style="padding: 0px;background-color: transparent;" align="center"><table cellpadding="0" cellspacing="0" border="0" style="width:600px;"><tr style="background-color: #ffffff;"><![endif]--><!--[if (mso)|(IE)]><td align="center" width="600" style="width: 600px;padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;" valign="top"><![endif]--><div class="u-col u-col-100" style="max-width: 320px;min-width: 600px;display: table-cell;vertical-align: top;"><div style="width: 100% !important;"><!--[if (!mso)&(!IE)]><!--><div style="padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;"><!--<![endif]--><table style="font-family:Open Sans,sans-serif;" role="presentation" cellpadding="0" cellspacing="0" width="100%" border="0" >'
    text += '<tbody><tr><td style="overflow-wrap:break-word;word-break:break-word;padding:18px 10px 12px;font-family:Open Sans,sans-serif;" align="right"><div style="color: #333333; line-height: 140%; text-align: center; word-wrap: break-word;"><p style="font-size: 14px; line-height: 140%;">'
    text += '<span style="font-size: 22px; line-height: 30.8px;"><strong>اعادة تعيين كلمة المرور</strong></span></p></div></td></tr></tbody></table><!--[if (!mso)&(!IE)]><!--></div><!--<![endif]--></div></div><!--[if (mso)|(IE)]></td><![endif]--><!--[if (mso)|(IE)]></tr></table></td></tr></table><![endif]--></div></div></div><div class="u-row-container" style="padding: 0px;background-color: transparent">'
    text += '<div class="u-row" style="Margin: 0 auto;min-width: 320px;max-width: 600px;overflow-wrap: break-word;word-wrap: break-word;word-break: break-word;background-color: #ffffff;"><div style="border-collapse: collapse;display: table;width: 100%;background-color: transparent;">'
    text += '<!--[if (mso)|(IE)]><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td style="padding: 0px;background-color: transparent;" align="center"><table cellpadding="0" cellspacing="0" border="0" style="width:600px;"><tr style="background-color: #ffffff;"><![endif]-->'
    text += '<!--[if (mso)|(IE)]><td align="center" width="600" style="width: 600px;padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;" valign="top"><![endif]--><div class="u-col u-col-100" style="max-width: 320px;min-width: 600px;display: table-cell;vertical-align: top;"><div style="width: 100% !important;"><!--[if (!mso)&(!IE)]><!--><div style="padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;"><!--<![endif]-->'
    text += '<table style="font-family:Open Sans,sans-serif;" role="presentation" cellpadding="0" cellspacing="0" width="100%" border="0" ><tbody><tr>'
    text += '<td style="overflow-wrap:break-word;word-break:break-word;padding:0px 25px 10px;font-family:Open Sans,sans-serif;" align="left"><div style="color: #333333; line-height: 160%; text-align: center; word-wrap: break-word;"><p style="font-size: 14px; line-height: 160%; text-align: right;float:right">لتغيير كلمة المرور اضغط الرابط في الأسفل</p></div></td></tr></tbody></table><!--[if (!mso)&(!IE)]><!--></div><!--<![endif]--></div></div><!--[if (mso)|(IE)]></td><![endif]--><!--[if (mso)|(IE)]></tr></table></td></tr></table><![endif]--></div></div></div><div class="u-row-container" style="padding: 0px;background-color: transparent"><div class="u-row" style="Margin: 0 auto;min-width: 320px;max-width: 600px;overflow-wrap: break-word;word-wrap: break-word;word-break: break-word;background-color: #ffffff;"><div style="border-collapse: collapse;display: table;width: 100%;background-color: transparent;">'
    text += '<!--[if (mso)|(IE)]><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td style="padding: 0px;background-color: transparent;" align="center"><table cellpadding="0" cellspacing="0" border="0" style="width:600px;"><tr style="background-color: #ffffff;"><![endif]-->'
    text += '<!--[if (mso)|(IE)]><td align="center" width="600" style="width: 600px;padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;" valign="top"><![endif]-->'
    text += '<div class="u-col u-col-100" style="max-width: 320px;min-width: 600px;display: table-cell;vertical-align: top;"><div style="width: 100% !important;"><!--[if (!mso)&(!IE)]><!--><div style="padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;"><!--<![endif]--><table id="u_content_button_4" style="font-family:Open Sans,sans-serif;" role="presentation" cellpadding="0" cellspacing="0" width="100%" border="0"><tbody><tr><td style="overflow-wrap:break-word;word-break:break-word;padding:10px;font-family:Open Sans,sans-serif;" align="left"><div align="center"><!--[if mso]><table width="100%" cellpadding="0" cellspacing="0" border="0" style="border-spacing: 0; border-collapse: collapse; mso-table-lspace:0pt; mso-table-rspace:0pt;font-family:Open Sans,sans-serif;"><tr><td style="font-family:Open Sans,sans-serif;" align="center"><v:roundrect xmlns:v="urn:schemas-microsoft-com:vml" xmlns:w="urn:schemas-microsoft-com:office:word" href="" style="height:38px; v-text-anchor:middle; width:274px;" arcsize="92%" stroke="f" fillcolor="#1b36ab"><w:anchorlock/><center style="color:#FFFFFF;font-family:Open Sans,sans-serif;"><![endif]-->'
    text += '<a href="+ link + " target="_blank" style="box-sizing: border-box;display: inline-block;font-family:Open Sans,sans-serif;text-decoration: none;-webkit-text-size-adjust: none;text-align: center;color: #FFFFFF; background-color: #33BEFF; border-radius: 35px; -webkit-border-radius: 35px; -moz-border-radius: 35px; width:auto; max-width:100%; overflow-wrap: break-word; word-break: break-word; word-wrap:break-word; mso-border-alt: none;"><span class="v-padding" style="display:block;padding:12px 40px 10px;line-height:120%;"><span style="font-size: 14px; line-height: 16.8px;"><strong><span style="line-height: 16.8px; font-size: 14px;">تغيير </span></strong></span></span></a><!--[if mso]></center></v:roundrect></td></tr></table><![endif]--></div></td></tr></tbody></table>'
    text += '<!--[if (!mso)&(!IE)]><!--></div><!--<![endif]--></div></div><!--[if (mso)|(IE)]></td><![endif]--><!--[if (mso)|(IE)]></tr></table></td></tr></table><![endif]--></div></div></div><div class="u-row-container" style="padding: 0px;background-color: transparent"><div class="u-row" style="Margin: 0 auto;min-width: 320px;max-width: 600px;overflow-wrap: break-word;word-wrap: break-word;word-break: break-word;background-color: #ffffff;"><div style="border-collapse: collapse;display: table;width: 100%;background-color: transparent;">'
    text += '<!--[if (mso)|(IE)]><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td style="padding: 0px;background-color: transparent;" align="center"><table cellpadding="0" cellspacing="0" border="0" style="width:600px;"><tr style="background-color: #ffffff;"><![endif]--><!--[if (mso)|(IE)]><td align="center" width="600" style="width: 600px;padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;" valign="top"><![endif]--><div class="u-col u-col-100" style="max-width: 320px;min-width: 600px;display: table-cell;vertical-align: top;"><div style="width: 100% !important;"><!--[if (!mso)&(!IE)]><!-->'
    text += '<div style="padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;">'
    text += '<!--<![endif]--><table style="font-family:Open Sans,sans-serif;" role="presentation" cellpadding="0" cellspacing="0" width="100%" border="0"><tbody><tr><td style="overflow-wrap:break-word;word-break:break-word;padding:15px 10px 9px;font-family:Open Sans,sans-serif;" align="left">'
    text += '<table height="0px" align="center" border="0" cellpadding="0" cellspacing="0" width="72%" style="border-collapse: collapse;table-layout: fixed;border-spacing: 0;mso-table-lspace: 0pt;mso-table-rspace: 0pt;vertical-align: top;border-top: 1px solid #413d45;-ms-text-size-adjust: 100%;-webkit-text-size-adjust: 100%"><tbody><tr style="vertical-align: top">'
    text += '<td style="word-break: break-word;border-collapse: collapse !important;vertical-align: top;font-size: 0px;line-height: 0px;mso-line-height-rule: exactly;-ms-text-size-adjust: 100%;-webkit-text-size-adjust: 100%">'
    text += '<span>&#160;</span></td></tr></tbody></table></td></tr></tbody></table><table style="font-family:Open Sans,sans-serif;" role="presentation" cellpadding="0" cellspacing="0" width="100%" border="0">'
    text += '<tbody><tr><td style="overflow-wrap:break-word;word-break:break-word;padding:10px;font-family:Open Sans,sans-serif;" align="left"><div style="color: #7e7e81; line-height: 150%; text-align: center; word-wrap: break-word;"><p style="font-size: 14px; line-height: 150%;">'
    text += '<span style="font-size: 12px; line-height: 18px;">هذه الرسالة تلقائية من فريق دعم منصة بوستيب, نتمنى لك يوما سعيد</span><span style="font-size: 12px; line-height: 18px;"></span>'
    text += '</p></div></td></tr></tbody></table><!--[if (!mso)&(!IE)]><!--></div><!--<![endif]--></div></div><!--[if (mso)|(IE)]></td><![endif]--><!--[if (mso)|(IE)]></tr></table></td></tr></table><![endif]--></div></div></div><!--[if (mso)|(IE)]></td></tr></table><![endif]--></td></tr></tbody></table><!--[if mso]></div><![endif]--><!--[if IE]></div><![endif]--></body></html>'

    to = email
    subject = 'Thanks :)'

    msg = EmailMultiAlternatives(subject, '...', 'support@booctep.com', [to])
    msg.attach_alternative(text, "text/html")
    msg.send()
    connection.close()  # Cleanup
    return HttpResponse("success")


def resetPassword(request):
    msg = ''
    email = request.POST.get('email')
    hashval = hashlib.md5(email.encode())
    hashString = str(hashval.hexdigest())
    lang = getLanguage(request)[0]
    domain = request.META['HTTP_HOST']
    if lang == 'ar/':
        link = "http://" + domain + "/" + lang + "forgot_password/?param=" + hashString
    else:
        link = "http://" + domain + "/en/forgot_password/?param=" + hashString
    
    try:
        obj = User.objects.get(email=email)
        if obj is not None:
            obj.hash = hashString
            obj.save()

            connection = get_connection()  # uses SMTP server specified in settings.py
            connection.open()  # If you don't open the connection manually, Django will automatically open, then tear down the connection in msg.send()
            imageLink = f"https://booctep.herokuapp.com/static/assets/img/favicon.png"
            text = '<!DOCTYPE HTML PUBLIC "-//W3C//DTD XHTML 1.0 Transitional //EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">'
            text += '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">'
            text += '<head><!--[if gte mso 9]><xml><o:OfficeDocumentSettings><o:AllowPNG/><o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings></xml><![endif]--><meta http-equiv="Content-Type" content="text/html; charset=UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><meta name="x-apple-disable-message-reformatting"><!--[if !mso]><!-->'
            text += '<meta http-equiv="X-UA-Compatible" content="IE=edge"><!--<![endif]--><title></title><style type="text/css">table, td { color: #000000; } a { color: #0000ee; text-decoration: underline; } @media (max-width: 480px) { #u_content_button_4 .v-padding { padding: 20px 50px !important; } }'
            text += '@media only screen and (min-width: 620px) {.u-row { width: 600px !important;}.u-row .u-col {vertical-align: top;}.u-row .u-col-100 {width: 600px !important;}}'
            text += '@media (max-width: 620px) {.u-row-container {max-width: 100% !important;padding-left: 0px !important;padding-right: 0px !important;}.u-row .u-col {min-width: 320px !important;max-width: 100% !important;display: block !important;}'
            text += '.u-row {width: calc(100% - 40px) !important;}.u-col {width: 100% !important;}.u-col > div {margin: 0 auto;}}body {margin: 0;padding: 0;}table,tr,td {vertical-align: top;border-collapse: collapse;}p {margin: 0;}'
            text += '.ie-container table,.mso-container table {table-layout: fixed;}* {line-height: inherit;}a[x-apple-data-detectors="true"] {color: inherit !important;text-decoration: none !important;}</style>'
            text += '<!--[if !mso]><!--><link href="https://fonts.googleapis.com/css?family=Lato:400,700&display=swap" rel="stylesheet" type="text/css"><link href="https://fonts.googleapis.com/css?family=Open+Sans:400,700&display=swap" rel="stylesheet" type="text/css"><link href="https://fonts.googleapis.com/css?family=Raleway:400,700&display=swap" rel="stylesheet" type="text/css"><!--<![endif]--></head>'
            text += '<body class="clean-body" style="margin: 0;padding: 0;-webkit-text-size-adjust: 100%;background-color: #efefef;color: #000000"><!--[if IE]><div class="ie-container"><![endif]--><!--[if mso]><div class="mso-container"><![endif]--><table style="border-collapse: collapse;table-layout: fixed;border-spacing: 0;mso-table-lspace: 0pt;mso-table-rspace: 0pt;vertical-align: top;min-width: 320px;Margin: 0 auto;background-color: #efefef;width:100%" cellpadding="0" cellspacing="0"><tbody><tr style="vertical-align: top"><td style="word-break: break-word;border-collapse: collapse !important;vertical-align: top"><!--[if (mso)|(IE)]><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td align="center" style="background-color: #efefef;"><![endif]--><div class="u-row-container" style="padding: 0px;background-color: transparent"><div class="u-row" style="Margin: 0 auto;min-width: 320px;max-width: 600px;overflow-wrap: break-word;word-wrap: break-word;word-break: break-word;background-color:   #d7dbf5;"><div style="border-collapse: collapse;display: table;width: 100%;background-color: transparent;"><!--[if (mso)|(IE)]><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td style="padding: 0px;background-color: transparent;" align="center"><table cellpadding="0" cellspacing="0" border="0" style="width:600px;"><tr style="background-color: #0000ff;"><![endif]--><!--[if (mso)|(IE)]><td align="center" width="600" style="width: 600px;padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;" valign="top"><![endif]--><div class="u-col u-col-100" style="max-width: 320px;min-width: 600px;display: table-cell;vertical-align: top;"><div style="width: 100% !important;"><!--[if (!mso)&(!IE)]><!--><div style="padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;"><!--<![endif]-->'
            text += '<table style="font-family:Open Sans,sans-serif;" role="presentation" cellpadding="0" cellspacing="0" width="100%" border="0"><tbody><tr><td style="overflow-wrap:break-word;word-break:break-word;padding:10px;font-family:Open Sans,sans-serif;" align="left"><table width="100%" cellpadding="0" cellspacing="0" border="0" ><tr>'
            text += '<td style="padding-right: 0px;padding-left: 0px;" align="center"><img align="center" border="0" src="{imageLink}" alt="Image" title="Image" style="outline: none;text-decoration: none;-ms-interpolation-mode: bicubic;clear: both;display: inline-block !important;border: none;height: auto;float: none;width: 100%;max-width: 80px;" width="80">'
            text += '</td></tr></table></td></tr></tbody></table><!--[if (!mso)&(!IE)]><!--></div><!--<![endif]--></div></div><!--[if (mso)|(IE)]></td><![endif]--><!--[if (mso)|(IE)]></tr></table></td></tr></table><![endif]--></div></div></div>'
            text += '<div class="u-row-container" style="padding: 0px;background-color: transparent"><div class="u-row" style="Margin: 0 auto;min-width: 320px;max-width: 600px;overflow-wrap: break-word;word-wrap: break-word;word-break: break-word;background-color: #ffffff;"><div style="border-collapse: collapse;display: table;width: 100%;background-color: transparent;">'
            text += '<!--[if (mso)|(IE)]><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td style="padding: 0px;background-color: transparent;" align="center"><table cellpadding="0" cellspacing="0" border="0" style="width:600px;"><tr style="background-color: #ffffff;"><![endif]--><!--[if (mso)|(IE)]><td align="center" width="600" style="width: 600px;padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;" valign="top"><![endif]--><div class="u-col u-col-100" style="max-width: 320px;min-width: 600px;display: table-cell;vertical-align: top;"><div style="width: 100% !important;"><!--[if (!mso)&(!IE)]><!--><div style="padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;"><!--<![endif]--><table style="font-family:Open Sans,sans-serif;" role="presentation" cellpadding="0" cellspacing="0" width="100%" border="0" >'
            text += '<tbody><tr><td style="overflow-wrap:break-word;word-break:break-word;padding:18px 10px 12px;font-family:Open Sans,sans-serif;" align="left"><div style="color: #333333; line-height: 140%; text-align: center; word-wrap: break-word;"><p style="font-size: 14px; line-height: 140%;">'
            text += '<span style="font-size: 22px; line-height: 30.8px;"><strong>إعادة تعيين كلمة المرور</strong></span></p></div></td></tr></tbody></table><!--[if (!mso)&(!IE)]><!--></div><!--<![endif]--></div></div><!--[if (mso)|(IE)]></td><![endif]--><!--[if (mso)|(IE)]></tr></table></td></tr></table><![endif]--></div></div></div><div class="u-row-container" style="padding: 0px;background-color: transparent">'
            text += '<div class="u-row" style="Margin: 0 auto;min-width: 320px;max-width: 600px;overflow-wrap: break-word;word-wrap: break-word;word-break: break-word;background-color: #ffffff;"><div style="border-collapse: collapse;display: table;width: 100%;background-color: transparent;">'
            text += '<!--[if (mso)|(IE)]><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td style="padding: 0px;background-color: transparent;" align="center"><table cellpadding="0" cellspacing="0" border="0" style="width:600px;"><tr style="background-color: #ffffff;"><![endif]-->'
            text += '<!--[if (mso)|(IE)]><td align="center" width="600" style="width: 600px;padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;" valign="top"><![endif]--><div class="u-col u-col-100" style="max-width: 320px;min-width: 600px;display: table-cell;vertical-align: top;"><div style="width: 100% !important;"><!--[if (!mso)&(!IE)]><!--><div style="padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;"><!--<![endif]-->'
            text += '<table style="font-family:Open Sans,sans-serif;" role="presentation" cellpadding="0" cellspacing="0" width="100%" border="0" ><tbody><tr>'
            text += '<td style="overflow-wrap:break-word;word-break:break-word;padding:0px 25px 10px;font-family:Open Sans,sans-serif;" align="left"><div style="color: #333333; line-height: 160%; text-align: center; word-wrap: break-word;"><p style="font-size: 14px; line-height: 160%; text-align: right;">لإعادة تعيين كلمة المرور, الرجاء الضغط على الرابط بالأسفل</p></div></td></tr></tbody></table><!--[if (!mso)&(!IE)]><!--></div><!--<![endif]--></div></div><!--[if (mso)|(IE)]></td><![endif]--><!--[if (mso)|(IE)]></tr></table></td></tr></table><![endif]--></div></div></div><div class="u-row-container" style="padding: 0px;background-color: transparent"><div class="u-row" style="Margin: 0 auto;min-width: 320px;max-width: 600px;overflow-wrap: break-word;word-wrap: break-word;word-break: break-word;background-color: #ffffff;"><div style="border-collapse: collapse;display: table;width: 100%;background-color: transparent;">'
            text += '<!--[if (mso)|(IE)]><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td style="padding: 0px;background-color: transparent;" align="center"><table cellpadding="0" cellspacing="0" border="0" style="width:600px;"><tr style="background-color: #ffffff;"><![endif]-->'
            text += '<!--[if (mso)|(IE)]><td align="center" width="600" style="width: 600px;padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;" valign="top"><![endif]-->'
            text += '<div class="u-col u-col-100" style="max-width: 320px;min-width: 600px;display: table-cell;vertical-align: top;"><div style="width: 100% !important;"><!--[if (!mso)&(!IE)]><!--><div style="padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;"><!--<![endif]--><table id="u_content_button_4" style="font-family:Open Sans,sans-serif;" role="presentation" cellpadding="0" cellspacing="0" width="100%" border="0"><tbody><tr><td style="overflow-wrap:break-word;word-break:break-word;padding:10px;font-family:Open Sans,sans-serif;" align="left"><div align="center"><!--[if mso]><table width="100%" cellpadding="0" cellspacing="0" border="0" style="border-spacing: 0; border-collapse: collapse; mso-table-lspace:0pt; mso-table-rspace:0pt;font-family:Open Sans,sans-serif;"><tr><td style="font-family:Open Sans,sans-serif;" align="center"><v:roundrect xmlns:v="urn:schemas-microsoft-com:vml" xmlns:w="urn:schemas-microsoft-com:office:word" href="" style="height:38px; v-text-anchor:middle; width:274px;" arcsize="92%" stroke="f" fillcolor="#1b36ab"><w:anchorlock/><center style="color:#FFFFFF;font-family:Open Sans,sans-serif;"><![endif]-->'
            text += '<a href="' + link + '" target="_blank" style="box-sizing: border-box;display: inline-block;font-family:Open Sans,sans-serif;text-decoration: none;-webkit-text-size-adjust: none;text-align: center;color: #FFFFFF; background-color: #33BEFF; border-radius: 35px; -webkit-border-radius: 35px; -moz-border-radius: 35px; width:auto; max-width:100%; overflow-wrap: break-word; word-break: break-word; word-wrap:break-word; mso-border-alt: none;"><span class="v-padding" style="display:block;padding:12px 40px 10px;line-height:120%;"><span style="font-size: 14px; line-height: 16.8px;"><strong><span style="line-height: 16.8px; font-size: 14px;"> تغيير كلمة المرور</span></strong></span></span></a><!--[if mso]></center></v:roundrect></td></tr></table><![endif]--></div></td></tr></tbody></table>'
            text += '<!--[if (!mso)&(!IE)]><!--></div><!--<![endif]--></div></div><!--[if (mso)|(IE)]></td><![endif]--><!--[if (mso)|(IE)]></tr></table></td></tr></table><![endif]--></div></div></div><div class="u-row-container" style="padding: 0px;background-color: transparent"><div class="u-row" style="Margin: 0 auto;min-width: 320px;max-width: 600px;overflow-wrap: break-word;word-wrap: break-word;word-break: break-word;background-color: #ffffff;"><div style="border-collapse: collapse;display: table;width: 100%;background-color: transparent;">'
            text += '<!--[if (mso)|(IE)]><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td style="padding: 0px;background-color: transparent;" align="center"><table cellpadding="0" cellspacing="0" border="0" style="width:600px;"><tr style="background-color: #ffffff;"><![endif]--><!--[if (mso)|(IE)]><td align="center" width="600" style="width: 600px;padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;" valign="top"><![endif]--><div class="u-col u-col-100" style="max-width: 320px;min-width: 600px;display: table-cell;vertical-align: top;"><div style="width: 100% !important;"><!--[if (!mso)&(!IE)]><!-->'
            text += '<div style="padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;">'
            text += '<!--<![endif]--><table style="font-family:Open Sans,sans-serif;" role="presentation" cellpadding="0" cellspacing="0" width="100%" border="0"><tbody><tr><td style="overflow-wrap:break-word;word-break:break-word;padding:15px 10px 9px;font-family:Open Sans,sans-serif;" align="left">'
            text += '<table height="0px" align="center" border="0" cellpadding="0" cellspacing="0" width="72%" style="border-collapse: collapse;table-layout: fixed;border-spacing: 0;mso-table-lspace: 0pt;mso-table-rspace: 0pt;vertical-align: top;border-top: 1px solid #DFF2F5;-ms-text-size-adjust: 100%;-webkit-text-size-adjust: 100%"><tbody><tr style="vertical-align: top">'
            text += '<td style="word-break: break-word;border-collapse: collapse !important;vertical-align: top;font-size: 0px;line-height: 0px;mso-line-height-rule: exactly;-ms-text-size-adjust: 100%;-webkit-text-size-adjust: 100%">'
            text += '<span>&#160;</span></td></tr></tbody></table></td></tr></tbody></table><table style="font-family:Open Sans,sans-serif;" role="presentation" cellpadding="0" cellspacing="0" width="100%" border="0">'
            text += '<tbody><tr><td style="overflow-wrap:break-word;word-break:break-word;padding:10px;font-family:Open Sans,sans-serif;" align="left"><div style="color: #7e7e81; line-height: 150%; text-align: center; word-wrap: break-word;"><p style="font-size: 14px; line-height: 150%;">'
            text += '<span style="font-size: 12px; line-height: 18px;">هذه الرسالة تلقائية من فريق دعم منصة بوستيب, نتمنى لك يوما سعيد</span><span style="font-size: 12px; line-height: 18px;"></span>'
            text += '</p></div></td></tr></tbody></table><!--[if (!mso)&(!IE)]><!--></div><!--<![endif]--></div></div><!--[if (mso)|(IE)]></td><![endif]--><!--[if (mso)|(IE)]></tr></table></td></tr></table><![endif]--></div></div></div><!--[if (mso)|(IE)]></td></tr></table><![endif]--></td></tr></tbody></table><!--[if mso]></div><![endif]--><!--[if IE]></div><![endif]--></body></html>'

            to = email
            subject = 'Reset password request'

            msg = EmailMultiAlternatives(subject, '...', 'support@booctep.com', [to])
            msg.attach_alternative(text, "text/html")
            msg.send()

        else:
            msg = 'error'
            hashString = "0"
    except:
        tb = sys.exc_info()[2]
        tbinfo = traceback.format_tb(tb)[0]
        msg = tbinfo + "\n" + ": " + str(sys.exc_info())
        hashString = "0"

    return render(request, 'resetpassword.html', {'lang': getLanguage(request)[0]})


def postResetPassword(request):
    email = request.POST.get('email')
    password = request.POST.get('password')
    user = User.objects.get(email=email)
    user.set_password(password)
    status = 1
    ret = {
        'status': status
    }
    return JsonResponse(ret)


def enrollment(request, course_id):
    if request.session.get('user_id') == None:
        return redirect('/')
    user_id = request.session.get("user_id")
    user_type = request.session.get("user_type")

    # if user's type is teacher then change his account to stu&teach
    if user_type == "teacher":
        user = User.objects.get(id=user_id)
        user.group_id = 4
        user.save()
        request.session['user_type'] = "stuteach"

    register_courses = student_register_courses.objects.filter(course_id_id=course_id).filter(student_id_id=user_id)
    if register_courses.count() == 0:
        time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        register_course = student_register_courses(
            course_id_id=course_id,
            student_id_id=user_id,
            last_completed_section_id=0,
            date_created=time,
            withdraw=0
        )
        register_course.save()

    course = Courses.objects.get(pk=course_id)
    course.category = categories.objects.get(pk=course.scat_id)
    
    similar_cat = course.subcat_id
    similar_parent_cat = course.scat_id

    register_course_ids = student_register_courses.objects.filter(student_id_id=user_id).values_list('course_id_id', flat=True)
    similar_course = Courses.objects.filter(Q(subcat_id=similar_cat) | Q(scat_id=similar_parent_cat)).filter(approval_status=2).exclude(id=course_id).exclude(id__in=register_course_ids).order_by('scat_id')

    discount = Discount.objects.all()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    for i in similar_course:
        if discount.count() == 0:
            discount_percent = 1
        else:
            if now > discount[0].expire_date:
                discount_percent = 1
            else:
                not_str = discount[0].not_apply_course
                not_list = not_str.split('.')
                if str(i.id) in not_list:
                    discount_percent = 1
                else:
                    discount_percent = (100 - discount[0].discount) / 100
        i.discount_price = round(i.price * discount_percent, 2)

    for c in similar_course:
        c.link = courseUrlGenerator(c)
        rate_list = course_comments.objects.filter(course_id_id=c.id)
        c.rating = getRatingFunc(rate_list)
        c.ratingCnt = course_comments.objects.filter(course_id_id=c.id).count()
        c.stuCnt = len(rate_list)
        c.videoCnt = getVideoCnt(c)

    similar_course = sorted(similar_course, key=attrgetter('rating'), reverse=True)[:5]

    favListShow, favCnt, alreadyinFavView, cartListShow, cartCnt, alreadyinCartView, cartTotalSum, noti_list, noti_cnt, msg_list, msg_cnt, stu_msg_list, stu_msg_cnt, total_msg_cnt = findheader(
        request.user.id)
    stu_courses = student_register_courses.objects.filter(student_id_id=request.user.id)
    
    # Sending to the creator of this course
    teacher_id = Courses.objects.get(pk=course_id).user_id
    teacher = User.objects.get(pk=teacher_id)
    to = teacher.email
    student = User.objects.get(pk=user_id)
    to1 = student.email
    imageLink = f"https://booctep.herokuapp.com/static/assets/img/favicon.png"
    link = ""
    lang = getLanguage(request)[0]
    domain = request.META['HTTP_HOST']
    if lang == 'ar/':
        link = "http://" + domain + "/" + lang + "courses/"
    else:
        link = "http://" + domain + "/en/courses/"
    
    
    text = '<!DOCTYPE HTML PUBLIC "-//W3C//DTD XHTML 1.0 Transitional //EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">'
    text +='<html xmlns="http://www.w3.org/1999/xhtml" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">'
    text +='<head><!--[if gte mso 9]><xml><o:OfficeDocumentSettings><o:AllowPNG/><o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings></xml><![endif]-->'
    text +='<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">'
    text +='<meta name="viewport" content="width=device-width, initial-scale=1.0"><meta name="x-apple-disable-message-reformatting"><!--[if !mso]><!--><meta http-equiv="X-UA-Compatible" content="IE=edge"><!--<![endif]-->'
    text +='<title></title>'
    text +='<style type="text/css">table, td { color: #000000; } a { color: #0000ee; text-decoration: underline; } @media (max-width: 480px) { #u_content_button_4 .v-padding { padding: 20px 50px !important; } }@media only screen and (min-width: 620px) {.u-row { width: 600px !important;}.u-row .u-col {vertical-align: top;}.u-row .u-col-100 {width: 600px !important;}}@media (max-width: 620px) {.u-row-container {max-width: 100% !important;padding-left: 0px !important;padding-right: 0px !important;}.u-row .u-col {min-width: 320px !important;max-width: 100% !important;display: block !important;}.u-row {width: calc(100% - 40px) !important;}.u-col {width: 100% !important;}.u-col > div {margin: 0 auto;}}body {margin: 0;padding: 0;}table,tr,td {vertical-align: top;border-collapse: collapse;}p {margin: 0;}.ie-container table,.mso-container table {table-layout: fixed;}* {line-height: inherit;}a[x-apple-data-detectors="true"] {color: inherit !important;text-decoration: none !important;}</style><!--[if !mso]><!-->'
    text +='<link href="https://fonts.googleapis.com/css?family=Lato:400,700&display=swap" rel="stylesheet" type="text/css">'
    text +='<link href="https://fonts.googleapis.com/css?family=Open+Sans:400,700&display=swap" rel="stylesheet" type="text/css">'
    text +='<link href="https://fonts.googleapis.com/css?family=Raleway:400,700&display=swap" rel="stylesheet" type="text/css"><!--<![endif]--></head><body class="clean-body" style="margin: 0;padding: 0;-webkit-text-size-adjust: 100%;background-color: #efefef;color: #000000"><!--[if IE]><div class="ie-container"><![endif]--><!--[if mso]><div class="mso-container"><![endif]--><table style="border-collapse: collapse;table-layout: fixed;border-spacing: 0;mso-table-lspace: 0pt;mso-table-rspace: 0pt;vertical-align: top;min-width: 320px;Margin: 0 auto;background-color: #efefef;width:100%" cellpadding="0" cellspacing="0"><tbody><tr style="vertical-align: top"><td style="word-break: break-word;border-collapse: collapse !important;vertical-align: top"><!--[if (mso)|(IE)]><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td align="center" style="background-color: #efefef;"><![endif]--><div class="u-row-container" style="padding: 0px;background-color: transparent"><div class="u-row" style="Margin: 0 auto;min-width: 320px;max-width: 600px;overflow-wrap: break-word;word-wrap: break-word;word-break: break-word;background-color:   #d7dbf5;"><div style="border-collapse: collapse;display: table;width: 100%;background-color: transparent;"><!--[if (mso)|(IE)]><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td style="padding: 0px;background-color: transparent;" align="center"><table cellpadding="0" cellspacing="0" border="0" style="width:600px;"><tr style="background-color: #0000ff;"><![endif]--><!--[if (mso)|(IE)]><td align="center" width="600" style="width: 600px;padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;" valign="top"><![endif]--><div class="u-col u-col-100" style="max-width: 320px;min-width: 600px;display: table-cell;vertical-align: top;"><div style="width: 100% !important;"><!--[if (!mso)&(!IE)]><!--><div style="padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;"><!--<![endif]--><table style="font-family:Open Sans,sans-serif;" role="presentation" cellpadding="0" cellspacing="0" width="100%" border="0"><tbody><tr><td style="overflow-wrap:break-word;word-break:break-word;padding:10px;font-family:Open Sans,sans-serif;" align="left"><table width="100%" cellpadding="0" cellspacing="0" border="0" ><tr><td style="padding-right: 0px;padding-left: 0px;" align="center">'
    text +='<img align="center" border="0" src="' + imageLink + '" alt="Image" title="Image" style="outline: none;text-decoration: none;-ms-interpolation-mode: bicubic;clear: both;display: inline-block !important;border: none;height: auto;float: none;width: 100%;max-width: 80px;" width="80"></td></tr></table></td></tr></tbody></table><!--[if (!mso)&(!IE)]><!--></div><!--<![endif]--></div></div><!--[if (mso)|(IE)]></td><![endif]--><!--[if (mso)|(IE)]></tr></table></td></tr></table><![endif]--></div></div></div><div class="u-row-container" style="padding: 0px;background-color: transparent"><div class="u-row" style="Margin: 0 auto;min-width: 320px;max-width: 600px;overflow-wrap: break-word;word-wrap: break-word;word-break: break-word;background-color: #ffffff;"><div style="border-collapse: collapse;display: table;width: 100%;background-color: transparent;"><!--[if (mso)|(IE)]><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td style="padding: 0px;background-color: transparent;" align="center"><table cellpadding="0" cellspacing="0" border="0" style="width:600px;"><tr style="background-color: #ffffff;"><![endif]--><!--[if (mso)|(IE)]><td align="center" width="600" style="width: 600px;padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;" valign="top"><![endif]--><div class="u-col u-col-100" style="max-width: 320px;min-width: 600px;display: table-cell;vertical-align: top;"><div style="width: 100% !important;"><!--[if (!mso)&(!IE)]><!--><div style="padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;"><!--<![endif]--><table style="font-family:Open Sans,sans-serif;" role="presentation" cellpadding="0" cellspacing="0" width="100%" border="0" ><tbody><tr><td style="overflow-wrap:break-word;word-break:break-word;padding:18px 10px 12px;font-family:Open Sans,sans-serif;" align="left"><div style="color: #333333; line-height: 140%; text-align: center; word-wrap: break-word;"><p style="font-size: 14px; line-height: 140%;"><span style="font-size: 22px; line-height: 30.8px;"><strong>Good News!</strong></span></p></div></td></tr></tbody></table><!--[if (!mso)&(!IE)]><!--></div><!--<![endif]--></div></div><!--[if (mso)|(IE)]></td><![endif]--><!--[if (mso)|(IE)]></tr></table></td></tr></table><![endif]--></div></div></div><div class="u-row-container" style="padding: 0px;background-color: transparent"><div class="u-row" style="Margin: 0 auto;min-width: 320px;max-width: 600px;overflow-wrap: break-word;word-wrap: break-word;word-break: break-word;background-color: #ffffff;"><div style="border-collapse: collapse;display: table;width: 100%;background-color: transparent;"><!--[if (mso)|(IE)]><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td style="padding: 0px;background-color: transparent;" align="center"><table cellpadding="0" cellspacing="0" border="0" style="width:600px;"><tr style="background-color: #ffffff;"><![endif]--><!--[if (mso)|(IE)]><td align="center" width="600" style="width: 600px;padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;" valign="top"><![endif]--><div class="u-col u-col-100" style="max-width: 320px;min-width: 600px;display: table-cell;vertical-align: top;"><div style="width: 100% !important;"><!--[if (!mso)&(!IE)]><!--><div style="padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;"><!--<![endif]--><table style="font-family:Open Sans,sans-serif;" role="presentation" cellpadding="0" cellspacing="0" width="100%" border="0" ><tbody><tr><td style="overflow-wrap:break-word;word-break:break-word;padding:0px 25px 10px;font-family:Open Sans,sans-serif;" align="left"><div style="color: #333333; line-height: 160%; text-align: center; word-wrap: break-word;"><p style="font-size: 14px; line-height: 160%; text-align: left;">Hello Dear!</br>Someone purchased your course! Please check your courses.</p></div></td></tr></tbody></table><!--[if (!mso)&(!IE)]><!--></div><!--<![endif]--></div></div><!--[if (mso)|(IE)]></td><![endif]--><!--[if (mso)|(IE)]></tr></table></td></tr></table><![endif]--></div></div></div><div class="u-row-container" style="padding: 0px;background-color: transparent"><div class="u-row" style="Margin: 0 auto;min-width: 320px;max-width: 600px;overflow-wrap: break-word;word-wrap: break-word;word-break: break-word;background-color: #ffffff;"><div style="border-collapse: collapse;display: table;width: 100%;background-color: transparent;"><!--[if (mso)|(IE)]><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td style="padding: 0px;background-color: transparent;" align="center"><table cellpadding="0" cellspacing="0" border="0" style="width:600px;"><tr style="background-color: #ffffff;"><![endif]--><!--[if (mso)|(IE)]><td align="center" width="600" style="width: 600px;padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;" valign="top"><![endif]--><div class="u-col u-col-100" style="max-width: 320px;min-width: 600px;display: table-cell;vertical-align: top;"><div style="width: 100% !important;"><!--[if (!mso)&(!IE)]><!--><div style="padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;"><!--<![endif]--><table id="u_content_button_4" style="font-family:Open Sans,sans-serif;" role="presentation" cellpadding="0" cellspacing="0" width="100%" border="0"><tbody><tr><td style="overflow-wrap:break-word;word-break:break-word;padding:10px;font-family:Open Sans,sans-serif;" align="left"><div align="center"><!--[if mso]><table width="100%" cellpadding="0" cellspacing="0" border="0" style="border-spacing: 0; border-collapse: collapse; mso-table-lspace:0pt; mso-table-rspace:0pt;font-family:Open Sans,sans-serif;"><tr><td style="font-family:Open Sans,sans-serif;" align="center"><v:roundrect xmlns:v="urn:schemas-microsoft-com:vml" xmlns:w="urn:schemas-microsoft-com:office:word" href="" style="height:38px; v-text-anchor:middle; width:274px;" arcsize="92%" stroke="f" fillcolor="#1b36ab"><w:anchorlock/><center style="color:#FFFFFF;font-family:Open Sans,sans-serif;"><![endif]-->'
    text +='<a href="' + link + '" target="_blank" style="box-sizing: border-box;display: inline-block;font-family:Open Sans,sans-serif;text-decoration: none;-webkit-text-size-adjust: none;text-align: center;color: #FFFFFF; background-color: #1b36ab; border-radius: 35px; -webkit-border-radius: 35px; -moz-border-radius: 35px; width:auto; max-width:100%; overflow-wrap: break-word; word-break: break-word; word-wrap:break-word; mso-border-alt: none;"><span class="v-padding" style="display:block;padding:12px 40px 10px;line-height:120%;"><span style="font-size: 14px; line-height: 16.8px;"><strong><span style="line-height: 16.8px; font-size: 14px;">Go to your courses</span></strong></span></span></a><!--[if mso]></center></v:roundrect></td></tr></table><![endif]--></div></td></tr></tbody></table><!--[if (!mso)&(!IE)]><!--></div><!--<![endif]--></div></div><!--[if (mso)|(IE)]></td><![endif]--><!--[if (mso)|(IE)]></tr></table></td></tr></table><![endif]--></div></div></div><div class="u-row-container" style="padding: 0px;background-color: transparent"><div class="u-row" style="Margin: 0 auto;min-width: 320px;max-width: 600px;overflow-wrap: break-word;word-wrap: break-word;word-break: break-word;background-color: #ffffff;"><div style="border-collapse: collapse;display: table;width: 100%;background-color: transparent;"><!--[if (mso)|(IE)]><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td style="padding: 0px;background-color: transparent;" align="center"><table cellpadding="0" cellspacing="0" border="0" style="width:600px;"><tr style="background-color: #ffffff;"><![endif]--><!--[if (mso)|(IE)]><td align="center" width="600" style="width: 600px;padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;" valign="top"><![endif]--><div class="u-col u-col-100" style="max-width: 320px;min-width: 600px;display: table-cell;vertical-align: top;"><div style="width: 100% !important;"><!--[if (!mso)&(!IE)]><!--><div style="padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;"><!--<![endif]--><table style="font-family:Open Sans,sans-serif;" role="presentation" cellpadding="0" cellspacing="0" width="100%" border="0"><tbody><tr><td style="overflow-wrap:break-word;word-break:break-word;padding:15px 10px 9px;font-family:Open Sans,sans-serif;" align="left"><table height="0px" align="center" border="0" cellpadding="0" cellspacing="0" width="72%" style="border-collapse: collapse;table-layout: fixed;border-spacing: 0;mso-table-lspace: 0pt;mso-table-rspace: 0pt;vertical-align: top;border-top: 1px solid #413d45;-ms-text-size-adjust: 100%;-webkit-text-size-adjust: 100%"><tbody><tr style="vertical-align: top"><td style="word-break: break-word;border-collapse: collapse !important;vertical-align: top;font-size: 0px;line-height: 0px;mso-line-height-rule: exactly;-ms-text-size-adjust: 100%;-webkit-text-size-adjust: 100%"><span>&#160;</span></td></tr></tbody></table></td></tr></tbody></table><table style="font-family:Open Sans,sans-serif;" role="presentation" cellpadding="0" cellspacing="0" width="100%" border="0"><tbody><tr><td style="overflow-wrap:break-word;word-break:break-word;padding:10px;font-family:Open Sans,sans-serif;" align="left"><div style="color: #7e7e81; line-height: 150%; text-align: center; word-wrap: break-word;"><p style="font-size: 14px; line-height: 150%;"><span style="font-size: 12px; line-height: 18px;">You have received this email as a registered user of Booctep.com</span><span style="font-size: 12px; line-height: 18px;"></span></p></div></td></tr></tbody></table><!--[if (!mso)&(!IE)]><!--></div><!--<![endif]--></div></div><!--[if (mso)|(IE)]></td><![endif]--><!--[if (mso)|(IE)]></tr></table></td></tr></table><![endif]--></div></div></div><!--[if (mso)|(IE)]></td></tr></table><![endif]--></td></tr></tbody></table><!--[if mso]></div><![endif]--><!--[if IE]></div><![endif]--></body>'
    text +='</html>'
    
    subject = 'Congrats, Updated Courses!'
    msg = EmailMultiAlternatives(subject, '...', 'support@booctep.com', [to, to1])
    msg.attach_alternative(text, "text/html")
    msg.send()
    
    return render(request, 'enrollment.html',
                  {'course': course, 'similar_courses': similar_course, 'favList': favListShow,'lang': getLanguage(request)[0],
                   'alreadyinFav': alreadyinFavView, 'cartList': cartListShow, 'stu_courses': stu_courses,
                   'alreadyinCart': alreadyinCartView, 'favCnt': favCnt, 'cartCnt': cartCnt, 'msg_list': msg_list,
                   'msg_cnt': msg_cnt, 'stu_msg_list': stu_msg_list, 'stu_msg_cnt': stu_msg_cnt, 'total_msg_cnt': total_msg_cnt,
                   'cartTotalSum': cartTotalSum, 'noti_cnt': noti_cnt})

@csrf_exempt
def enrollments(request, course_ids):
    if request.session.get('user_id') == None:
        return redirect('/')
    user_id = request.session.get("user_id")
    user_type = request.session.get("user_type")

    course_ids = json.loads(course_ids)

    courses = []
    for course_id in course_ids:
        course = Courses.objects.get(pk=course_id)
        courses.append(course) 

        register_courses = student_register_courses.objects.filter(course_id_id=course_id).filter(student_id_id=user_id)
        if register_courses.count() == 0:
            time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            register_course = student_register_courses(
                course_id_id=course_id,
                student_id_id=user_id,
                last_completed_section_id=0,
                date_created=time,
                withdraw=0
            )
            register_course.save()
            
    course = Courses.objects.get(pk=course_ids[0])
    course.category = categories.objects.get(pk=course.scat_id)
    
    similar_cat = course.subcat_id
    similar_parent_cat = course.scat_id
    register_course_ids = student_register_courses.objects.filter(student_id_id=user_id).values_list('course_id_id', flat=True)
    similar_course = Courses.objects.filter(Q(subcat_id=similar_cat) | Q(scat_id=similar_parent_cat)).filter(approval_status=2).exclude(id=course.id).exclude(id__in=register_course_ids).order_by('scat_id')

    discount = Discount.objects.all()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    for i in similar_course:
        if discount.count() == 0:
            discount_percent = 1
        else:
            if now > discount[0].expire_date:
                discount_percent = 1
            else:
                not_str = discount[0].not_apply_course
                not_list = not_str.split('.')
                if str(i.id) in not_list:
                    discount_percent = 1
                else:
                    discount_percent = (100 - discount[0].discount) / 100
        i.discount_price = round(i.price * discount_percent, 2)

    for c in similar_course:
        c.link = courseUrlGenerator(c)
        rate_list = course_comments.objects.filter(course_id_id=c.id)
        c.rating = getRatingFunc(rate_list)
        c.ratingCnt = course_comments.objects.filter(course_id_id=c.id).count()
        c.stuCnt = len(rate_list)
        c.videoCnt = getVideoCnt(c)

    similar_course = sorted(similar_course, key=attrgetter('rating'), reverse=True)[:5]

    favListShow, favCnt, alreadyinFavView, cartListShow, cartCnt, alreadyinCartView, cartTotalSum, noti_list, noti_cnt, msg_list, msg_cnt, stu_msg_list, stu_msg_cnt, total_msg_cnt = findheader(
        request.user.id)
    stu_courses = student_register_courses.objects.filter(student_id_id=request.user.id)

    return render(request, 'enrollments.html',
                  {'courses': courses, 'similar_courses': similar_course, 'favList': favListShow,'lang': getLanguage(request)[0],
                   'alreadyinFav': alreadyinFavView, 'cartList': cartListShow, 'stu_courses': stu_courses,
                   'alreadyinCart': alreadyinCartView, 'favCnt': favCnt, 'cartCnt': cartCnt, 'msg_list': msg_list,
                   'msg_cnt': msg_cnt, 'stu_msg_list': stu_msg_list, 'stu_msg_cnt': stu_msg_cnt, 'total_msg_cnt': total_msg_cnt,
                   'cartTotalSum': cartTotalSum, 'noti_cnt': noti_cnt})

@csrf_exempt
def searchCourseName(request):
    key = request.POST.get('key')
    courses = Courses.objects.filter(Q(name__contains=key))[:5]
    ret = {
        'courses': serializers.serialize('json', courses)
    }
    return JsonResponse(ret)


@csrf_exempt
def saveCardInfo(request):
    user_id = request.session.get("user_id")
    id = request.POST.get('card_id')
    passport_number = request.POST.get('passport_number')
    full_name = request.POST.get('full_name')
    country = request.POST.get('country')
    address = request.POST.get('address')
    status = 1
    try:
        if id == None or id == '':
            ele = Card(
                user_id=user_id,
                passport_number=passport_number,
                full_name=full_name,
                country=country,
                address=address
            )
            ele.save()
        else:
            ele = Card.objects.get(pk=id)
            ele.passport_number = passport_number
            ele.full_name = full_name
            ele.country = country
            ele.address = address
            ele.save()
    except:
        status = 0
    ret = {
        'status': status
    }
    return JsonResponse(ret)


@csrf_exempt
def setPrivacy(request):
    user_id = request.POST.get('user_id')
    receive_email = request.POST.get('receive_email')
    if receive_email == 'true':
        receive_email = 1
    else:
        receive_email = 0
    status = 1
    try:
        user = User.objects.get(pk=user_id)
        user.receive_email = receive_email
        user.save()
    except:
        status = 0
    ret = {
        'status': status
    }
    return JsonResponse(ret)


@csrf_exempt
def deleteCourseById(request):
    id = request.POST.get('course')
    status = 1
    try:
        if Courses.objects.filter(id=id).exists():
            Courses.objects.get(pk=id).delete()
    except:
        status = 0
    ret = {
        'status': status
    }
    return JsonResponse(ret)


@csrf_exempt
def sendTransferRequest(request):
    teacher_id = request.POST.get('teacher')
    status = 1
    try:
        course_list = Courses.objects.filter(user_id=teacher_id).values_list('id', flat=True)
        course_list = map(str, course_list)
        course_list_id = ','.join(course_list)
        student_register_courses.objects.extra(where=['find_in_set(course_id_id, "' + course_list_id + '")']).filter(
            withdraw=1).update(withdraw=2)
    except:
        status = 0
    ret = {
        'status': status
    }
    return JsonResponse(ret)


@csrf_exempt
def checkPayoutStatus(request):
    teacher_id = request.POST.get('teacher')
    status = 1
    try:
        if Card.objects.filter(user_id=teacher_id).exists() == 0:
            status = 0
    except:
        status = 0
    ret = {
        'status': status
    }
    return JsonResponse(ret)

@csrf_exempt
def discount_banner(request):
    discount = Discount.objects.all()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    discount_description = ""
    discount_percent = ""
    discount_expire = ''
    if discount.count() == 0:
        status = 0
    else:
        if now > discount[0].expire_date:
            status = 0
        else:
            status = 1
            discount_description = discount[0].description
            discount_percent = discount[0].discount
            discount_expire = discount[0].expire_date
    
    ret = {
        'status': status,
        'description': discount_description,
        'discount': discount_percent,
        'expire_date': discount_expire,
        'now_date': now
    }

    return JsonResponse(ret)

#
# def handler404(request, exception):
#     return render(request, 'filter_404_page.html')
