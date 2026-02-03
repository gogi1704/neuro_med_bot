import aiosqlite
import datetime
import asyncio
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
from typing import Optional

db_path = 'dialogs.db'
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # на уровень выше папки db
CREDS_PATH = os.path.join(BASE_DIR, "docs", "after-tests-db-e0cd34372c4a.json")

# ==== Настройки Google API ====
SCOPE = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
SPREADSHEET_NAME = "after_tests_db"  # Имя файла в Google Sheets


# =========================================================
# Добавили message_links, user_reply_state, user_answer_state
# =========================================================
async def init_db():
    async with aiosqlite.connect(db_path) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS neuro_bot_dialogs (
                telegram_id INTEGER PRIMARY KEY,
                user_name TEXT,
                dialog_text TEXT,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                med_id TEXT,
                user_state TEXT
            )
        """)

        # await db.execute("""
        #     CREATE TABLE IF NOT EXISTS user_data (
        #         user_id INTEGER PRIMARY KEY,
        #         name TEXT NOT NULL,
        #         is_medosomotr TEXT,
        #         phone TEXT,
        #         register_date DATETIME DEFAULT CURRENT_TIMESTAMP,
        #         from_manager TEXT,
        #         privacy_policy_date DATETIME DEFAULT CURRENT_TIMESTAMP,
        #         get_dop_tests TEXT
        #     )
        # """)
        #
        # await db.execute("""
        #     CREATE TABLE IF NOT EXISTS user_anketa (
        #         user_id INTEGER PRIMARY KEY,
        #         organization_or_inn TEXT,
        #         osmotr_date DATETIME,
        #         age INTEGER,
        #         weight TEXT,
        #         height TEXT,
        #         smoking TEXT,
        #         alcohol TEXT,
        #         physical_activity TEXT,
        #         hypertension TEXT,
        #         darkening_of_the_eyes TEXT,
        #         sugar TEXT,
        #         joint_pain TEXT,
        #         chronic_diseases TEXT,
        #         FOREIGN KEY(user_id) REFERENCES user_data(user_id)
        #     )
        # """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS neuro_dialog_states (
                user_id INTEGER PRIMARY KEY,
                dialog_state TEXT NOT NULL
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                key TEXT PRIMARY KEY,
                is_active BOOLEAN DEFAULT 1
            )
        """)

        # ===== NEW (как в другом боте) =====
        await db.execute("""
            CREATE TABLE IF NOT EXISTS neuro_message_links (
                group_message_id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS neuro_user_reply_state (
                user_id INTEGER PRIMARY KEY,
                manager_message_id TEXT
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS neuro_user_answer_state (
                user_id INTEGER PRIMARY KEY,
                manager_message_id TEXT
            )
        """)
        # ===================================
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tests_and_results (
                med_id INTEGER PRIMARY KEY,
                results TEXT,
                deviations TEXT,
                decode TEXT
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS pending_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                med_id INTEGER NOT NULL,
                telegram_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL,
                kind TEXT NOT NULL,  -- 'results' | 'decode'
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(med_id, kind)
            )
        """)
        await db.commit()

    await sync_from_google_sheets()


# ==== Подключение к Google Sheets ====
def get_sheet():
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDS_PATH, SCOPE)
    client = gspread.authorize(creds)
    sheet = client.open(SPREADSHEET_NAME)
    return {
        "neuro_bot_dialogs": sheet.worksheet("neuro_bot_dialogs"),
        "neuro_dialog_states": sheet.worksheet("neuro_dialog_states"),
        "api_keys": sheet.worksheet("api_keys"),
        "neuro_message_links": sheet.worksheet("neuro_message_links"),
        "neuro_user_reply_state": sheet.worksheet("neuro_user_reply_state"),
        "neuro_user_answer_state": sheet.worksheet("neuro_user_answer_state"),
        "tests_and_results": sheet.worksheet("tests_and_results"),
        "pending_notifications": sheet.worksheet("pending_notifications"),  # ✅ NEW
    }


# =========================================================
# SYNC FROM GOOGLE SHEETS (оставил твой подход; новые таблицы не трогаем)
# =========================================================
async def sync_from_google_sheets():
    sheets = get_sheet()

    def _safe_int(x: str, default: int | None = None) -> int | None:
        try:
            x = str(x).strip()
            if x == "":
                return default
            return int(float(x))  # на случай "123.0" из Sheets
        except Exception:
            return default

    async with aiosqlite.connect(db_path) as db:
        # Очистка таблиц (как у тебя)
        await db.execute("DELETE FROM neuro_bot_dialogs")
        await db.execute("DELETE FROM neuro_dialog_states")
        await db.execute("DELETE FROM api_keys")
        await db.execute("DELETE FROM neuro_message_links")
        await db.execute("DELETE FROM neuro_user_reply_state")
        await db.execute("DELETE FROM neuro_user_answer_state")
        await db.execute("DELETE FROM tests_and_results")
        await db.execute("DELETE FROM pending_notifications")  # ✅ NEW

        # ---------------------------
        # neuro_bot_dialogs
        # ---------------------------
        rows = sheets["neuro_bot_dialogs"].get_all_values()[1:]
        for r in rows:
            # ожидаем 6 колонок
            if not r or len(r) < 6:
                continue

            telegram_id, user_name, dialog_text, updated_at, med_id, user_state = r[:6]
            tid = _safe_int(telegram_id)
            if tid is None:
                continue

            await db.execute(
                """
                INSERT INTO neuro_bot_dialogs
                (telegram_id, user_name, dialog_text, updated_at, med_id, user_state)
                VALUES (?,?,?,?,?,?)
                """,
                (tid, user_name, dialog_text, updated_at, med_id, user_state)
            )

        # ---------------------------
        # neuro_dialog_states
        # ---------------------------
        rows = sheets["neuro_dialog_states"].get_all_values()[1:]
        for r in rows:
            if not r or len(r) < 2:
                continue
            user_id, dialog_state = r[:2]
            uid = _safe_int(user_id)
            if uid is None:
                continue
            await db.execute(
                "INSERT INTO neuro_dialog_states (user_id, dialog_state) VALUES (?, ?)",
                (uid, dialog_state)
            )

        # ---------------------------
        # neuro_message_links
        # ---------------------------
        rows = sheets["neuro_message_links"].get_all_values()[1:]
        for r in rows:
            if not r or len(r) < 2:
                continue
            group_message_id, user_id = r[:2]
            uid = _safe_int(user_id)
            gmid = _safe_int(group_message_id)
            if uid is None or gmid is None:
                continue
            await db.execute(
                "INSERT INTO neuro_message_links (group_message_id, user_id) VALUES (?, ?)",
                (gmid, uid)
            )

        # ---------------------------
        # neuro_user_reply_state
        # ---------------------------
        rows = sheets["neuro_user_reply_state"].get_all_values()[1:]
        for r in rows:
            if not r or len(r) < 2:
                continue
            user_id, manager_message_id = r[:2]
            uid = _safe_int(user_id)
            if uid is None:
                continue
            await db.execute(
                "INSERT INTO neuro_user_reply_state (user_id, manager_message_id) VALUES (?, ?)",
                (uid, manager_message_id)
            )

        # ---------------------------
        # neuro_user_answer_state
        # ---------------------------
        rows = sheets["neuro_user_answer_state"].get_all_values()[1:]
        for r in rows:
            if not r or len(r) < 2:
                continue
            user_id, manager_message_id = r[:2]
            uid = _safe_int(user_id)
            if uid is None:
                continue
            await db.execute(
                "INSERT INTO neuro_user_answer_state (user_id, manager_message_id) VALUES (?, ?)",
                (uid, manager_message_id)
            )

        # ---------------------------
        # tests_and_results
        # ---------------------------
        rows = sheets["tests_and_results"].get_all_values()[1:]
        for r in rows:
            if not r or len(r) < 4:
                continue
            med_id, results, deviations, decode = r[:4]
            mid = _safe_int(med_id)
            if mid is None:
                continue
            await db.execute(
                "INSERT INTO tests_and_results (med_id, results, deviations, decode) VALUES (?, ?, ?, ?)",
                (mid, results, deviations, decode)
            )

        # ---------------------------
        # pending_notifications  ✅ NEW
        # ---------------------------
        rows = sheets["pending_notifications"].get_all_values()[1:]
        for r in rows:
            if not r or len(r) < 6:
                continue

            row_id, med_id, telegram_id, chat_id, kind, created_at = r[:6]

            rid = _safe_int(row_id)
            mid = _safe_int(med_id)
            tid = _safe_int(telegram_id)
            cid = _safe_int(chat_id)
            kind = str(kind).strip()

            if mid is None or tid is None or cid is None:
                continue
            if kind not in ("results", "decode"):
                continue

            # При старте после DELETE можно вставлять id как есть.
            # Если id пустой — дадим SQLite сгенерировать.
            if rid is not None:
                await db.execute(
                    """
                    INSERT INTO pending_notifications (id, med_id, telegram_id, chat_id, kind, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (rid, mid, tid, cid, kind, created_at)
                )
            else:
                await db.execute(
                    """
                    INSERT INTO pending_notifications (med_id, telegram_id, chat_id, kind, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (mid, tid, cid, kind, created_at)
                )

        # ---------------------------
        # api_keys
        # ---------------------------
        rows = sheets["api_keys"].get_all_values()[1:]
        for r in rows:
            if not r or len(r) < 2:
                continue
            key, is_active = r[:2]
            key = key.strip()
            if not key:
                continue
            active = str(is_active).strip().upper() == "TRUE"
            await db.execute(
                "INSERT OR IGNORE INTO api_keys (key, is_active) VALUES (?, ?)",
                (key, active)
            )

        await db.commit()
        print("[✅] Данные из Google Sheets загружены в SQLite (включая pending_notifications)")



# =========================================================
# SYNC TO GOOGLE SHEETS (оставил твой подход; новые таблицы не трогаем)
# =========================================================
async def sync_to_google_sheets():
    sheets = get_sheet()

    async with aiosqlite.connect(db_path) as db:
        # ---------------------------
        # neuro_dialog_states
        # ---------------------------
        async with db.execute("SELECT user_id, dialog_state FROM neuro_dialog_states") as cur:
            rows = await cur.fetchall()
        sheets["neuro_dialog_states"].clear()
        sheets["neuro_dialog_states"].update("A1", [["user_id", "dialog_state"]] + rows)

        # ---------------------------
        # neuro_bot_dialogs
        # ---------------------------
        async with db.execute(
            "SELECT telegram_id, user_name, dialog_text, updated_at, med_id, user_state FROM neuro_bot_dialogs"
        ) as cur:
            rows = await cur.fetchall()
        sheets["neuro_bot_dialogs"].clear()
        sheets["neuro_bot_dialogs"].update(
            "A1",
            [["telegram_id", "user_name", "dialog_text", "updated_at", "med_id", "user_state"]] + rows
        )

        # ---------------------------
        # api_keys
        # ---------------------------
        try:
            async with db.execute("SELECT key, is_active FROM api_keys") as cursor:
                keys = await cursor.fetchall()
            header = ["key", "is_active"]
            data = [[row[0], "TRUE" if row[1] else "FALSE"] for row in keys]
            sheet = sheets["api_keys"]
            sheet.clear()
            sheet.update("A1", [header] + data)
            print("[✅] api_keys обновлены")
        except Exception as e:
            print(f"[❌] Ошибка api_keys: {e}")

        # ---------------------------
        # neuro_message_links
        # ---------------------------
        async with db.execute("SELECT group_message_id, user_id FROM neuro_message_links") as cur:
            rows = await cur.fetchall()
        sheets["neuro_message_links"].clear()
        sheets["neuro_message_links"].update("A1", [["group_message_id", "user_id"]] + rows)

        # ---------------------------
        # neuro_user_reply_state
        # ---------------------------
        async with db.execute("SELECT user_id, manager_message_id FROM neuro_user_reply_state") as cur:
            rows = await cur.fetchall()
        sheets["neuro_user_reply_state"].clear()
        sheets["neuro_user_reply_state"].update("A1", [["user_id", "manager_message_id"]] + rows)

        # ---------------------------
        # neuro_user_answer_state
        # ---------------------------
        async with db.execute("SELECT user_id, manager_message_id FROM neuro_user_answer_state") as cur:
            rows = await cur.fetchall()
        sheets["neuro_user_answer_state"].clear()
        sheets["neuro_user_answer_state"].update("A1", [["user_id", "manager_message_id"]] + rows)

        # ---------------------------
        # tests_and_results  ✅ FIXED HEADER
        # ---------------------------
        # async with db.execute("SELECT med_id, results, deviations, decode FROM tests_and_results") as cur:
        #     rows = await cur.fetchall()
        # sheets["tests_and_results"].clear()
        # sheets["tests_and_results"].update(
        #     "A1",
        #     [["med_id", "results", "deviations", "decode"]] + rows
        # )

        # ---------------------------
        # pending_notifications ✅ NEW
        # ---------------------------
        async with db.execute("""
            SELECT id, med_id, telegram_id, chat_id, kind, created_at
            FROM pending_notifications
            ORDER BY id ASC
        """) as cur:
            rows = await cur.fetchall()

        sheets["pending_notifications"].clear()
        sheets["pending_notifications"].update(
            "A1",
            [["id", "med_id", "telegram_id", "chat_id", "kind", "created_at"]] + rows
        )

        print("[✅] Данные из SQLite выгружены в Google Sheets (включая pending_notifications)")



# ==== Периодическая синхронизация ====
async def periodic_sync(interval: int = 3600):
    while True:
        await asyncio.sleep(interval)
        try:
            await sync_to_google_sheets()
            print(f"Успешная синхронизация.")
        except Exception as e:
            print(f"Ошибка при синхронизации в Google Sheets: {e}")


# =========================================================
# DIALOGS
# =========================================================
async def append_answer(telegram_id: int, role: str, text: str):
    new_entry = f"\n[{role}]\n{text.strip()}\n"

    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            INSERT INTO neuro_bot_dialogs (telegram_id, dialog_text, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(telegram_id) DO UPDATE SET
                dialog_text = COALESCE(neuro_bot_dialogs.dialog_text, '') || excluded.dialog_text,
                updated_at = CURRENT_TIMESTAMP
            """,
            (telegram_id, new_entry)
        )
        await db.commit()


async def create_dialog_user_with_med_id(telegram_id: int, med_id: str):
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            INSERT INTO neuro_bot_dialogs (telegram_id, med_id)
            VALUES (?, ?)
            ON CONFLICT(telegram_id)
            DO UPDATE SET
                med_id = excluded.med_id,
                updated_at = CURRENT_TIMESTAMP
            """,
            (telegram_id, med_id)
        )
        await db.commit()

async def get_dialog(telegram_id: int) -> str:
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            "SELECT dialog_text FROM neuro_bot_dialogs WHERE telegram_id = ?",
            (telegram_id,)
        )
        row = await cursor.fetchone()
        return row[0] if row else ""

async def delete_line(telegram_id: int):
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "DELETE FROM neuro_bot_dialogs WHERE telegram_id = ?",
            (telegram_id,)
        )
        await db.commit()

async def delete_dialog(telegram_id: int):
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            UPDATE neuro_bot_dialogs
            SET dialog_text = '',
                updated_at = CURRENT_TIMESTAMP
            WHERE telegram_id = ?
            """,
            (telegram_id,)
        )
        await db.commit()

async def get_med_id(telegram_id: int) -> str | None:
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            "SELECT med_id FROM neuro_bot_dialogs WHERE telegram_id = ?",
            (telegram_id,)
        )
        row = await cursor.fetchone()
        return row[0] if row and row[0] else None

async def set_user_state(telegram_id: int, user_state: str):
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            INSERT INTO neuro_bot_dialogs (telegram_id, user_state)
            VALUES (?, ?)
            ON CONFLICT(telegram_id)
            DO UPDATE SET
                user_state = excluded.user_state,
                updated_at = CURRENT_TIMESTAMP
            """,
            (telegram_id, user_state)
        )
        await db.commit()

async def get_user_state(telegram_id: int) -> str | None:
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            "SELECT user_state FROM neuro_bot_dialogs WHERE telegram_id = ?",
            (telegram_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

# =========================================================
# USERS
# =========================================================
async def get_user(user_id: int) -> dict | None:
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            "SELECT user_id, name, is_medosomotr, phone, register_date, from_manager, privacy_policy_date, get_dop_tests FROM user_data WHERE user_id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()
        if row:
            return {
                "user_id": row[0],
                "name": row[1],
                "is_medosomotr": row[2],
                "phone": row[3],
                "register_date": row[4],
                "from_manager": row[5],
                "privacy_policy_date": row[6],
                "get_dop_tests": row[7]
            }
        return None


# =========================================================
# ANKETA
# =========================================================
async def get_anketa(user_id: int) -> dict | None:
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute("""
            SELECT * FROM user_anketa WHERE user_id = ?
        """, (user_id,))
        row = await cursor.fetchone()
        if row:
            columns = [
                "user_id", "organization_or_inn", "osmotr_date", "age", "weight", "height",
                "smoking", "alcohol", "physical_activity",
                "hypertension", "darkening_of_the_eyes", "sugar", "joint_pain", "chronic_diseases"
            ]
            return dict(zip(columns, row))
        return None


# =========================================================
# NEURO_DIALOG_STATE
# =========================================================
async def set_neuro_dialog_states(user_id: int, state: str):
    async with aiosqlite.connect(db_path) as db:
        await db.execute("""
            INSERT INTO neuro_dialog_states (user_id, dialog_state)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET dialog_state=excluded.dialog_state
        """, (user_id, state))
        await db.commit()

async def get_neuro_dialog_states(user_id: int) -> str | None:
    async with aiosqlite.connect(db_path) as db:
        async with db.execute("""
            SELECT dialog_state FROM neuro_dialog_states WHERE user_id = ?
        """, (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

async def delete_neuro_dialog_states(user_id: int):
    async with aiosqlite.connect(db_path) as db:
        await db.execute("""
            DELETE FROM neuro_dialog_states WHERE user_id = ?
        """, (user_id,))
        await db.commit()


#______ #ANSWER_STATE
async def save_user_answer_state(user_id: int, manager_msg_id: int):
    async with aiosqlite.connect(db_path) as db:
        await db.execute("""
            INSERT OR REPLACE INTO neuro_user_answer_state (user_id, manager_message_id)
            VALUES (?, ?)
        """, (user_id, manager_msg_id))
        await db.commit()

async def get_user_answer_state(user_id: int):
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute("SELECT manager_message_id FROM neuro_user_answer_state WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        return row[0] if row else None

async def delete_user_answer_state(user_id: int):
    async with aiosqlite.connect(db_path) as db:
        await db.execute("DELETE FROM neuro_user_answer_state WHERE user_id = ?", (user_id,))
        await db.commit()

async def save_message_link(group_msg_id: int, user_id: int):
    async with aiosqlite.connect(db_path) as db:
        await db.execute("""
            INSERT OR REPLACE INTO neuro_message_links (group_message_id, user_id)
            VALUES (?, ?)
        """, (group_msg_id, user_id))
        await db.commit()

async def get_user_id_by_group_message(group_msg_id: int):
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute("SELECT user_id FROM neuro_message_links WHERE group_message_id = ?", (group_msg_id,))
        row = await cursor.fetchone()
        return row[0] if row else None


# ______ TESTS_AND_RESULTS
async def get_test_results(med_id: int) -> Optional[str]:
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            "SELECT results FROM tests_and_results WHERE med_id = ?",
            (med_id,)
        ) as cursor:
            row = await cursor.fetchone()

    if not row or not row[0]:
        return None

    return row[0]

async def get_test_decode(med_id: int) -> Optional[str]:
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            "SELECT decode FROM tests_and_results WHERE med_id = ?",
            (med_id,)
        ) as cursor:
            row = await cursor.fetchone()

    if not row or not row[0]:
        return None

    return row[0]

async def get_deviations(med_id: int) -> Optional[str]:
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            "SELECT deviations FROM tests_and_results WHERE med_id = ?",
            (med_id,)
        ) as cursor:
            row = await cursor.fetchone()

    if not row or not row[0]:
        return None

    return row[0]



# ______ pending
async def add_pending_notification(med_id: int, telegram_id: int, chat_id: int, kind: str):
    if kind not in ("results", "decode"):
        raise ValueError("kind must be 'results' or 'decode'")

    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            INSERT INTO pending_notifications (med_id, telegram_id, chat_id, kind)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(med_id, kind) DO UPDATE SET
                telegram_id = excluded.telegram_id,
                chat_id = excluded.chat_id
            """,
            (med_id, telegram_id, chat_id, kind)
        )
        await db.commit()

async def get_all_pending_by_kind(kind: str) -> list[tuple[int, int, int, int]]:
    """
    Возвращает список задач: (id, med_id, telegram_id, chat_id)
    """
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            "SELECT id, med_id, telegram_id, chat_id FROM pending_notifications WHERE kind = ?",
            (kind,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [(int(r[0]), int(r[1]), int(r[2]), int(r[3])) for r in rows]

async def delete_pending_by_id(row_id: int):
    async with aiosqlite.connect(db_path) as db:
        await db.execute("DELETE FROM pending_notifications WHERE id = ?", (row_id,))
        await db.commit()

async def get_results_only(med_id: int) -> Optional[str]:
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            "SELECT results FROM tests_and_results WHERE med_id = ?",
            (med_id,)
        ) as cursor:
            row = await cursor.fetchone()
    if not row or not row[0]:
        return None
    return row[0]

async def get_decode_only(med_id: int) -> Optional[str]:
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            "SELECT decode FROM tests_and_results WHERE med_id = ?",
            (med_id,)
        ) as cursor:
            row = await cursor.fetchone()
    if not row or not row[0]:
        return None
    return row[0]







# =========================================================
# API_KEYS
# =========================================================
async def get_active_keys() -> list[str]:
    async with aiosqlite.connect(db_path) as db:
        async with db.execute("SELECT key FROM api_keys WHERE is_active=1") as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

async def deactivate_key(api_key: str):
    async with aiosqlite.connect(db_path) as db:
        await db.execute("UPDATE api_keys SET is_active = 0 WHERE key=?", (api_key,))
        await db.commit()
    try:
        await sync_to_google_sheets()
    except Exception as e:
        print(f"Не удалось синхронизировать ключи: {e}")




async def sync_tests_and_results_from_google():
    sheets = get_sheet()

    def _safe_int(x: str, default: Optional[int] = None) -> Optional[int]:
        try:
            x = str(x).strip()
            if x == "":
                return default
            return int(float(x))  # на случай "123.0" из Sheets
        except Exception:
            return default

    # Берём данные из листа tests_and_results
    rows = sheets["tests_and_results"].get_all_values()[1:]  # пропускаем заголовок

    async with aiosqlite.connect(db_path) as conn:
        for r in rows:
            if not r or len(r) < 4:
                continue

            med_id, results, deviations, decode = r[:4]
            mid = _safe_int(med_id)
            if mid is None:
                continue

            # Приводим к строкам, но сохраняем пустые как ''
            results = "" if results is None else str(results)
            deviations = "" if deviations is None else str(deviations)
            decode = "" if decode is None else str(decode)

            # UPSERT: обновляем только НЕпустые значения из Google,
            # чтобы пустыми ячейками не затереть уже загруженные данные.
            await conn.execute(
                """
                INSERT INTO tests_and_results (med_id, results, deviations, decode)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(med_id) DO UPDATE SET
                    results = CASE
                        WHEN excluded.results IS NOT NULL AND excluded.results != ''
                        THEN excluded.results
                        ELSE tests_and_results.results
                    END,
                    deviations = CASE
                        WHEN excluded.deviations IS NOT NULL AND excluded.deviations != ''
                        THEN excluded.deviations
                        ELSE tests_and_results.deviations
                    END,
                    decode = CASE
                        WHEN excluded.decode IS NOT NULL AND excluded.decode != ''
                        THEN excluded.decode
                        ELSE tests_and_results.decode
                    END
                """,
                (mid, results, deviations, decode)
            )

        await conn.commit()

    print("[✅] tests_and_results синхронизированы из Google Sheets (UPSERT, без очистки)")

async def sync_tests_job(context):
    try:
        await sync_tests_and_results_from_google()
    except Exception as e:
        # лучше печатать traceback как мы делали в error_handler
        print(f"[❌] Ошибка синхронизации tests_and_results: {type(e).__name__}: {e}")