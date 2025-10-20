from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageEnhance
import base64, os, uuid
from pydantic import BaseModel

app = FastAPI()

# ✅ Mở toàn quyền CORS để mọi nơi đều gọi được API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Cho phép tất cả domain
    allow_credentials=True,
    allow_methods=["*"],          # Cho phép tất cả HTTP methods
    allow_headers=["*"],          # Cho phép tất cả headers
)


def apply_frame(base_image_path, frame_path, output_path, pink_strength=0.25):
    base = Image.open(base_image_path).convert("RGBA")
    frame = Image.open(frame_path).convert("RGBA")
    base = base.resize(frame.size)

    # 🌸 Tạo lớp phủ màu hồng nhẹ
    pink_overlay = Image.new("RGBA", base.size, (255, 182, 193, int(255 * pink_strength)))
    base = Image.alpha_composite(base, pink_overlay)

    # ☀️ Tăng sáng nhẹ
    enhancer = ImageEnhance.Brightness(base)
    base = enhancer.enhance(1.1)

    # 🖼 Ghép khung
    combined = Image.alpha_composite(base, frame)
    combined.save(output_path, format="PNG")
    return output_path


@app.post("/apply_frame")
async def apply_frame_endpoint(
    image: UploadFile,
    pink_strength: float = Form(0.25)
):
    image_bytes = await image.read()
    base_path = "example.jpg"
    with open(base_path, "wb") as f:
        f.write(image_bytes)

    frame_path = "static/frame4.png"
    output_path = "anh_da_ghep_pink.png"
    apply_frame(base_path, frame_path, output_path, pink_strength=pink_strength)

    with open(output_path, "rb") as f:
        result_b64 = base64.b64encode(f.read()).decode("utf-8")

    return result_b64


class ImagePayload(BaseModel):
    image_b64: str


# =====================
# 🧩 API: Upload ảnh base64 → lưu file → trả URL (JSON body)
# =====================
@app.post("/upload_base64")
async def upload_base64(payload: ImagePayload):
    """Nhận ảnh base64 (JSON), lưu vào thư mục /image, và trả về URL tải ảnh"""
    try:
        # Tạo thư mục nếu chưa có
        os.makedirs("image", exist_ok=True)

        # Sinh tên file ngẫu nhiên
        filename = f"{uuid.uuid4().hex}.png"
        file_path = os.path.join("image", filename)

        # Giải mã base64 (hỗ trợ cả data URL)
        image_b64 = payload.image_b64
        if image_b64.startswith("data:image"):
            image_b64 = image_b64.split(",", 1)[1]
        image_data = base64.b64decode(image_b64)

        # Lưu file
        with open(file_path, "wb") as f:
            f.write(image_data)

        # Tạo URL để truy cập ảnh
        image_url = f"/image/{filename}"
        return {"filename": filename, "url": image_url}

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# =====================
# 🖼 API: Trả ảnh trong /image
# =====================
@app.get("/image/{filename}")
def get_uploaded_image(filename: str):
    """Trả file ảnh từ thư mục /image"""
    file_path = os.path.join("image", filename)
    if not os.path.exists(file_path):
        return JSONResponse({"error": "File không tồn tại."}, status_code=404)
    return FileResponse(file_path)


# ✅ Mount static để truy cập index.html, frame2.png, frame4.png...
app.mount("/", StaticFiles(directory="static", html=True), name="static")
