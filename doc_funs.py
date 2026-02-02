import re
import os
import tempfile
from typing import Optional
import aiohttp
from docx import Document
from telegram import Update
from telegram.ext import ContextTypes
from telegram import InputFile


GOOGLE_DOC_ID_RE = re.compile(r"/document/d/([a-zA-Z0-9_-]+)")

def extract_google_doc_id(url: str) -> Optional[str]:
    """
    Возвращает Google Doc ID из ссылки вида:
    https://docs.google.com/document/d/<ID>/edit?...
    """
    m = GOOGLE_DOC_ID_RE.search(url or "")
    return m.group(1) if m else None

async def download_google_doc_as_docx(doc_id: str) -> str:
    """
    Скачивает Google Doc как .docx во временный файл.
    Возвращает путь к файлу.
    """
    export_url = f"https://docs.google.com/document/d/{doc_id}/export?format=docx"

    fd, tmp_path = tempfile.mkstemp(prefix="gdoc_", suffix=".docx")
    os.close(fd)  # файл будем писать сами

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(export_url, allow_redirects=True) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"Google export failed: HTTP {resp.status}")
                data = await resp.read()

        with open(tmp_path, "wb") as f:
            f.write(data)

        return tmp_path

    except Exception:
        # если скачивание упало — подчистим временный файл
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise

def extract_text_from_docx(docx_path: str) -> str:
    """
    Достаёт текст из .docx (параграфы -> строки).
    """
    doc = Document(docx_path)
    lines = [p.text.strip() for p in doc.paragraphs if p.text and p.text.strip()]
    return "\n".join(lines).strip()

async def send_results_doc_and_text(update: Update, context: ContextTypes.DEFAULT_TYPE, doc_url: str):
    chat_id = update.effective_chat.id

    doc_id = extract_google_doc_id(doc_url)
    if not doc_id:
        await context.bot.send_message(chat_id=chat_id, text="Не смог распознать ссылку на документ.")
        return

    tmp_path = None
    try:
        tmp_path = await download_google_doc_as_docx(doc_id)
        text = extract_text_from_docx(tmp_path)

        # 1) отправляем документ
        filename = f"results_{doc_id}.docx"
        with open(tmp_path, "rb") as f:
            await context.bot.send_document(
                chat_id=chat_id,
                document=InputFile(f, filename=filename),
                caption="Ваш документ с результатами ✅"
            )

        # # 2) отправляем текст (если он есть)
        # if text:
        #     # Telegram ограничивает длину сообщения (~4096 символов)
        #     max_len = 3900
        #     if len(text) <= max_len:
        #         await context.bot.send_message(chat_id=chat_id, text=text)
        #     else:
        #         # если много — режем на части
        #         for i in range(0, len(text), max_len):
        #             await context.bot.send_message(chat_id=chat_id, text=text[i:i+max_len])
        # else:
        #     await context.bot.send_message(chat_id=chat_id, text="Документ скачан, но текста внутри не найдено.")

    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"Не получилось скачать/прочитать документ: {e}")

    finally:
        # 3) удаляем временный файл
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass

