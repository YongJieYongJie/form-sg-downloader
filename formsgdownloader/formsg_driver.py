"""This selenium module contains helper function for automation of FormSG at
https://forms.gov.sg.

Usage: Call `login()` with the relevant email address, and enter the one-time
    password when prompted. Subsequently, call the required functions such as
    `activate_form()`, passing in the required argument(s).

Data required: The `FORMS` constant contains a mapping from `form_code` to
    the relevant data from FormSG -- the `form_id` and the `secret_key`. For
    each form created on FormSG, assign that form an unique `form_code`, and
    update the mapping in `FORMS` with the `form_id` and `secret_key` from
    FormSG.

Note: Functions starting with an underscore are meant to be internal
    functions, and there should generally be no need to call such functions
    directly.

"""
import datetime as dt
import os
import time

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


FORMS = {}
IS_INIT = False

# General Actions

def login(email):

    _init()

    enter_email(email)
    otp = input('Please enter the one-time password: ')
    enter_one_time_password(otp)


def enter_email(email):

    D.get('https://form.gov.sg/#!/signin')
    _type('//*[@id="email-input"]', email)
    _click('//*[@id="sign-in"]//button[contains(text(),"Get Started")]')


def enter_one_time_password(otp):

    _type('//*[@id="otp-input"]', otp)
    _click('//*[@id="sign-in"]//button[contains(text(),"Sign In")]')
    time.sleep(1)

    _click('//div[@class="storage-modal__close"]', missing_ok=True)
    _wait_for_element_to_disappear('/html/body/div[1]/div/div/div/div[1]/div')


def download_csv(form_code):

    print(f'[-->] Downloading data from form: {form_code}... ', end='')
    _init()

    _go_to_form_admin(form_code)
    _go_to_data_tab()
    try:
        _type('//*[@id="secretKeyInput"]', FORMS[form_code]['secret_key'], set_value_directly=True)
        _click('//button[.=" Unlock Responses "]')

        # Set the date range to start from yesterday
        # _click('//*[@id="date-picker"]/input')
        # for _ in 'DD MMM YYYY':
        #     _type('//div[@class="calendar left"]//input', Keys.BACKSPACE)
        # yesterday = dt.date.today() - dt.timedelta(days=1)
        # yesterday_string = dt.datetime.strftime(yesterday, '%d %b %Y')
        # _type('//div[@class="calendar left"]//input', f'{yesterday_string}{Keys.ENTER}')

        # for _ in 'DD MMM YYYY':
        #     _type('//div[@class="calendar right"]//input', Keys.BACKSPACE)
        # today_string = dt.datetime.strftime(dt.date.today(), '%d %b %Y')
        # _type('//div[@class="calendar right"]//input', f'{today_string}{Keys.ENTER}{Keys.TAB}')

        # _type('//*[@id="date-picker"]/input', Keys.ENTER)

        _click('//*[@id="btn-export"]')
        time.sleep(1)
        _wait_for_element('//*[@id="btn-export"]/span[.="Export"]', 300) # Wait 5 minutes until download finishes, i.e., the "Export" button can be clicked again
        print('OK')

    except NoSuchElementException as e:
        # Only catch the exception if the missing element is the secret key
        #     input.
        if 'secretKeyInput' in str(e) and _is_element_visible('//*[@id="responses-tab"]//*[contains(text(),"No signs of movement")]'):
            print('No data')
        else:
            raise


def close():

    D.close()


# Helper functions

def _get_form_admin_url(form_code):

    form_id = FORMS[form_code]['form_id']
    return(f'https://form.gov.sg/#!/{form_id}/admin')


def _go_to_form_admin(form_code):

    D.get(_get_form_admin_url(form_code))
    time.sleep(0.5)
    _wait_for_element('//*[@id="edit-form"]')


def _go_to_data_tab():

    _click('//*[@id="admin-tabs-container"]/li/a[.="Data"]')
    _wait_for_element('//*[@id="results-tabs-container"]//a[.="Responses"]')
    time.sleep(0.5)


def _init(download_dir=None, binary_path=None, force=False):

    global D, IS_INIT
    if (not IS_INIT) or force:

        if not download_dir: # Default download directory
            download_dir = os.path.join(
                os.path.basename(__file__), '..', 'data', 'raw',
                dt.datetime.strftime(dt.datetime.now(), '%Y-%m-%d_%H%Mh'))

        download_dir = os.path.abspath(download_dir)
        print('[*] Ensuring that folder exists at:', download_dir)
        os.makedirs(download_dir, exist_ok=True)

        print('[*] Initializing Selenium')
        chrome_options = webdriver.ChromeOptions()
        prefs = {'download.default_directory': download_dir}
        chrome_options.add_experimental_option('prefs', prefs)
        chrome_options.add_argument('--headless --disable-gpu')
        if binary_path:
            D = webdriver.Chrome(binary_path, options=chrome_options)
        else:
            D = webdriver.Chrome(options=chrome_options)

        IS_INIT = True

    init_settings = {'download_dir': download_dir}
    return init_settings


# TagUI replacement functions (for ease of adapting TagUI code into Selenium)

def _type(element_xpath, characters, set_value_directly=False):

    elem = _wait_for_element(element_xpath, 1)
    # elem = D.find_element_by_xpath(element_xpath)
    to_clear = '[clear]' in characters

    if set_value_directly:
        if to_clear:
            characters = characters.replace('[clear]', '')
            D.execute_script('arguments[0].setAttribute("value", arguments[1])', elem, characters)
        else:
            existing_value = elem.get_attribute('value')
            D.execute_script('arguments[0].setAttribute("value", arguments[1])', elem, existing_value + characters)

    else:
        if to_clear:
            characters = characters.replace('[clear]', '')
            elem.clear()
        elem.send_keys(characters)

    D.execute_script('arguments[0].dispatchEvent(new CustomEvent("change"))', elem)


def _click(element_xpath, missing_ok=False):

    try:
        elem = D.find_element_by_xpath(element_xpath)
        D.execute_script('arguments[0].click()', elem)
    except Exception as e:
        if missing_ok:
            pass
        else:
            print(f'Error while trying to click the element "{element_xpath}". '
                  'Full error message is as below:')
            print(e)

            next_step = input('Proceed as usual? (Y/n) ').lower()
            while next_step not in ['y', 'n', '']:
                next_step = input('Proceed as usual? (Y/n)').lower()
            if next_step == 'n':
                raise


# Selenium helper functions

def _is_element_visible(element_xpath, seconds=1):

    try:
        _wait_for_element(element_xpath, seconds)
        return True
    except NoSuchElementException:
        return False


def _wait_for_element(element_xpath, seconds=10):

    try:
        elem = WebDriverWait(D, seconds).until(
            EC.visibility_of_element_located((By.XPATH, element_xpath))
        )
        return elem
    except TimeoutException:
        raise NoSuchElementException('Unable to locate element by xpath '
            f'({element_xpath}) after timeout of {seconds} seconds.')


def _wait_for_element_to_disappear(element_xpath, seconds=10):

    WebDriverWait(D, seconds).until(
        EC.invisibility_of_element_located((By.XPATH, element_xpath))
    )

# Module configuration functions

def _set_forms_details(forms):
    """
    Args:
        forms (iterable of tuple): An iterable of 3-tuples, each representing
            the form name, form ID, and form secret key.
    """
    global FORMS
    for form in forms:
        f_name, f_id, f_secret_key = form
        FORMS[f_name] = { 'secret_key': f_secret_key, 'form_id': f_id }


if __name__ == '__main__':

    email = input('Please enter your email address: ')
    init_settings = _init()
    login(email)
    print(f'[*] Data downloaded to: {init_settings["download_dir"]}')
    close()
