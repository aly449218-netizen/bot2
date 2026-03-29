import cv2
import numpy as np
import pytesseract
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

import os
TOKEN = os.getenv("TOKEN")

# ================= Sudoku Solver =================
def is_valid(board, row, col, num):
    for i in range(9):
        if board[row][i] == num or board[i][col] == num:
            return False

    start_row, start_col = 3*(row//3), 3*(col//3)
    for i in range(3):
        for j in range(3):
            if board[start_row+i][start_col+j] == num:
                return False

    return True

def solve(board):
    for i in range(9):
        for j in range(9):
            if board[i][j] == 0:
                for num in range(1, 10):
                    if is_valid(board, i, j, num):
                        board[i][j] = num
                        if solve(board):
                            return True
                        board[i][j] = 0
                return False
    return True

# ================= Image Processing =================
def extract_grid(image_path):
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5,5), 0)
    thresh = cv2.adaptiveThreshold(blur,255,1,1,11,2)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    biggest = max(contours, key=cv2.contourArea)

    pts = biggest.reshape(4,2)
    pts = sorted(pts, key=lambda x: x[0]+x[1])

    return img  # تبسيط (بدون perspective الآن)

def get_board(image_path):
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    board = []
    h, w = gray.shape
    cell_h, cell_w = h//9, w//9

    for i in range(9):
        row = []
        for j in range(9):
            cell = gray[i*cell_h:(i+1)*cell_h, j*cell_w:(j+1)*cell_w]

            _, thresh = cv2.threshold(cell, 150, 255, cv2.THRESH_BINARY_INV)

            text = pytesseract.image_to_string(
                thresh,
                config='--psm 10 -c tessedit_char_whitelist=123456789'
            )

            try:
                num = int(text.strip())
            except:
                num = 0

            row.append(num)
        board.append(row)

    return board

def draw_solution(original_path, board):
    img = cv2.imread(original_path)
    h, w, _ = img.shape
    cell_h, cell_w = h//9, w//9

    for i in range(9):
        for j in range(9):
            if board[i][j] != 0:
                cv2.putText(
                    img,
                    str(board[i][j]),
                    (j*cell_w + 10, i*cell_h + 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 255, 0),
                    2
                )

    output_path = "solved.png"
    cv2.imwrite(output_path, img)
    return output_path

# ================= Telegram =================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    file = await photo.get_file()
    await file.download_to_drive("sudoku.jpg")

    await update.message.reply_text("⏳ جاري حل السودوكو...")

    board = get_board("sudoku.jpg")

    if solve(board):
        result_img = draw_solution("sudoku.jpg", board)
        await update.message.reply_photo(photo=open(result_img, 'rb'))
    else:
        await update.message.reply_text("❌ ما كدرت أحل اللغز")

# ================= Run =================
app = Application.builder().token(TOKEN).build()
app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

print("Bot is running...")
app.run_polling()
