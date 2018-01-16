from datetime import datetime
import json
import os
import time
from unittest import suite
import unittest

import redis
from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

from automation.settings import BASE_DIR
from google.cloud import bigquery
from reports import configuration, HTMLTestRunner
from reports.utils import is_valid_ip


def execute_tests(ss_config, include_tests=None, exclude_tests=None):
    """ """
    loader = TestLoaderWithKwargs()
    suite1 = loader.loadTestsFromTestCase(ShieldSquare, ss_config, include_tests, exclude_tests)
    test_suites = unittest.TestSuite([suite1])
    runner = HTMLTestRunner.HTMLTestRunner(stream='',
                                           title='Connector Automation Testing Report',
                                           description='Acceptance Tests',
                                           live_id=ss_config['liveid'])
    return runner.run(test_suites)


class TestLoaderWithKwargs(unittest.TestLoader):
    """A test loader which allows to parse keyword arguments to the
       test case class."""
    def loadTestsFromTestCase(self, testCaseClass, kwargs, include_tests,
                              exclude_tests):
        """Return a suite of all tests cases contained in
           testCaseClass."""
        if issubclass(testCaseClass, suite.TestSuite):
            raise TypeError("Test cases should not be derived from \
                            TestSuite. Maybe you meant to derive from \
                             TestCase?")
        testCaseNames = self.getTestCaseNames(testCaseClass)
        if not testCaseNames and hasattr(testCaseClass, 'runTest'):
            testCaseNames = ['runTest']

        # Modification here: parse keyword arguments to testCaseClass.
        test_cases = []
        for test_case_name in testCaseNames:
            if exclude_tests and test_case_name in exclude_tests:
                continue

            if include_tests:
                if test_case_name in include_tests:
                    test_cases.append(testCaseClass(test_case_name, kwargs))
            else:
                test_cases.append(testCaseClass(test_case_name, kwargs))
        loaded_suite = self.suiteClass(test_cases)
        return loaded_suite


class ShieldSquare(unittest.TestCase):
    """ """
    csv_dict = dict()
    def __init__(self, testname, config):
        super(ShieldSquare, self).__init__(testname)
        self.config = config
        if config['liveid'] not in ShieldSquare.csv_dict:
            ShieldSquare.csv_dict[config['liveid']] = {}

    @classmethod
    def setUpClass(cls):
        """ """
        try:
            cls.client = bigquery.Client(project="ss-production-storage")
            cls.driver = webdriver.PhantomJS(service_args=['--ssl-protocol=any'])
            cls.driver.maximize_window()
            cls.r = redis.Redis(host=configuration.redis_connection['host'],
                                port=configuration.redis_connection['port'],
                                password=configuration.redis_connection['password'])
        except Exception as e:
            print 'exception in setup: ', e
            raise unittest.SkipTest("Exception occured in setUpClass")
            

    @classmethod
    def tearDownClass(cls):
        """ """
        if cls.driver:
            cls.driver.quit()

    def hit_and_get_uzma(self, hits=1):
        """ Deleting shieldsquare one cookie will reset cookies and send
        new cookie values""" 
        self.driver.delete_cookie('__uzma')
        
        if hits > 1:
            for i in range(hits):
                self.driver.get(self.config['url'])
                time.sleep(10)
        else:
            self.driver.get(self.config['url'])
        
        cookies = self.driver.get_cookies()
        uzma_value = ''
        for cookie in cookies:
            if cookie['name'] == '__uzma':
                uzma_value = cookie['value']
                break
        self.assertNotEqual(uzma_value, '', '__uzma is empty from browser')
        return uzma_value

    def query_bigquery(self, uzma_value, query, time_delay=60):
        """ Query bigQuery and get the result with selected query """
        if time_delay != 60 and self.config['bq_delay'] > time_delay:
            time_delay = self.config['bq_delay']
            
        time.sleep(time_delay)
        utc_time = datetime.utcnow().strftime("%d%m%y_%H")
        table_name = self.config['sid'] + "_" + utc_time
        if query == '*':
            query = '''SELECT apidata._zpsbd0,apidata._zpsbd1,apidata._zpsbd2,
                    apidata._zpsbd3,apidata._zpsbd4,apidata._zpsbd5,
                    apidata._zpsbd6,apidata._zpsbd7,apidata._zpsbd8,
                    apidata._zpsbd9,apidata._zpsbda, apidata.__uzma, 
                    apidata.__uzmb, apidata.__uzmc,apidata.__uzmd, apidata.ssresp'''

        where_clasue = ' where apidata.__uzma = "' + uzma_value + '";'
        query = query + ' FROM Citadel_Stream.' + table_name + where_clasue 
                
        result = self.client.run_sync_query(query)
        result.use_legacy_sql = False
        result.run()
        self.assertGreaterEqual(len(result.rows), 1, 
                                "0 results found from BiqQuery")
        return result

    def is_production_sid(self, zpsbd1):
        """ """
        if zpsbd1:
            sid = self.r.hget('H:sidmap', zpsbd1)
            if self.config['sid'] == sid:
                return True
        return False

    def prepare_csv(self, t_name, testdata=None, state=False):
        if testdata:
            try:
                liveid = self.config['liveid']
                ShieldSquare.csv_dict[liveid][t_name] = testdata
            except Exception as e:
                print 'Exception in prepare_csv: {}'.format(e)

    def prepare_testdict(self, testdict, row):
        keys = ('_zpsbd0', '_zpsbd1', '_zpsbd2', '_zpsbd3', '_zpsbd4', '_zpsbd5',
                '_zpsbd6', '_zpsbd7', '_zpsbd8', '_zpsbd9', '_zpsbda', '__uzma',
                '__uzmb', '__uzmc', '__uzmd', 'ssresp')
        return dict(zip(keys, row))
    
    def set_status_pass(self, t_name):
        try:
            liveid = self.config['liveid']
            if ShieldSquare.csv_dict[liveid]:
                for test in ShieldSquare.csv_dict[liveid][t_name]:
                    test['status'] = 'Pass'
        except KeyError:
            pass    
     
    def test_PI_00001(self):
        """If mode is 'Active' set _zpsbd0 to true, else false"""
        uzma_value = self.hit_and_get_uzma()
        result = self.query_bigquery(uzma_value, '*')
        m_datasets = []
        first_test = True
        for row in result.rows:
            testdata = dict()
            testdata.update(self.prepare_testdict(testdata, row))
            if first_test:
                testdata['t_name'] = self._testMethodName
                first_test = False
            testdata['status'] = 'Pass' if (True if self.config['mode'] else False) == row[0] else 'Fail'
            testdata['observed'] = row[0]
            testdata['expected'] = row[0]
            m_datasets.append(testdata)
            self.prepare_csv(self._testMethodName, m_datasets)
            self.assertEqual(True if self.config['mode'] else False, row[0],
                             'Expected: {}, Observed: {}'.format(True if self.config['mode'] else False,row[0]))
        print "Mode: [{}] configured".format(self.config['mode'])

    def test_PI_00002(self):
        """Set _zpsbd1 with environment ID (Sandbox/Production)"""
        uzma_value = self.hit_and_get_uzma()
        result = self.query_bigquery(uzma_value, '*')
        m_datasets = []
        first_test = True    
        for row in result.rows:
            testdata = dict()
            testdata.update(self.prepare_testdict(testdata, row))
            if first_test:
                testdata['t_name'] = self._testMethodName
                first_test = False
            testdata['status'] = 'Pass' if self.config['env'] == row[1] else 'Fail'
            testdata['expected'] = self.config['env']
            testdata['observed'] = row[1]
            m_datasets.append(testdata)
            self.prepare_csv(self._testMethodName, m_datasets)
            self.assertEqual(self.config['env'], row[1],
                             'Expected: {}, Observed: {}'.format(self.config['env'],
                                                                 row[1]))
         
    def test_PI_00003(self):
        """Environment ID 4th part should be equal to PID 2nd part"""
        uzma_value = self.hit_and_get_uzma()
        result = self.query_bigquery(uzma_value, '*')
        m_datasets = []
        first_test = True
        for row in result.rows:
            testdata = dict()
            testdata.update(self.prepare_testdict(testdata, row))
            if first_test:
                testdata['t_name'] = self._testMethodName
                first_test = False
            testdata['status'] = 'Fail'
            testdata['expected'] = row[1].split('-')[3]
            testdata['observed'] = row[2].split('-')[1]
            m_datasets.append(testdata)
            self.prepare_csv(self._testMethodName, m_datasets)
            self.assertEqual(testdata['expected'], testdata['observed'],
                             'Expected: {}, Observed: {}'.format(testdata['expected'],
                                                                 testdata['observed']))
        self.set_status_pass(self._testMethodName) #revisit
                              
    def test_PI_00004(self):
        """PID(_zpsbd2) value should be different for every request"""
        uzma_value = self.hit_and_get_uzma(10)
        result = self.query_bigquery(uzma_value, '*')
        m_datasets = []
        zpsbd2_list = []
        first_test = True
        for row in result.rows:
            testdata = dict()
            testdata.update(self.prepare_testdict(testdata, row))
            if first_test:
                testdata['t_name'] = self._testMethodName
                first_test = False
            testdata['expected'] = False
            testdata['observed'] = row[2] in zpsbd2_list
            testdata['status'] = 'Pass' if testdata['observed'] == False else 'Fail'
            m_datasets.append(testdata)
            self.prepare_csv(self._testMethodName, m_datasets)
            self.assertEqual(False, testdata['observed'],
                             '{} is not unique: {}'.format(row[2], zpsbd2_list))
            zpsbd2_list.append(row[2])
        print "Unique PIDs: {}".format(zpsbd2_list)
 
    def test_PI_00005(self):
        """Verify _zpsbd6 is having a valid IP address"""
        uzma_value = self.hit_and_get_uzma()
        result = self.query_bigquery(uzma_value, '*')
        m_datasets = []
        first_test = True       
        for row in result.rows:
            testdata = dict()
            testdata.update(self.prepare_testdict(testdata, row))
            if first_test:
                testdata['t_name'] = self._testMethodName
                first_test = False
            testdata['status'] = 'Pass' if row[6] else 'Fail'
            testdata['expected'] = 'Not Empty'
            testdata['observed'] = row[6]
            m_datasets.append(testdata)
            self.prepare_csv(self._testMethodName, m_datasets)
            self.assertNotEqual(isinstance(row[6], (list, tuple)), True,
                                "_zpsbd6 is having multiple IPs: [{}]".format(row[6]))
 
            is_valid = is_valid_ip(row[6])
            self.assertEqual(is_valid, True, "zpsbd6 is not valid IP address: [{}]".format(row[6]))
            print '_zpsbd6', row[6]
            
        self.set_status_pass(self._testMethodName) #revisit
 
    def test_PI_00006(self):
        """Verify __uzma cookie value will be same for successive requests and 
        generate new __uzma if cookie is deleted"""
        m_datasets = []
        first_test = True
        self.driver.delete_cookie('__uzma')
        time.sleep(10)
        self.driver.get(self.config['url'])
        
        cookies = self.driver.get_cookies()
        b_uzma = b_uzmb = b_uzmc = b_uzmd = ''
        for cookie in cookies:
            if cookie['name'] == '__uzma':
                b_uzma = cookie['value']
            elif cookie['name'] == '__uzmb':
                b_uzmb = cookie['value']
            elif cookie['name'] == '__uzmc':
                b_uzmc = cookie['value']
            elif cookie['name'] == '__uzmd':
                b_uzmd = cookie['value']
        
            if b_uzma != '' and b_uzmb != '' and b_uzmc != '' and b_uzmd != '':
                break
        
        self.driver.delete_cookie('__uzma')
        time.sleep(60)
        self.driver.get(self.config['url'])
        after_cookies = self.driver.get_cookies()
        a_uzma = a_uzmb = a_uzmc = a_uzmd = ''

        for cookie in after_cookies:
            if cookie['name'] == '__uzma':
                a_uzma = cookie['value']
            elif cookie['name'] == '__uzmb':
                a_uzmb = cookie['value']
            elif cookie['name'] == '__uzmc':
                a_uzmc = cookie['value']
            elif cookie['name'] == '__uzmd':
                a_uzmd = cookie['value']
        
            if a_uzma != '' and a_uzmb != '' and a_uzmc != '' and a_uzmd != '':
                break  
        testdata = dict()
        if first_test:
            testdata['t_name'] = self._testMethodName
            first_test = False                
        testdata['__uzma'] = '{}, {}'.format(b_uzma, a_uzma)
        testdata['__uzmb'] = '{}, {}'.format(b_uzmb, a_uzmb)
        testdata['__uzmc'] = '{}, {}'.format(b_uzmc, a_uzmc)
        testdata['__uzmd'] = '{}, {}'.format(b_uzmd, a_uzmd)
        testdata['expected'] = '__uzma non empty and unique'
        testdata['observed'] = '{}, {}'.format(b_uzma, a_uzma)
        testdata['status'] = 'Pass' if b_uzma != a_uzma else 'Fail'
        m_datasets.append(testdata)
        self.prepare_csv(self._testMethodName, m_datasets)
        self.assertNotEqual(b_uzma, a_uzma,
                         '__uzma is same before|after delete')
        
    def test_PI_00007(self):
        """Verify current timestamp is set to __uzmb cookie when cookie is 
        deleted and will be same for every successive requests"""
        m_datasets = []
        first_test = True
        self.driver.delete_cookie('__uzmb')
        time.sleep(10)
        self.driver.get(self.config['url'])
        cookies = self.driver.get_cookies()
        b_uzma = b_uzmb = b_uzmc = b_uzmd = ''
        for cookie in cookies:
            if cookie['name'] == '__uzma':
                b_uzma = cookie['value']
            elif cookie['name'] == '__uzmb':
                b_uzmb = cookie['value']
            elif cookie['name'] == '__uzmc':
                b_uzmc = cookie['value']
            elif cookie['name'] == '__uzmd':
                b_uzmd = cookie['value']
        
            if b_uzma != '' and b_uzmb != '' and b_uzmc != '' and b_uzmd != '':
                break
        
        self.driver.delete_cookie('__uzmb')
        time.sleep(60)
        self.driver.get(self.config['url'])
        after_cookies = self.driver.get_cookies()
        a_uzma = a_uzmb = a_uzmc = a_uzmd = ''
        for cookie in after_cookies:
            if cookie['name'] == '__uzma':
                a_uzma = cookie['value']
            elif cookie['name'] == '__uzmb':
                a_uzmb = cookie['value']
            elif cookie['name'] == '__uzmc':
                a_uzmc = cookie['value']
            elif cookie['name'] == '__uzmd':
                a_uzmd = cookie['value']
        
            if a_uzma != '' and a_uzmb != '' and a_uzmc != '' and a_uzmd != '':
                break  
        testdata = dict()
        if first_test:
            testdata['t_name'] = self._testMethodName
            first_test = False                
        testdata['__uzma'] = '{}, {}'.format(b_uzma, a_uzma)
        testdata['__uzmb'] = '{}, {}'.format(b_uzmb, a_uzmb)
        testdata['__uzmc'] = '{}, {}'.format(b_uzmc, a_uzmc)
        testdata['__uzmd'] = '{}, {}'.format(b_uzmd, a_uzmd)
        testdata['expected'] = '__uzmb non empty and unique'
        testdata['observed'] = '{}, {}'.format(b_uzmb, a_uzmb)
        testdata['status'] = 'Pass' if b_uzmb != a_uzmb else 'Fail'
        m_datasets.append(testdata)
        self.prepare_csv(self._testMethodName, m_datasets)  
        self.assertNotEqual(b_uzmb, a_uzmb,
                         '__uzmb is same before|after delete')

    def test_PI_00008(self):
        """Verify current timestamp is set to __uzmd cookie for every request 
        and generate new __uzmd value if cookie is deleted"""
        m_datasets = []
        first_test = True
        self.driver.delete_cookie('__uzmd')
        time.sleep(10)
        self.driver.get(self.config['url'])
        cookies = self.driver.get_cookies()
        b_uzma = b_uzmb = b_uzmc = b_uzmd = ''
        for cookie in cookies:
            if cookie['name'] == '__uzma':
                b_uzma = cookie['value']
            elif cookie['name'] == '__uzmb':
                b_uzmb = cookie['value']
            elif cookie['name'] == '__uzmc':
                b_uzmc = cookie['value']
            elif cookie['name'] == '__uzmd':
                b_uzmd = cookie['value']
        
            if b_uzma != '' and b_uzmb != '' and b_uzmc != '' and b_uzmd != '':
                break
        
        self.driver.delete_cookie('__uzmd')
        time.sleep(60)
        self.driver.get(self.config['url'])
        after_cookies = self.driver.get_cookies()
        a_uzma = a_uzmb = a_uzmc = a_uzmd = ''
        for cookie in after_cookies:
            if cookie['name'] == '__uzma':
                a_uzma = cookie['value']
            elif cookie['name'] == '__uzmb':
                a_uzmb = cookie['value']
            elif cookie['name'] == '__uzmc':
                a_uzmc = cookie['value']
            elif cookie['name'] == '__uzmd':
                a_uzmd = cookie['value']
        
            if a_uzma != '' and a_uzmb != '' and a_uzmc != '' and a_uzmd != '':
                break  
        testdata = dict()
        if first_test:
            testdata['t_name'] = self._testMethodName
            first_test = False                
        testdata['__uzma'] = '{}, {}'.format(b_uzma, a_uzma)
        testdata['__uzmb'] = '{}, {}'.format(b_uzmb, a_uzmb)
        testdata['__uzmc'] = '{}, {}'.format(b_uzmc, a_uzmc)
        testdata['__uzmd'] = '{}, {}'.format(b_uzmd, a_uzmd)
        testdata['expected'] = '__uzmd non empty and different'
        testdata['observed'] = '{}, {}'.format(b_uzmd, a_uzmd)
        testdata['status'] = 'Pass' if b_uzmd != a_uzmd else 'Fail'
        m_datasets.append(testdata)
        self.prepare_csv(self._testMethodName, m_datasets)
        self.assertNotEqual(b_uzmd, a_uzmd,
                         '__uzmd is same before|after delete')

    def test_PI_00009(self):
        """Increment __uzmc counter value by 3 for every request and generate 
        new __uzmc(xxxxx10xxxxx) value if cookie is deleted"""
        m_datasets = []
        first_test = True
        self.driver.delete_cookie('__uzmd')
#         counter = 10
        for i in range(5):
            self.driver.get(self.config['url'])
            cookies = self.driver.get_cookies()
            b_uzma = b_uzmb = b_uzmc = b_uzmd = ''
            counter = (7+3*(i+1))
            for cookie in cookies:
                if cookie['name'] == '__uzma':
                    b_uzma = cookie['value']
                elif cookie['name'] == '__uzmb':
                    b_uzmb = cookie['value']
                elif cookie['name'] == '__uzmc':
                    b_uzmc = cookie['value']
                elif cookie['name'] == '__uzmd':
                    b_uzmd = cookie['value']
            
                if b_uzma and b_uzmb and b_uzmc and b_uzmd:
                    testdata = dict()
                    if first_test:
                        testdata['t_name'] = self._testMethodName
                        first_test = False
                    req_counter = int(b_uzmc[5:-5])
                    testdata['__uzma'] = b_uzma
                    testdata['__uzmb'] = b_uzmb
                    testdata['__uzmc'] = b_uzmc
                    testdata['__uzmd'] = b_uzmd
                    testdata['expected'] = counter
                    testdata['observed'] = int(b_uzmc[5:-5])
                    testdata['status'] = 'Pass' if req_counter == counter else 'Fail'
                    m_datasets.append(testdata)
                    self.prepare_csv(self._testMethodName, m_datasets)
                    self.assertEqual(req_counter, counter,
                                     '__uzmc counter is incorrect')
                    break
        
        self.driver.delete_cookie('__uzmc')
        time.sleep(60)
        self.driver.get(self.config['url'])
        after_cookies = self.driver.get_cookies()
        a_uzma = a_uzmb = a_uzmc = a_uzmd = ''
        for cookie in after_cookies:
            if cookie['name'] == '__uzma':
                a_uzma = cookie['value']
            elif cookie['name'] == '__uzmb':
                a_uzmb = cookie['value']
            elif cookie['name'] == '__uzmc':
                a_uzmc = cookie['value']
            elif cookie['name'] == '__uzmd':
                a_uzmd = cookie['value']
        
            if a_uzma != '' and a_uzmb != '' and a_uzmc != '' and a_uzmd != '':
                break 
 
        testdata = dict()
        if first_test:
            testdata['t_name'] = self._testMethodName
            first_test = False

        req_counter = int(a_uzmc[5:-5])                
        testdata['__uzma'] = a_uzma
        testdata['__uzmb'] = a_uzmb
        testdata['__uzmc'] = a_uzmc
        testdata['__uzmd'] = a_uzmd
        testdata['expected'] = 10
        testdata['observed'] = req_counter
        testdata['status'] = 'Pass' if req_counter == 10 else 'Fail'
        m_datasets.append(testdata)
        self.prepare_csv(self._testMethodName, m_datasets)
        self.assertEqual(req_counter, 10,
                         '__uzmc is not reset if cookie is deleted')
        
    def test_PI_00010(self):
        """Hit single request from browser and verify no. of API calls 
        received in BigQuery"""
        uzma_value = self.hit_and_get_uzma()
        result = self.query_bigquery(uzma_value, '*')
        m_datasets = []
        count = 0
        first_test = True     
        for row in result.rows:
            testdata = dict()
            testdata.update(self.prepare_testdict(testdata, row))
            if first_test:
                testdata['t_name'] = self._testMethodName
                first_test = False
            testdata['status'] = 'Pass'
            testdata['observed'] = 1
            testdata['expected'] = 1
            m_datasets.append(testdata)
            count += 1
        self.prepare_csv(self._testMethodName, m_datasets)
        self.assertNotEqual(count, 0,
                            "API packets are not reached to Big Query in 1 min or request time out happens")
        if count > 1:
            print 'One browser hit receives more than one packet'
 
    def test_PI_00011(self):
        """Verify session value is same across the website"""
        uzma_value = self.hit_and_get_uzma(10)
        result = self.query_bigquery(uzma_value, '*')
        m_datasets = []
        session_value = ''
        first_test = True
        for row in result.rows:
            testdata = dict()
            testdata.update(self.prepare_testdict(testdata, row))
            if first_test:
                testdata['t_name'] = self._testMethodName
                first_test = False
            testdata['status'] = 'Pass' if row[5] == session_value else 'Fail'
            testdata['observed'] = row[5]
            testdata['expected'] = 'Not empty'
            m_datasets.append(testdata)
            self.prepare_csv(self._testMethodName, m_datasets)
            if session_value != '':
                self.assertEqual(session_value, row[5],
                                 "Session is not unique across the site")
            else:
                session_value = row[5]
        self.assertNotEqual(session_value, '', 'Session is empty for 10 hits')
 
    def test_PI_00012(self):
        """Verify call type"""
        calltype = {1: 'page load',
                    2: 'form submit',
                    4: 'show captcha/block',
                    5: 'resolve captcha',
                    6: 'mobile traffic',
                    }
        uzma_value = self.hit_and_get_uzma(1)
        result = self.query_bigquery(uzma_value, '*')
        m_datasets = []
        first_test = True
        for row in result.rows:
            testdata = dict()
            testdata.update(self.prepare_testdict(testdata, row))
            if first_test:
                testdata['t_name'] = self._testMethodName
                first_test = False
            testdata['status'] = 'Pass' if row[8] in calltype.keys() else 'Fail'
            testdata['observed'] = row[8]
            testdata['expected'] = 'in {}'.format(calltype.keys())
            m_datasets.append(testdata)
            self.prepare_csv(self._testMethodName, m_datasets)
            self.assertEqual(row[8] in calltype.keys(), True,
                            "call type: {} is not in {}".format(row[8], calltype.keys()))
 
    def test_PI_00013(self):
        """Verify requests timeout"""
        uzma_value = self.hit_and_get_uzma(10)
        result = self.query_bigquery(uzma_value, '*')
        count = 0
        m_datasets = []
        first_test = True
        
        for row in result.rows:
            testdata = dict()
            testdata.update(self.prepare_testdict(testdata, row))
            if first_test:
                testdata['t_name'] = self._testMethodName
                first_test = False
            testdata['status'] = 'Pass'
            testdata['observed'] = 1
            testdata['expected'] = '>= 1'
            m_datasets.append(testdata)
            count += 1
        self.prepare_csv(self._testMethodName, m_datasets)
        self.assertGreaterEqual(count, 10,
                                "hits:[10], received packets:[{}]".format(count))
 
    def test_PI_00014(self):
        """Verify connector got response code 2 and show the CAPTCHA page"""
        dcap = dict(DesiredCapabilities.PHANTOMJS)
        dcap["phantomjs.page.settings.userAgent"] = 'curl'
        driver = webdriver.PhantomJS(desired_capabilities=dcap)
        print 'driver: ', driver.__dict__
        print 'type: ', type(driver)
        driver.delete_cookie('__uzma')
        time.sleep(5)
        driver.get(self.config['url'])
        cookies = driver.get_cookies()
        for cookie in cookies:
            if cookie['name'] == '__uzma':
                uzma_value = cookie['value']
                break
        
        driver.get(self.config['url'])
        result = self.query_bigquery(uzma_value, '*')
        calltype1 = calltype4 = ssresp = 0
        m_datasets = []
        first_test = True
        for row in result.rows:
            testdata = dict()
            testdata.update(self.prepare_testdict(testdata, row))
            if first_test:
                testdata['t_name'] = self._testMethodName
                first_test = False
            testdata['status'] = 'Pass' if row[15] == '2' else 'Fail'
            testdata['observed'] = row[15]
            testdata['expected'] = 'ssresp-2'
            m_datasets.append(testdata)
            self.assertEqual(row[0], True, "Monitor mode is configured")

            if row[8] == 1:
                calltype1 += 1
            elif row[8] == 4:
                calltype4 += 1
            if row[15] == '2':
                ssresp += 1
        self.prepare_csv(self._testMethodName, m_datasets)
        self.assertGreaterEqual(ssresp, 1, "Captcha response is not received")
        self.assertGreaterEqual(calltype4, 1, "Captcha page was not shown")
        self.assertGreaterEqual(calltype1, 1, "Requests are not reached to CFM")
 
    def test_PI_00015(self):
        """Verify connector got response code 3 and show the block page"""
        dcap = dict(DesiredCapabilities.PHANTOMJS)
        dcap["phantomjs.page.settings.userAgent"] = 'curl'
        driver = webdriver.PhantomJS(desired_capabilities=dcap)
        driver.delete_cookie('__uzma')
        time.sleep(5)
        driver.get(self.config['url'])
        cookies = driver.get_cookies()
        uzma_value = ''
        for cookie in cookies:
            if cookie['name'] == '__uzma':
                uzma_value = cookie['value']
                break
        
        driver.get(self.config['url'])
        result = self.query_bigquery(uzma_value, '*')
        calltype1 = calltype4 = ssresp = 0
        m_datasets = []
        first_test = True
        for row in result.rows:
            testdata = dict()
            testdata.update(self.prepare_testdict(testdata, row))
            if first_test:
                testdata['t_name'] = self._testMethodName
                first_test = False
            testdata['status'] = 'Pass' if row[15] == '3' else 'Fail'
            testdata['observed'] = row[15]
            testdata['expected'] = 'ssresp-3'
            m_datasets.append(testdata)
            self.assertEqual(row[0], True, "Monitor mode is configured")

            if row[8] == 1:
                calltype1 += 1
            elif row[8] == 4:
                calltype4 += 1
            if row[15] == '3':
                ssresp += 1
            
        self.prepare_csv(self._testMethodName, m_datasets)
        self.assertGreaterEqual(ssresp, 1, "BLOCK response is not received")
        self.assertGreaterEqual(calltype4, 1, "BLOCK page is not shown")
        self.assertGreaterEqual(calltype1, 1, "Requests are not reached to BigQuery")
 
    def test_PI_00016(self):
        """Verify connector got integrated across the customer website and 
        cookies are getting set properly"""
        json_file = 'static/downloads/json/' + self.config['sid'] + "_" + datetime.utcnow().strftime("%d%m%y_%H%M") + ".json"
        os.chdir(BASE_DIR)
        os.system("scrapy crawl drudge -a domains=" + self.config['url'] + " -o " + json_file + " -t json")
        time.sleep(120)
        with open(json_file) as json_data:
            data = json.load(json_data)
       
        integrated_urls = []
        non_integrated_url = []
        print "Total tested URLs: {}".format(len(data))
        m_datasets = []
        first_test = True
        for item in data:
            site_url = item['details']
            self.driver.delete_cookie('__uzma')
            time.sleep(5)
            self.driver.get(site_url)
            cookies = self.driver.get_cookies()
            uzma = uzmb = uzmc = uzmd = ''
            integrated = False
            testdata = dict()
            for cookie in cookies:
                if not uzma and cookie['name'] == '__uzma':
                    uzma = cookie['value']
                if not uzmb and cookie['name'] == '__uzmb':
                    uzmb = int(cookie['value'])
                if not uzmc and cookie['name'] == '__uzmc':
                    uzmc = int((cookie['value'])[5:-5])
                if not uzmd and cookie['name'] == '__uzmd':
                    uzmd = int(cookie['value'])
                    
                if uzma and uzmb and uzmc and uzmd:
                    testdata['__uzma'] = uzma
                    testdata['__uzmb'] = uzmb
                    testdata['__uzmc'] = uzmc
                    testdata['__uzmd'] = uzmd
                    integrated = True
                    break
    
            if first_test:
                testdata['t_name'] = self._testMethodName
                first_test = False
    
            testdata['status'] = 'Pass' if integrated else 'Fail'
            testdata['observed'] = site_url
            testdata['expected'] = 'integration'
            m_datasets.append(testdata) 
    
            if integrated:
                integrated_urls.append(site_url)
            else:
                non_integrated_url.append(site_url)
   
        self.prepare_csv(self._testMethodName, m_datasets)
        self.assertEqual(len(data), len(integrated_urls),
                         'Integrated URLs: {}, Non integrated URLs: {}'.format(integrated_urls, non_integrated_url))
