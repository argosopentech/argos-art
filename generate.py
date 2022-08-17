#!/usr/bin/env python3

import requests, csv, os, validators, io, click, time, datetime, io, sys, shutil
from bs4 import BeautifulSoup
from PIL import Image
from jinja2 import Environment, FileSystemLoader

WEBSITE_FOLDER = "Website"
IMAGES_FOLDER = WEBSITE_FOLDER + "/Images"
STYLESHEETS_FOLDER = WEBSITE_FOLDER + "/Stylesheets"
RESCALE_FACTOR = 0.75
QUALITY_FACTOR = 70
OPTIMIZE = True
MAX_IMAGE_SIZE = 89478485
MAX_PIXEL_SIZE = 500
Image.MAX_IMAGE_PIXELS = None
UNSUPPORTED_FORMATS = ["djvu", "pdf", "svg"]
HEADERS = {
    'User-Agent': "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5)AppleWebKit/537.36 (KHTML, like Gecko)Chrome/50.0.2661.102 Safari/537.36"
}

def download_image(image_url, image_name, log_data):
    if not validators.url(image_url):
        log_data["Message"] = "Invalid URL:\n" + image_url + "\n"
        return False
    if os.path.exists(image_name):
        log_data["Message"] = "Image: " + image_name + " exists." + "\n"
        return False
    if image_url.startswith('https://upload'): return save_image(image_url, image_name, log_data)
    try:
        r = requests.get(image_url, headers=HEADERS)
    except requests.exceptions.RequestException as e:
        log_data["Message"] = "Caught an exception when loading the page:\n" + str(e) + "\n"
        return True
    soup = BeautifulSoup(r.text, 'html.parser')
    div_list = soup.find_all('div')
    image_link = ""
    for div in div_list:
        if ('class' in div.attrs and 'mw-mmv-image' in div['class']) or ('id' in div.attrs and div['id'] == 'file'):
            a_tag = div.contents[0]
            image_link = a_tag['href']
            if len(a_tag.contents) > 0:
                img_tag = a_tag.contents[0]
                if 'src' in img_tag.attrs:
                    image_link = img_tag['src']
            if not image_link:
                log_data["Message"] = "No image source url on this page:\n" + image_url + "\n"
                return True
            log_data["Error"] = save_image(image_link, image_name, log_data)
    return log_data["Error"]


def save_image(image_url, image_name, log_data):
    try:
        image_extension =  image_url.split(".")[-1]
        if image_extension in UNSUPPORTED_FORMATS:
            log_data["Message"] = "DJVU file format is not supported!\n"
            log_data["Message"] += "Image URL:\n" + image_url + "\n"
            return False
        if image_url.startswith("//"):
            image_url = image_url.replace("//", "https://", 1)
        image_content = requests.get(image_url, headers=HEADERS).content
        if "File not found" in str(image_content):
            log_data["Message"] = "File not found at URL: " + image_url + "\n"
            return False
        image_file = io.BytesIO(image_content)
        try:
            image = Image.open(image_file)
        except Exception as e:
            log_data["Message"] = "Error opening Image in the memory:\n"
            log_data["Message"] += image_name + "\nfrom url:\n" + image_url
            log_data["Message"] += "\nException:\n" + str(e) + "\n"
            log_data["Message"] += "URL content = " + str(image_content) + "\n"
            return True
    except requests.exceptions.RequestException as e:
        log_data["Message"] = "Exception when saving the image " + image_name + " to the memory.\n"
        log_data["Message"] += "Image URL:\n" + image_url + "\nException:\n" + str(e) + "\n"
        return True
    if image.size[0] * image.size[1] > MAX_IMAGE_SIZE:
        log_data["Message"] = "Image size is greater than the size limit defined by Pillow\n"
        log_data["Message"] += "Image Name:\n" + image_name + "\nImage URL:" + image_url + "\n"
        return False
    image_size = [image.size[0], image.size[1]]
    while max(image_size[0], image_size[1]) > MAX_PIXEL_SIZE:
        image_size[0] = int(image_size[0] * RESCALE_FACTOR)
        image_size[1] = int(image_size[1] * RESCALE_FACTOR)
    image.thumbnail((image_size[0], image_size[1]), Image.Resampling.LANCZOS)
    if not image:
        log_data["Message"] = "Image = None!\nName:\n" + image_name + "\nURL:\n" + image_url + "\n"
        return True
    with open(image_name, 'wb') as f:
        if image.format == "TIFF":
            image.save(f, image.format)
        else:
            image.save(f, image.format, optimize=OPTIMIZE, quality=QUALITY_FACTOR)
        log_data["Message"] = "Writing: " + image_name + " with format: " + image.format + "\n"
        return False


def read_file():
    started_at_seconds = time.time()
    starting_time = datetime.datetime.now()
    starting_time = starting_time.strftime("%I:%M:%S")
    with open('Art.csv', 'r', encoding='utf-8') as csv_file, open('log.txt', 'a') as log_file:
        csv_reader = csv.DictReader(csv_file)
        csv_list = list(csv_reader)
        csv_size = len(csv_list) - 1
        index = 0
        for line in csv_list:
            log_data = {"Error": False, "Message": ""}
            if not line['ID'] or not line['Artist'] or not line['Wikimedia'] or line['Wikimedia'] == '':
                print_skipped_lines(log_data, log_file, index, line)
                continue
            image_name = str(line['ID']) + '.jpg'
            image_url = str(line['Wikimedia']).replace("\t", "").replace(" ", "")
            if image_url.startswith("//"):
                image_url = image_url.replace("//", "https://", 1)
            image_path = IMAGES_FOLDER + "/" + image_name
            print_progress(started_at_seconds, index, csv_size, starting_time, image_name, image_url)
            log_data["Error"] = download_image(image_url, image_path, log_data)
            if log_data["Error"]:
                print("Log Data:\n", log_data["Message"])
                log_file.write(log_data["Message"])
                return
            time.sleep(0.025)
            index += 1


def print_skipped_lines(log_data, log_file, index, line):
    click.clear()
    log_data["Message"] = "Line " + str(index + 1) + " skipped.\n"
    log_data["Message"] += "ID: " + str(line['ID']) + "\n"
    log_data["Message"] += "Name: " + str(line['Artist']) + "\n"
    log_data["Message"] += "URL: " + str(line['Wikimedia']) + "\n"
    print(log_data["Message"])
    log_file.write(log_data["Message"])


def print_progress(started_at_seconds, index, csv_size, starting_time, image_name, image_url):
    click.clear()
    elapsed_seconds = time.time() - started_at_seconds
    elapsed_minutes, elapsed_seconds = divmod(elapsed_seconds, 60)
    elapsed_hours, elapsed_minutes = divmod(elapsed_minutes, 60)
    elapsed_seconds = int(elapsed_seconds)
    elapsed_minutes = int(elapsed_minutes)
    elapsed_hours = int(elapsed_hours)
    progress = "Progress: " + \
        str(round((index + 1) / csv_size * 100, 2)) + "% - "
    if elapsed_hours > 0:
        progress += f"{elapsed_hours:d} hours, {elapsed_minutes:02d} minutes and {elapsed_seconds:02d} seconds"
    elif elapsed_minutes > 0:
        progress += f"{elapsed_minutes:02d} minutes and {elapsed_seconds:02d} seconds"
    else:
        progress += f"{elapsed_seconds:02d} seconds"
    progress += " elapsed since " + str(starting_time) + "\n"
    progress += str(index + 1) + " of " + str(csv_size) + \
        " images processed.\n"
    progress += "Image Name: " + image_name + "\nImage URL:\n" + image_url + "\n\n"
    print(progress)


def generate_website():
    images = []
    file_loader = FileSystemLoader('Templates')
    env = Environment(loader=file_loader)
    with open('Art.csv', encoding='utf-8') as csv_file:
        csv_reader = csv.DictReader(csv_file)
        for line in csv_reader:
            image_name = IMAGES_FOLDER + "/" + str(line['ID']) + ".jpg"
            if not os.path.exists(image_name): continue
            images.append(line)
    if len(images) > 0:
        index_file_name = WEBSITE_FOLDER + "/index.html"
        if not os.path.exists(index_file_name):
            render_index_page(images, index_file_name, env)
        for image in images:
            image_file_name = WEBSITE_FOLDER + "/i/" + str(image["ID"]) + ".html"
            if not os.path.exists(image_file_name):
                render_image_page(image, image_file_name, env)
        

def render_index_page(images, file_name, env):
    template = env.get_template('index.html')
    output = template.render(title='Argos Images', images=images)
    with open(file_name, 'w', encoding='utf-8') as index_file:
        index_file.write(output)


def render_image_page(image, file_name, env):
    template = env.get_template('image.html')
    title = str(image["ID"]) + ". " + str(image["Artist"]) + " - " + str(image["Year"])
    output = template.render(title=title, image=image)
    with open(file_name, 'w', encoding='utf-8') as image_file:
        image_file.write(output)


def make_directories():
    if not os.path.isdir(WEBSITE_FOLDER): os.mkdir(WEBSITE_FOLDER)
    if not os.path.isdir(WEBSITE_FOLDER + "/i"): os.mkdir(WEBSITE_FOLDER + "/i")
    if not os.path.isdir(IMAGES_FOLDER): os.mkdir(IMAGES_FOLDER)


def copy_stylesheets():
    shutil.copytree("Stylesheets", STYLESHEETS_FOLDER)


def main():
    make_directories()
    read_file()
    generate_website()
    copy_stylesheets()

if __name__ == "__main__":
    main()