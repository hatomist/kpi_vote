from pyzbar import pyzbar


def get_code_from_image(img):
    barcodes = pyzbar.decode(img)
    codes = []
    for code in barcodes:
        x, y, w, h = code.rect
        # 1
        barcode_info = code.data.decode('utf-8')
        codes.append(barcode_info)

    return codes[0] if codes else None
