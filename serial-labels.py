"""
Prints serial numbers on Avery 6467 sticker labels.
(c) Ameryn Media, 2015. All rights reserved.
"""

from ConfigParser import ConfigParser
import os

from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch, mm

import config


def print_serial_labels(series):
    # Draw front covers
    stickers_location = os.path.join(config.pdf_folder, 'serial-stickers.pdf')
    c = canvas.Canvas(stickers_location, pagesize=letter)
    width, height = letter
    pdfmetrics.registerFont(TTFont('Garamond', config.font_path))
    c.setFont('Garamond', 18)
    for count, num in enumerate(series):
        if count > 0 and count % 80 == 0:
            c.showPage()
            c.setFont('Garamond', 18)
        left_padding = count % 80 / 20 * 2.0625 * inch
        c.drawString(0.5*inch + left_padding, 10.15*inch - count%20*0.5*inch, str(num))
    c.save()

    # Open notes in default text editor
    os.startfile(stickers_location)

if __name__ == '__main__':
    order = 4178
    item = (1, 300)
    print_serial_labels([str(order).zfill(5) + '-' + str(i).zfill(5) for i in range(item[0], item[1] + 1)])
    print [str(order).zfill(5) + '-' + str(i).zfill(5) for i in range(item[0], item[1] + 1)]