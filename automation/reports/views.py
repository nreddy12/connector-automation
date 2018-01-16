# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import csv
from datetime import datetime
import mimetypes
import os
import urllib
from wsgiref.util import FileWrapper

from django.http.response import HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import redis

from automation.settings import BASE_DIR
from reports.HTMLTestRunner import get_live_update, stop_running_test
from reports.configuration import redis_connection
from reports.shieldsquare import execute_tests, ShieldSquare
from reports.utils import custom_email


def home(request):
    return render(request, 'index.html', context=None)

@csrf_exempt
def cancel_test(request):
    live_id = request.POST.get('liveupdate', '').strip()
    stop_running_test(live_id)
    return render(request, 'live_update.html', context=None)
    
@csrf_exempt
def get_test_live_report(request):
    live_id = request.POST.get('liveupdate', '').strip()
    update = get_live_update(live_id)
    if update:
        status_str = '##'.join(str(v) for v in update)
    else:
        status_str = ''
    return render(request, 'live_update.html', {'status_str': status_str})


@csrf_exempt
def test_progress(request):
    return render(request, 'test.html', context=None)


def download_test_report(request, fileid):
    filename = 'static/downloads/csv/{}.csv'.format(fileid)
    wrapper = FileWrapper(open(filename, 'rb'))
    content_type = mimetypes.guess_type(filename)[0]
    response = HttpResponse(wrapper, content_type=content_type)
    response['Content-Length']      = os.path.getsize(filename)   
    response['Content-Disposition'] = 'attachment; filename="{}.csv"'.format(fileid)
    return response


@require_http_methods(['POST', 'GET'])
def get_report(request):
    """ """
    sid = request.POST.get('sid', '').strip()
    env = request.POST.get('env', '').strip()
    url = request.POST.get('url', '').strip()
    liveid = request.POST.get('liveupdate', '').strip()
    bq_delay = request.POST.get('bq_time', '').strip()
    
    mode = False
    if request.POST.get('mode', '') == 'on':
        mode = True

    if bq_delay:
        bq_delay = int(bq_delay)
    else:
        bq_delay = 60

    ss_config = {'sid': sid,
                'url': url,
                'mode': mode,
                'env': env,
                'liveid': liveid,
                'bq_delay': bq_delay,
                }

    #validate environment id with redis
    redis_con = redis.Redis(host=redis_connection['host'],
                            port=redis_connection['port'],
                            password=redis_connection['password'])

    if redis_con:
        r_sid = redis_con.hget('H:sidmap', env)
        if r_sid:
            if int(r_sid) == int(sid) + 1:
                return render(request, 'test_report.html',
                              {'status': False,
                               'msg': 'Sandbox ID is configured'})
        else:
            return render(request, 'test_report.html',
                          {'status': False,
                           'msg': 'Given Environment ID is invalid'})
    try:
        if urllib.urlopen(url).getcode() == 400:
            return render(request, 'test_report.html',
                          {'status': False,
                           'msg': 'URL is not working, 404 Not Found'})
    except IOError:
        return render(request, 'test_report.html',
                      {'status': False,
                       'msg': 'Socket error, Connection refused'})
    
    include_tests = None
    exclude_tests = None
    if request.POST.get('cust_toggle', '') == 'on':
        include_tests = request.POST.get('cust_test', '')
        if include_tests:
            include_tests = [ctest.strip() for ctest in include_tests.split(',')]
    else:
        exclude_tests = request.POST.get('cust_test', '')
        if exclude_tests:
            exclude_tests = [ctest.strip() for ctest in exclude_tests.split(',')]
    
    data = execute_tests(ss_config, include_tests, exclude_tests)
    # write dictionary data to .csv file
    fileid = '{}_{}'.format(sid, datetime.now().strftime("%d%m%y_%H%M"))
    filename = 'static/downloads/csv/{}.csv'.format(fileid)

    with open(filename, 'w') as csvfile:
        fieldnames = ['t_name', 'status', 'expected', 'observed', '__uzma',
                      '__uzmb', '__uzmc', '__uzmd', '_zpsbd0', '_zpsbd1',
                      '_zpsbd2', '_zpsbd3', '_zpsbd4', '_zpsbd5', '_zpsbd6',
                      '_zpsbd7', '_zpsbd8', '_zpsbd9', '_zpsbda', 'ssresp']
                       
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, restval='')
        writer.writeheader()
        liveid = ss_config['liveid']
        if liveid in ShieldSquare.csv_dict:
            for test_data in ShieldSquare.csv_dict[liveid]:
                writer.writerows(ShieldSquare.csv_dict[liveid][test_data])
            
    # revisit this code
    if ss_config['liveid'] in ShieldSquare.csv_dict:
        del ShieldSquare.csv_dict[ss_config['liveid']]

    if request.POST.get('email_chk', '') == 'on':
        to_list = request.POST.get('to', '')
        if to_list:
            to_list = [email.strip() for email in to_list.split(',')]
        cc_list = request.POST.get('cc', '')
        if cc_list:
            cc_list = [email.strip() for email in cc_list.split(',')]

        context = {'user_name': '',
                   'current_time': datetime.now().strftime('%d %b-%Y %H:%M:%S'),
                   'msg': 'message',
                   'report_attr': data['report_attrs'],
                   'config': ss_config,
                   }

        attachments = []
        attachments.append(filename)
        custom_email(label="test_report",
                     to=to_list,
                     cc=cc_list,
                     context=context,
                     attachments=attachments)

    data['status'] = True
    data['fileid'] = fileid
    return render(request, 'test_report.html', data)

