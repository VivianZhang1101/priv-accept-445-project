#!/usr/bin/env python3

from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchFrameException
import argparse
from urllib.parse import urlparse
from datetime import datetime
from selenium import webdriver
import traceback
import os
import sys
import json
import time
import re

# Parse Vars
parser = argparse.ArgumentParser()
parser.add_argument('--url', type=str, default='https://www.theguardian.com/')
parser.add_argument('--outfile', type=str, default='output.json')
parser.add_argument('--accept_words', type=str, default="accept_words.txt")
parser.add_argument('--chrome_driver', type=str, default="./chromedriver")
parser.add_argument('--screenshot_dir', type=str, default=None)
parser.add_argument('--lang', type=str, default=None)
parser.add_argument('--timeout', type=int, default=5)
parser.add_argument('--clear_cache', action='store_true')
parser.add_argument('--headless', action='store_true')
parser.add_argument('--docker', action='store_true')
parser.add_argument('--try_scroll', action='store_true')
parser.add_argument('--full_net_log', action='store_true')
parser.add_argument('--pre_visit', action='store_true')
globals().update(vars(parser.parse_args()))

log_entries = []
GLOBAL_SELECTOR = "a, button, div, span, form, p"
stats = {}


def main():
    global driver
    global url

    # Fix Url
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "http://" + url

    # Enable browser logging and start driver
    log("Starting Driver")
    d = DesiredCapabilities.CHROME
    # d['loggingPrefs'] = { 'performance':'ALL' }
    d['goog:loggingPrefs'] = {'performance': 'ALL'}
    options = Options()
    stats["lang"] = "default"
    stats["headless"] = False
    if lang is not None:
        stats["lang"] = lang
        options.add_experimental_option('prefs', {'intl.accept_languages': lang})
    if headless:
        options.headless = True
        options.add_argument("window-size=1920,1080")
        stats["headless"] = True
    if docker:
        options.add_argument("no-sandbox")
        options.add_argument("disable-dev-shm-usage")

    driver = webdriver.Chrome(executable_path=chrome_driver, desired_capabilities=d, options=options)
    time.sleep(timeout)

    #  Go to the page, first visit
    stats["pre-visit"] = False
    if pre_visit:
        stats["pre-visit"] = True
        log("Making Pre-First Visit")
        driver.get(url)
        time.sleep(timeout)
        
    log("Making First Visit to: {}".format(url))
    stats["target"] = url
    stats["start-time"] = time.time()

    start_time=time.time()
    driver.get(url)
    end_time=time.time()
    log("First Visit Selenium time [s]: {}".format(end_time-start_time))
    stats["first-visit-selenium-time"] = end_time-start_time
    log("Landed to: {}".format(driver.current_url))
    stats["first-visit-landing-page"] = driver.current_url
    time.sleep(timeout)
    stats["first-visit-timings"] = driver.execute_script("var performance = window.performance || {}; var timings = performance.timing || {}; return timings;")
    before_data = get_data(driver)
    make_screenshot("{}/all-first.png".format(screenshot_dir))

    # Click Banner
    log("Searching Banner")
    banner_data = click_banner(driver)

    if not "clicked_element" in banner_data:
        iframe_contents = driver.find_elements_by_css_selector("iframe")
        for content in iframe_contents:
            log("Switching to frame: {}".format(content.id) )
            try:
                driver.switch_to.frame(content)
                banner_data = click_banner(driver)
                driver.switch_to.default_content()
                if "clicked_element" in banner_data:
                    break
            except NoSuchFrameException:
                driver.switch_to.default_content()
                log("Error in switching to frame")
                
    stats["has-scrolled"] = False
    if not "clicked_element" in banner_data and try_scroll:
        log("Trying with scroll")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
        stats["has-scrolled"] = True
    stats["has-found-banner"] = "clicked_element" in banner_data
    time.sleep(timeout)
    click_data = get_data(driver)
    make_screenshot("{}/all-click.png".format(screenshot_dir))
    log("URL after click: {}".format(driver.current_url))
    stats["after-click-landing-page"] = driver.current_url

    #  Go to the page, second visit
    log("Making the Second Visit")
    stats["has-cleared-cache"] = False
    if clear_cache:
        clear_status()
        stats["has-cleared-cache"] = True
    # Clean last page
    driver.get("about:blank")
    _ = get_data(driver)
    if pre_visit:
        driver.get(url)

    start_time=time.time()
    driver.get(url)
    end_time=time.time()
    log("Second Visit Selenium time [s]: {}".format(end_time-start_time))
    stats["second-visit-selenium-time"] = end_time-start_time
    time.sleep(timeout)
    stats["second-visit-timings"] = driver.execute_script("var performance = window.performance || {}; var timings = performance.timing || {}; return timings;")
    after_data = get_data(driver)
    make_screenshot("{}/all-second.png".format(screenshot_dir))

    # Save
    data = {"first": before_data, "click": click_data, "second": after_data, "banner_data": banner_data,
            "log": log_entries, "stats": stats}
    json.dump(data, open(outfile, "w"), indent=4)

    # Quit
    driver.quit()
    log("All Done")


def clear_status():
    driver.execute_cdp_cmd('Network.clearBrowserCache', {})
    if not headless:
        driver.get("chrome://net-internals/#sockets")
        driver.find_element_by_id("sockets-view-flush-button").click()
        driver.get("chrome://net-internals/#dns")
        driver.find_element_by_id("dns-view-clear-cache").click()
    else:
        log("Warning: cannot clean DNS and socket cache in headless mode.")


def get_data(driver):

    #data = {"urls": [],"cookies": driver.get_cookies()}  # Worse than next line
    if full_net_log:
        data = { "requests": [], "responses": [], "responses-extra": [],
                "cookies": driver.execute_cdp_cmd('Network.getAllCookies', {})}
    else:
        data = { "urls": [],
                "cookies": driver.execute_cdp_cmd('Network.getAllCookies', {})}

    log = driver.get_log('performance')

    for entry in log:
        message = json.loads(entry["message"])
        if full_net_log:
            if message["message"]["method"] == "Network.responseReceived":
                data["responses"].append(message["message"]["params"])
            elif message["message"]["method"] == "Network.responseReceivedExtraInfo":
                data["responses-extra"].append(message["message"]["params"])
            elif message["message"]["method"] == "Network.requestWillBeSent":
                data["requests"].append(message["message"]["params"])
        else:
            if message["message"]["method"] == "Network.responseReceived":
                url = message["message"]["params"]["response"]["url"]
                data["urls"].append(url)

    return data


def make_screenshot(path):
    if screenshot_dir is not None:
        if not os.path.exists(screenshot_dir):
            os.makedirs(screenshot_dir)
        try:
            driver.save_screenshot(path)
        except Exception as e:
            log("Exception in making screenshot: {}".format(e))


def click_banner(driver):

    accept_words_list = set()
    for w in open(accept_words, "r").read().splitlines():
        if not w.startswith("#") and not w == "":
            accept_words_list.add(w)

    banner_data = {"matched_containers": [], "candidate_elements": []}
    contents = driver.find_elements_by_css_selector(GLOBAL_SELECTOR)

    candidate = None


    for c in contents:
        try:
            if c.text.lower().strip(" ✓›!\n") in accept_words_list:
                candidate = c
                banner_data["candidate_elements"].append({"id": c.id,
                                                          "tag_name": c.tag_name,
                                                          "text": c.text,
                                                          "size": c.size,
                                                          })
                break
        except:
            log("Exception in processing element: {}".format (c.id) )
            
    # Click the candidate
    if candidate is not None:
        try: # in some pages element is not clickable


            if screenshot_dir is not None:
                if not os.path.exists(screenshot_dir):
                    os.makedirs(screenshot_dir)
                try:
                    candidate.screenshot("{}/clicked_element.png".format(screenshot_dir))
                except Exception as e:
                    log("Exception in making screenshot: {}".format(e))

            candidate.click()
            banner_data["clicked_element"] = candidate.id
            log("Clicked: {}".format (candidate.id) )
        except:
            log("Exception in candidate click")
    else:
        log("Warning, no matching candidate")

    return banner_data


def match_domains(domain, match):
    labels_domains = domain.strip(".").split(".")
    labels_match = match.strip(".").split(".")
    return labels_match == labels_domains[-len(labels_match):]


def log(str):
    print(datetime.now().strftime("[%Y-%m-%d %H:%M:%S]"), str)
    log_entries.append((datetime.now().strftime("%Y-%m-%d %H:%M:%S"), str))


if __name__ == "__main__":

    try:
        main()
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        log("Exception at line {}: {}".format(exc_tb.tb_lineno, e))
        traceback.print_exception(exc_type, exc_obj, exc_tb)
        log("Quitting")
        driver.quit()
        
