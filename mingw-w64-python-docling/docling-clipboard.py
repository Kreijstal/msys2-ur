#!/usr/bin/env python
"""Run Granite-Docling on the image in the Windows clipboard.

Copy a screenshot of a table/page (Win+Shift+S, "Copy image", ...) and run

    python docling-clipboard.py            # DocTags as produced by the model
    python docling-clipboard.py --otsl     # only the <otsl> table markup
    python docling-clipboard.py --html     # HTML via docling-core
    python docling-clipboard.py --markdown # Markdown via docling-core

--image FILE reads an image file instead of the clipboard. The model
(ibm-granite/granite-docling-258M) is downloaded from Hugging Face on first use.
"""

import argparse
import ctypes
import io
import re
import struct
import sys

from PIL import Image

MODEL_ID = "ibm-granite/granite-docling-258M"
PROMPT = "Convert this page to docling."


def _clipboard_dib_ctypes():
    """Read CF_DIB from the clipboard with plain Win32 calls.

    Fallback for Pillow builds whose ImageGrab.grabclipboard() is unavailable.
    """
    CF_DIB = 8
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    user32.OpenClipboard.argtypes = [ctypes.c_void_p]
    user32.GetClipboardData.restype = ctypes.c_void_p
    user32.GetClipboardData.argtypes = [ctypes.c_uint]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalSize.restype = ctypes.c_size_t
    kernel32.GlobalSize.argtypes = [ctypes.c_void_p]

    if not user32.OpenClipboard(None):
        raise OSError("OpenClipboard failed: %d" % ctypes.get_last_error())
    try:
        handle = user32.GetClipboardData(CF_DIB)
        if not handle:
            return None
        ptr = kernel32.GlobalLock(handle)
        try:
            dib = ctypes.string_at(ptr, kernel32.GlobalSize(handle))
        finally:
            kernel32.GlobalUnlock(handle)
    finally:
        user32.CloseClipboard()

    # prepend a BITMAPFILEHEADER so PIL's BMP reader can parse the DIB
    header_size, = struct.unpack_from("<I", dib, 0)
    bit_count, = struct.unpack_from("<H", dib, 14)
    compression, = struct.unpack_from("<I", dib, 16)
    colors_used, = struct.unpack_from("<I", dib, 32)
    if colors_used == 0 and bit_count <= 8:
        colors_used = 1 << bit_count
    masks = 12 if compression == 3 and header_size == 40 else 0  # BI_BITFIELDS
    offset = 14 + header_size + masks + 4 * colors_used
    bmp = b"BM" + struct.pack("<IHHI", 14 + len(dib), 0, 0, offset) + dib
    return Image.open(io.BytesIO(bmp))


def grab_clipboard_image():
    data = None
    try:
        from PIL import ImageGrab

        data = ImageGrab.grabclipboard()
    except (ImportError, AttributeError, NotImplementedError, OSError) as e:
        print(f"ImageGrab.grabclipboard() unavailable ({e}); using ctypes", file=sys.stderr)
        data = _clipboard_dib_ctypes()
    if isinstance(data, list):  # files copied in Explorer
        for name in data:
            try:
                return Image.open(name)
            except OSError:
                continue
        data = None
    if data is None:
        sys.exit("no image in the clipboard")
    return data


def run_granite_docling(image, max_new_tokens):
    import torch
    from transformers import AutoModelForImageTextToText, AutoProcessor

    processor = AutoProcessor.from_pretrained(MODEL_ID)
    model = AutoModelForImageTextToText.from_pretrained(MODEL_ID, dtype=torch.float32)
    model.eval()
    messages = [{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": PROMPT}]}]
    prompt = processor.apply_chat_template(messages, add_generation_prompt=True)
    inputs = processor(text=prompt, images=[image], return_tensors="pt")
    with torch.inference_mode():
        out = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
    new_tokens = out[:, inputs["input_ids"].shape[1]:]
    doctags = processor.batch_decode(new_tokens, skip_special_tokens=False)[0]
    for eos in ("<end_of_utterance>", "<|end_of_text|>"):
        doctags = doctags.replace(eos, "")
    return doctags.strip()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    fmt = ap.add_mutually_exclusive_group()
    fmt.add_argument("--otsl", action="store_true", help="print only the <otsl>...</otsl> tables")
    fmt.add_argument("--html", action="store_true", help="print HTML (docling-core)")
    fmt.add_argument("--markdown", action="store_true", help="print Markdown (docling-core)")
    ap.add_argument("--image", help="read this image file instead of the clipboard")
    ap.add_argument("--max-new-tokens", type=int, default=4096)
    args = ap.parse_args()

    image = Image.open(args.image) if args.image else grab_clipboard_image()
    image = image.convert("RGB")
    print(f"image {image.size[0]}x{image.size[1]}, running {MODEL_ID} ...", file=sys.stderr)

    doctags = run_granite_docling(image, args.max_new_tokens)

    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    if args.otsl:
        tables = re.findall(r"<otsl>.*?</otsl>", doctags, flags=re.S)
        if not tables:
            sys.exit("no <otsl> table in the output:\n" + doctags)
        print("\n".join(tables))
    elif args.html or args.markdown:
        from docling_core.types.doc.document import DoclingDocument, DocTagsDocument

        dt_doc = DocTagsDocument.from_doctags_and_image_pairs([doctags], [image])
        doc = DoclingDocument.load_from_doctags(dt_doc, document_name="clipboard")
        print(doc.export_to_html() if args.html else doc.export_to_markdown())
    else:
        print(doctags)


if __name__ == "__main__":
    main()
