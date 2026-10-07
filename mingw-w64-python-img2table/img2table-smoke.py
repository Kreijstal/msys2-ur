import os
import sys

import cv2
import numpy as np

out = sys.argv[1]
cells = [["Name", "Qty", "Price"],
         ["Apple", "12", "3.50"],
         ["Melon", "7", "9.25"]]

# 3x3 ruled table rendered with OpenCV
h, w, x0, y0, cw, ch = 400, 760, 40, 40, 220, 90
img = np.full((h, w, 3), 255, np.uint8)
for i in range(4):
    cv2.line(img, (x0, y0 + i * ch), (x0 + 3 * cw, y0 + i * ch), (0, 0, 0), 3)
    cv2.line(img, (x0 + i * cw, y0), (x0 + i * cw, y0 + 3 * ch), (0, 0, 0), 3)
for r, row in enumerate(cells):
    for c, txt in enumerate(row):
        cv2.putText(img, txt, (x0 + c * cw + 25, y0 + r * ch + 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0, 0, 0), 3)
png = os.path.join(out, "table.png")
cv2.imwrite(png, img)

from img2table.document import PDF, Image
from img2table.ocr import RapidOCR


def grid(table):
    return [[(cell.value or "").strip() for cell in row] for row in table.content.values()]


def norm(rows):
    return [[v.replace(" ", "").upper() for v in row] for row in rows]


ocr = RapidOCR()
tables = Image(png).extract_tables(ocr=ocr, implicit_rows=False, borderless_tables=False)
print("image tables:", len(tables))
got = grid(tables[0])
print("image cells:", got)
assert norm(got) == norm(cells), got

xlsx = os.path.join(out, "tables.xlsx")
Image(png).to_xlsx(xlsx, ocr=ocr)
assert os.path.getsize(xlsx) > 1000
print("xlsx:", os.path.getsize(xlsx), "bytes")

# same table as a native PDF (text layer, no OCR needed)
import pymupdf
doc = pymupdf.open()
page = doc.new_page(width=612, height=792)
px, py, pw, ph = 72, 100, 150, 40
for i in range(4):
    page.draw_line((px, py + i * ph), (px + 3 * pw, py + i * ph), width=1.5)
    page.draw_line((px + i * pw, py), (px + i * pw, py + 3 * ph), width=1.5)
for r, row in enumerate(cells):
    for c, txt in enumerate(row):
        page.insert_text((px + c * pw + 12, py + r * ph + 26), txt, fontsize=14)
pdf = os.path.join(out, "table.pdf")
doc.save(pdf)

ptables = PDF(pdf).extract_tables(implicit_rows=False, borderless_tables=False)
got = grid(ptables[0][0])
print("pdf cells:", got)
assert norm(got) == norm(cells), got
print("img2table ok")
