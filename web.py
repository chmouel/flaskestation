import datetime
import json
import logging
import os
import sys
import time

import matplotlib.pyplot as plt
import numpy as np
import qrcode
from flask import Flask, redirect, request, send_from_directory, render_template
from PIL import Image, ImageDraw, ImageFont
from PyPDF2 import PdfFileReader, PdfFileWriter

app = Flask(__name__)

# Generate time for how many minutes ago
HOW_MANY_MINUTES_AGO = 10

# How many days ago we cleanup pdf
CLEANUP_DAYS = 1

MOTIF_EMOJIS = {
    "sport": "🏃🏽‍♂️",
    "travail": "👔",
    "courses": "🛍",
    "famille": "👨‍👦",
    "sante": "💉",
}


def gen(config):
    img = Image.open("tmp/page1-template.png")
    img_array = np.array(img)

    # Erase stuff
    img_array[285:310, 240:] = 255
    img_array[330:370, 245:370] = 255
    img_array[330:370, 617:720] = 255
    img_array[376:402, 270:] = 255

    # Erase cross
    img_array[824:849, 158:181] = 255

    # # Erase Current date
    img_array[1418:1437, 187:303] = 255

    # # Erase Current time
    img_array[1418:1437, 549:611] = 255

    # Erase QR
    img_array[1355:1545, 915:1108] = 255
    img = Image.fromarray(img_array)

    # Create crosses:
    def get_cross():
        image = Image.new('RGB', (20, 20), color=(255, 255, 255))
        image_draw = ImageDraw.Draw(image)
        image_font = ImageFont.truetype("Arial.ttf", 22)
        image_draw.text((5, -2), 'X', (0, 0, 0), font=image_font)
        return np.array(image)

    img_array = np.array(img)
    cross = get_cross()
    if "travail" in config['motif']:
        img_array[530:550, 159:179] = cross
    if "courses" in config['motif']:
        img_array[621:641, 159:179] = cross
    if "sante" in config['motif']:
        img_array[742:762, 159:179] = cross
    if "famille" in config['motif']:
        img_array[826:846, 159:179] = cross
    if "sport" in config['motif']:
        img_array[990:1010, 159:179] = cross

    # Grosse flemme de tracker les pixels position et hopefully j'ai pas
    # handicap ou d'ennuis judiciaire de prevu, patch welcome si vous en avez
    # besoin ;)
    #
    # if "handicap" in config['motif]:
    #     img_array[905:925, 155:175] = cross
    # if "judiciaire" in config['motif']:
    #     img_array[1110:1140, 155:175] = cross
    # if "missions" in config['motif]:
    #     img_array[1185:1215, 155:175] = cross

    # # QR CODE
    qr_text = f"Cree le: {datetime.datetime.now().strftime('%d/%m/%Y a %H:%M')};\n" \
              f" Nom: {config['last_name']};\n" \
              f" Prenom: {config['first_name']};\n" \
              f" Naissance: {config['birth_date']} a {config['birth_city']};\n" \
              f" Adresse: {config['address']};\n" \
              f" Sortie: {config['leave_date']} a {config['leave_hour']};\n" \
              f" Motifs: {config['motif']}"

    # qr_text = "hyduzqhdzoiqd zqoihdpodqz"
    qqrcode = qrcode.make(qr_text, border=0)
    qqrcode = qqrcode.resize((185, 185))
    qqrcode = np.array(qqrcode).astype(np.uint8) * 255
    qqrcode = qqrcode.repeat(3).reshape(qqrcode.shape[0], qqrcode.shape[1], -1)
    # img_array = np.array(img)
    img_array[1361:1546, 905:1090] = np.array(qqrcode)
    img = Image.fromarray(img_array)

    # Fill args
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype("Arial.ttf", 23)
    draw.text((253, 286),
              f'{config["first_name"]} {config["last_name"]}', (0, 0, 0),
              font=font)
    draw.text((244, 331), f'{config["birth_date"]}', (0, 0, 0), font=font)
    draw.text((620, 331), f'{config["birth_city"]}', (0, 0, 0), font=font)
    draw.text((280, 376), f'{config["address"]}', (0, 0, 0), font=font)

    draw.text((190, 1420), config['leave_date'], (0, 0, 0), font=font)
    draw.text((551, 1420), config['leave_hour'], (0, 0, 0), font=font)

    plt.imsave("tmp/pass1-page1.pdf", np.array(img), format="pdf")

    # ---------------------------
    #  Second Page (Big QR code)
    # ---------------------------
    img = np.array(Image.open('tmp/page2-template.png'))
    img[:] = 255
    qqrcode = Image.fromarray(qqrcode)
    qqrcode = qqrcode.resize((qqrcode.size[0] * 3, qqrcode.size[1] * 3))
    qqrcode = np.array(qqrcode)
    img[113:113 + qqrcode.shape[0], 113:113 + qqrcode.shape[1]] = qqrcode
    plt.imsave("tmp/pass1-page2.pdf", img, format="pdf")

    # --------------------
    # Merge PDFs
    # --------------------
    pdf1 = PdfFileReader('tmp/pass1-page1.pdf')
    pdf2 = PdfFileReader('tmp/pass1-page2.pdf')
    writer = PdfFileWriter()
    writer.addPage(pdf1.getPage(0))
    writer.addPage(pdf2.getPage(0))
    writer.write(open(f"static/pdfs/{config['pdfname']}.pdf", "wb"))

    os.remove("tmp/pass1-page1.pdf")
    os.remove("tmp/pass1-page2.pdf")


def dir_cleanup(path):
    for filename in os.listdir(path):
        fpath = os.path.join(path, filename)
        if fpath.endswith(".pdf") and os.stat(
                fpath).st_mtime < time.time() - CLEANUP_DAYS * 86400:
            logging.debug("Cleaning old pdf: %s", fpath)
            os.remove(fpath)


@app.route('/attestation/static/<path:path>', methods=['GET'])
def serve_dir_directory_index(path):
    return send_from_directory('static', path)


@app.route("/attestation/<user>/<motif>")
def attestation(user, motif):
    profile_config = get_config()
    if not profile_config:
        return "Configuration error! no config.json"

    reqdate = request.args.get('ds')
    if reqdate:
        ditimeparsed = datetime.datetime.strptime(reqdate, '%Y-%m-%d')
        leave_date = ditimeparsed.strftime("%d/%m/%Y")
    else:
        leave_date = datetime.datetime.now().strftime("%d/%m/%Y")

    reqdate = request.args.get('ts')
    if reqdate:
        leave_hour = reqdate
    else:
        leave_hour = (
            datetime.datetime.now() -
            datetime.timedelta(minutes=HOW_MANY_MINUTES_AGO)).strftime("%H:%M")

    pdfname = f"{user}-{motif}-{leave_date.replace('/', '_')}-{leave_hour}"
    gen({
        **profile_config[user],
        "motif": motif,
        "leave_date": leave_date,
        "leave_hour": leave_hour,
        "pdfname": pdfname,
    })

    return redirect(f"/attestation/static/pdfs/{pdfname}.pdf", code=302)


def get_config():
    config_file = os.path.join(app.root_path, "config.json")
    if not os.path.exists(config_file):
        logging.error("No config file config.json in root dir has been found")
        return {}
    return json.load(open(config_file))


@app.route('/android-icon-<size>.png')
def androidicon(size):
    return send_from_directory(os.path.join(app.root_path, 'static',
                                            'favicons'),
                               f'android-icon-{size}.png',
                               mimetype='image/vnd.microsoft.icon')


@app.route("/attestation/")
def index():
    dir_cleanup(os.path.join(app.root_path, 'static', 'pdfs'))
    config = get_config()
    if not config:
        return "Configuration error! no config.json"

    icon_dir = os.path.join(app.root_path, 'static', "profiles")
    for profile in config:
        if os.path.exists(os.path.join(icon_dir, f"{profile}.png")):
            config[profile]["profile_icon"] = f"static/profiles/{profile}.png"
        elif os.path.exists(os.path.join(icon_dir, f"{profile}.jpg")):
            config[profile]["profile_icon"] = f"static/profiles/{profile}.jpg"
        else:
            config[profile]["profile_icon"] = ""
    return render_template('index.jinja',
                           config=config,
                           motif_emojis=MOTIF_EMOJIS)


def cli(user, motif):
    profile_config = get_config()
    if not profile_config:
        return "Configuration error! no config.json"

    leave_date = datetime.datetime.now().strftime("%d/%m/%Y")
    leave_hour = (
        datetime.datetime.now() -
        datetime.timedelta(minutes=HOW_MANY_MINUTES_AGO)).strftime("%H:%M")

    pdfname = f"{user}-{motif}-{leave_date.replace('/', '_')}-{leave_hour}"
    gen({
        **profile_config[user],
        "motif": motif,
        "leave_date": leave_date,
        "leave_hour": leave_hour,
        "pdfname": pdfname,
    })

    fpath = os.path.join(app.root_path, 'static', "pdfs", f"{pdfname}.pdf")
    os.system(f"open {fpath}")


if __name__ == '__main__':
    cli(sys.argv[1], sys.argv[2])

if __name__ != '__main__':
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
