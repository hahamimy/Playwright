import asyncio
import csv
import json
import os
from urllib.parse import unquote
from playwright.async_api import async_playwright

# === THÔNG TIN ĐĂNG NHẬP ===
USERNAME = "muaxuan0505"
PASSWORD = "123asdasd"

# === TÊN FILE CSV ===
DATA_DIR = "ThongKE"
CSV_FILE = os.path.join(DATA_DIR, "mau.csv")

async def init_csv():
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(CSV_FILE):
        os.remove(CSV_FILE)
        print(f"[INFO] Đã xóa file {CSV_FILE} cũ.")

    with open(CSV_FILE, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow([
            "phien", "xuc_xac_1", "xuc_xac_2", "xuc_xac_3",
            "tong_diem", "ket_qua_that",
            "du_doan", "ket_qua_du_doan", "tien_cuoc", "cua_cuoc"
        ])
    print(f"[INFO] Đã tạo file {CSV_FILE} mới.")

async def get_txtTimerBet_text(page):
    try:
        return await page.evaluate("""
            () => {
                const el = document.querySelector("#txtTimerBet");
                return el?.innerText?.trim() || el?.textContent?.trim();
            }
        """)
    except:
        return None

async def get_txtTimerBet_style(page):
    try:
        return await page.evaluate("""
            () => document.querySelector("#txtTimerBet")?.getAttribute("style") || ""
        """)
    except:
        return ""

async def main():
    await init_csv()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        # ✅ Chặn tải ảnh, font, media
        async def route_block_media(route):
            if route.request.resource_type in ["image", "font", "media"]:
                await route.abort()
            else:
                await route.continue_()

        await page.route("**/*", route_block_media)


        print("[INFO] Truy cập trang...")
        await page.goto("https://gamvip.com", timeout=60000)

        print("[INFO] Đăng nhập...")
        await page.fill('input[name="txtUsername"]', USERNAME)
        await page.fill('input[name="txtPassword"]', PASSWORD)
        await page.click('.button-login')
        await page.wait_for_selector("#mainTurnTx")
        print("[OK] Đăng nhập thành công!")

        last_phien = None

        while True:
            try:
                print("[INFO] Đợi phiên mới...")
                while True:
                    text = await get_txtTimerBet_text(page)
                    style = await get_txtTimerBet_style(page)
                    if "display: none" in style and text in ["00:59", "00:58", "00:57", "00:56", "00:55", "00:54", "00:53"]:
                        break
                    await asyncio.sleep(0.1)

                print("[INFO] Phát hiện phiên mới! Bắt đầu quét kết quả...")

                for _ in range(180):  # Tối đa 90s
                    items = await page.query_selector_all("#mainTurnTx i")
                    if not items:
                        await asyncio.sleep(0.1)
                        continue

                    latest = items[-1]
                    data = await latest.get_attribute("data-value")
                    if not data:
                        await asyncio.sleep(0.1)
                        continue

                    try:
                        json_data = json.loads(unquote(data))
                    except Exception as e:
                        print("[ERROR] Lỗi JSON:", e)
                        await asyncio.sleep(0.1)
                        continue

                    phien = json_data.get("GameSessionID")
                    if last_phien is not None and phien <= last_phien:
                        await asyncio.sleep(0.1)
                        continue

                    # Kiểm tra trùng phiên
                    existing_phien = set()
                    if os.path.exists(CSV_FILE):
                        with open(CSV_FILE, 'r', encoding='utf-8') as f:
                            reader = csv.DictReader(f, delimiter=';')
                            for row in reader:
                                existing_phien.add(int(row['phien'].lstrip('#')))

                    if phien in existing_phien:
                        print(f"[WARN] Phiên {phien} đã tồn tại.")
                        last_phien = phien
                        break

                    # === GHI KẾT QUẢ MỚI ===
                    x1 = json_data["Dice1"]
                    x2 = json_data["Dice2"]
                    x3 = json_data["Dice3"]
                    tong = json_data["DiceSum"]
                    ket_qua = "Tài" if tong >= 11 else "Xỉu"

                    with open(CSV_FILE, mode='a', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f, delimiter=';')
                        writer.writerow([
                            f"#{phien}", x1, x2, x3, tong, ket_qua,
                            "", "", "", ""
                        ])

                    last_phien = phien
                    print(f"[OK] Ghi phiên #{phien}: {x1},{x2},{x3} → {tong} ({ket_qua})")
                    break

                print("[INFO] Nghỉ 70s rồi tiếp tục vòng mới...")
                await asyncio.sleep(70)

            except Exception as e:
                print(f"[ERROR] Trong vòng lặp: {e}")
                await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())

