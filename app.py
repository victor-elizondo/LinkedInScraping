import os
import time
import re
import xlsxwriter
from bs4 import BeautifulSoup
from selenium import webdriver


def check_url(url):
    regex = re.compile(
        r'^(?:http|ftp)s?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return re.match(regex, url) is not None


def get_profile_data(link_linkedin_profile):
    # Setting of the delay (seconds) between operations that need to be sure loading of page is ended
    loading_pause_time = 2

    # Opening of the profile page
    browser.get(link_linkedin_profile)

    # Scraping Email Address from Contact Info (email)

    # > click on 'Contact info' link on the page
    browser.execute_script(
        "(function(){try{for(i in document.getElementsByTagName('a')){let el = document.getElementsByTagName('a')[i]; "
        "if(el.innerHTML.includes('Contact info')){el.click();}}}catch(e){}})()")
    time.sleep(loading_pause_time)

    # > gets email from the 'Contact info' popup
    email = browser.execute_script(
        "return (function(){try{for (i in document.getElementsByClassName('pv-contact-info__contact-type')){ let el = "
        "document.getElementsByClassName('pv-contact-info__contact-type')[i]; if(el.className.includes('ci-email')){ "
        "return el.children[2].children[0].innerText; } }} catch(e){return '';}})()")

    # > close the 'Contact info' popup
    browser.execute_script("document.getElementsByClassName('artdeco-modal__dismiss')[0].click()")

    # Loading of the first part of page (containing last job position)
    window_height = browser.execute_script("return window.innerHeight")

    for i in range(1, 5):
        browser.execute_script(f"window.scrollTo(0, {window_height * i});")
        time.sleep(loading_pause_time)

    # Parsing of the page html structure
    soup = BeautifulSoup(browser.page_source, 'lxml')

    # Scraping of the Name (profile_name)
    name_div = soup.find('div', {'class': 'flex-1 mr5'})
    name_loc = name_div.find_all('ul')
    profile_name = name_loc[0].find('li').get_text().strip()

    # Scraping of the Job Position
    exp_section = soup.find('section', {'id': 'experience-section'})
    exp_section = exp_section.find('ul')
    div_tags = exp_section.find('div')
    a_tags = div_tags.find('a')

    # Scraping of the Job Position - company_name, job_title
    try:
        company_name = a_tags.find_all('p')[1].get_text().strip()
        job_title = a_tags.find('h3').get_text().strip()
        spans = a_tags.find_all('span')
    except:
        company_name = a_tags.find_all('span')[1].get_text().strip()
        job_title = exp_section.find('ul').find('li').find_all('span')[2].get_text().strip()
        spans = exp_section.find('ul').find('li').find_all('span')

    # Scraping of Job Position - location
    location = ''
    next_span_is_location = False
    for span in spans:
        if next_span_is_location:
            location = span.get_text().strip()
            break
        if span.get_text().strip() == 'Location':
            next_span_is_location = True

    # Scraping of Industry
    company_url = a_tags.get('href')
    try:
        browser.get('https://www.linkedin.com'+company_url)
        industry = browser.execute_script("return document.getElementsByClassName('org-top-card-summary-info-list__info-item')[0].innerText")
    except:
        industry = 'N/A'

    # Returning of the data
    return [profile_name, email, [company_name, job_title, location, industry]]


# Loading of configurations
configurations = open('configs.txt', 'r')
username = configurations.readline()
password = configurations.readline()
driver = configurations.readline()
configurations.close()

# Building of the path to Chrome driver executable file
driver_bin = os.path.join(os.path.abspath(os.path.dirname(__file__)), driver)

# Creation of a new instance of Chrome
browser = webdriver.Chrome(executable_path=driver_bin)

# Doing login on Linkedin
browser.get('https://www.linkedin.com/uas/login')

username_input = browser.find_element_by_id('username')
username_input.send_keys(username)

password_input = browser.find_element_by_id('password')
password_input.send_keys(password)
try:
    password_input.submit()
except:
    pass

# Loading of Profiles data - see: get_profile_data()
profiles_data = []
for profile_link in open("profiles.txt", "r"):
    if profile_link == '':
        continue

    if check_url(profile_link):
        try:
            profiles_data.append(get_profile_data(profile_link))
        except:
            profiles_data.append(['', '', ['', '', '', '']])
    else:
        profiles_data.append(['BAD FORMATTED LINK', '', ['', '', '', '']])

# Closing of Chrome
browser.quit()

# Generation of XLS file with profiles data
workbook = xlsxwriter.Workbook('results.xlsx')
worksheet = workbook.add_worksheet()

headers = ['Name', 'Company', 'Job Title', 'Location', 'Industry', 'Email']
for h in range(len(headers)):
    worksheet.write(0, h, headers[h])

for i in range(len(profiles_data)):
    profile_data = profiles_data[i]
    xls_row = i + 1

    # Mapping of profile data based on previous declared headers
    worksheet.write(xls_row, 0, profile_data[0])
    worksheet.write(xls_row, 1, profile_data[2][0])
    worksheet.write(xls_row, 2, profile_data[2][1])
    worksheet.write(xls_row, 3, profile_data[2][2])
    worksheet.write(xls_row, 4, profile_data[2][3])
    worksheet.write(xls_row, 5, profile_data[1])

workbook.close()
