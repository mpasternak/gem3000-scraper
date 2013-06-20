# -*- encoding: utf-8 -*-
from datetime import datetime, timedelta

import bs4, requests, sys

CGI_BIN_LOGIN = '/cgi-bin/login'

class Sample:
    PATIENT = "P"
    QUALITY_CONTROL = "Q"
    CVP = "C"


class BadCredentials(Exception):
    pass


class Gem3000:
    def __init__(self, host):
        self.host = host
        self.session = requests.Session()

    def url(self, path):
        return "https://%s%s" % (self.host, path)

    def formPost(self, path, data):
        return self.session.post(
            self.url(path),
            data=data,
            verify=False,
            headers={
                'content-type': 'application/x-www-form-urlencoded'})

    def login(self, username="GEM", password="1234"):
        res = self.session.get(self.url(CGI_BIN_LOGIN), verify=False)
        assert("ID operatora" in res.content)
        res = self.formPost(
            CGI_BIN_LOGIN,
            dict(
                user=username,
                password=password,
                Login="Połączenie"))

        if "ny operator" in res.content:
            raise BadCredentials

    def fetch_sample_urls(self, patient_id=None):
        frm = datetime.now() - timedelta(days=1365)
        to = datetime.now()

        data = dict(
            patient_id = patient_id,

            sample_type = Sample.PATIENT,
            sample_status = 'accepted',
            submit = 'Szukaj',

            first_name = '',
            last_name = '',
            oper_id = '',

            fyear = frm.year,
            fmonth = frm.month - 1,
            fday = frm.day,
            from_hr = "00",
            from_min = "00",
            from_time = "00:00",

            tyear = to.year,
            tmonth = to.month - 1,
            tday = to.day,
            to_hr = "23",
            to_min = "59",
            to_time = "23:59")

        res = self.formPost('/cgi-bin/samplereview', data)

        soup = bs4.BeautifulSoup(res.content)

        for link in soup.find_all("a")[2:]:
            yield link['href']

    def fetch_sample(self, url):

        res = self.session.get(self.url(url), verify=False)
        soup = bs4.BeautifulSoup(res.content)

        main = soup.find_all('table', width=1050)[0]
        #import pdb; pdb.set_trace()
        ret = {}

        def byClass(_class):
            return soup.find_all(attrs={'class':_class})[0].text.strip()

        ret['patient_id'] = byClass('PatientID')
        ret['sample_id'] = url.split('=')[1].split('&')[0] + url.split('sampnum=')[1]
        ret['timestamp'] = byClass('Timestamp').replace("  ", " ")
        ret['material'] = byClass('SampleType')
        ret['operator'] = byClass('OperatorIDNo')

        for tr in main.find_all('tr'):
            td = tr.find_all('td')
            if len(td) == 4:

                key = td[0].text.strip()
                value = td[2].text.strip()
                unit = td[3].text.strip()

                ret[key] = {'value': value, 'units': unit}

        return ret

if __name__ == "__main__":
    g = Gem3000(host="192.168.3.211")
    g.login()
    try:
        id3 = sys.argv[1]
    except IndexError:
        id3 = 735039137
    for url in g.fetch_sample_urls(id3):
        data = g.fetch_sample(url)
        d, t = data['timestamp'].split(" ")

        for key in data.keys():
            if key in ['sample_id', 'patient_id', 'material', 'timestamp', 'operator']:
                continue
            values = [data['patient_id'], d, t,
                      data['sample_id'],
                      key, data[key]['value'], data[key]['units']]
            print "\t".join([value.encode('utf-8') for value in values])

