import base64
import io
import qrcode

def make_qr_data_url(value):
    image = qrcode.make(value)
    output = io.BytesIO()
    image.save(output, format="PNG")
    encoded = base64.b64encode(output.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"
