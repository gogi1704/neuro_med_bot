import aiosqlite
import datetime
import asyncio
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os

db_path='dialogs.db'
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # на уровень выше папки db
CREDS_PATH = os.path.join(BASE_DIR, "docs", "anamnez-bot-fd6467c32f62.json")

async def init_db():
        async with aiosqlite.connect(db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS neuro_bot_dialogs (
                    telegram_id INTEGER PRIMARY KEY,
                    user_name TEXT,
                    dialog_text TEXT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    med_id TEXT
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_data (
                    user_id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    is_medosomotr TEXT,
                    phone TEXT,
                    register_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    from_manager TEXT,
                    privacy_policy_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    get_dop_tests TEXT
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_anketa (
                    user_id INTEGER PRIMARY KEY,
                    organization_or_inn TEXT,
                    osmotr_date DATETIME,
                    age INTEGER,
                    weight TEXT,
                    height TEXT,
                    smoking TEXT,
                    alcohol TEXT,
                    physical_activity TEXT,
                    hypertension TEXT,
                    darkening_of_the_eyes TEXT,
                    sugar TEXT,
                    joint_pain TEXT,
                    chronic_diseases TEXT,
                    FOREIGN KEY(user_id) REFERENCES user_data(user_id)
                )
            """)

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

            await db.commit()
        await sync_from_google_sheets()


# ==== Настройки Google API ====
SCOPE = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
SPREADSHEET_NAME = "anamnez_db"  # Имя файла в Google Sheets


# ==== Подключение к Google Sheets ====
def get_sheet():
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDS_PATH, SCOPE)
    client = gspread.authorize(creds)
    sheet = client.open(SPREADSHEET_NAME)
    return {
        "user_data": sheet.worksheet("user_data"),
        "user_anketa": sheet.worksheet("user_anketa"),
        "neuro_bot_dialogs": sheet.worksheet("neuro_bot_dialogs"),
        "neuro_dialog_states": sheet.worksheet("neuro_dialog_states"),
        "api_keys": sheet.worksheet("api_keys")
    }

# ==== Загрузка данных из Google Sheets в SQLite ====
async def sync_from_google_sheets():
    sheets = get_sheet()
    async with aiosqlite.connect(db_path) as db:
        # Очистка таблиц
        await db.execute("DELETE FROM user_data")
        await db.execute("DELETE FROM user_anketa")
        await db.execute("DELETE FROM neuro_bot_dialogs")
        await db.execute("DELETE FROM neuro_dialog_states")
        await db.execute("DELETE FROM api_keys")

        # user_data
        rows = sheets["user_data"].get_all_values()[1:]
        for r in rows:
            user_id, name, is_medosomotr, phone, register_date, from_manager, privacy_policy_date, get_dop_tests = r
            await db.execute(
                "INSERT INTO user_data (user_id, name, is_medosomotr, phone, register_date, from_manager, privacy_policy_date, get_dop_tests) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (int(user_id), name, is_medosomotr, phone, register_date, from_manager, privacy_policy_date, get_dop_tests)
            )

        # user_anketa
        rows = sheets["user_anketa"].get_all_values()[1:]
        for r in rows:
            user_id, organization_or_inn, osmotr_date, age, weight, height, smoking, alcohol, physical_activity, hypertension, darkening_of_the_eyes, sugar, joint_pain, chronic_diseases = r
            await db.execute(
                """INSERT INTO user_anketa (
                    user_id, organization_or_inn, osmotr_date, age, weight, height,
                    smoking, alcohol, physical_activity, hypertension, darkening_of_the_eyes, sugar, joint_pain, chronic_diseases
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (int(user_id), organization_or_inn, osmotr_date,
                 age if age else None,
                 weight if weight else None,
                 height if height else None,
                 smoking, alcohol, physical_activity, hypertension, darkening_of_the_eyes, sugar, joint_pain, chronic_diseases)
            )

        # neuro_bot_dialogs
        rows = sheets["neuro_bot_dialogs"].get_all_values()[1:]
        for r in rows:
            telegram_id, user_name, dialog_text, updated_at, med_id = r
            await db.execute(
                "INSERT INTO dialog_states (telegram_id, user_name, dialog_text, updated_at, med_id) VALUES (?,?,?,?,?)",
                (int(telegram_id), user_name, dialog_text, updated_at, med_id)
            )


        # neuro_dialog_states
        rows = sheets["neuro_dialog_states"].get_all_values()[1:]
        for r in rows:
            user_id, dialog_state = r
            await db.execute(
                "INSERT INTO dialog_states (user_id, neuro_dialog_states) VALUES (?, ?)",
                (int(user_id), dialog_state)
            )

        # api_keys
        api_keys = sheets["api_keys"].get_all_values()[1:]  # пропустить заголовок
        for row in api_keys:
            key, is_active = row
            await db.execute(
                "INSERT OR IGNORE INTO api_keys (key, is_active) VALUES (?, ?)",
                (key.strip(), is_active.strip() == "TRUE")
            )

        await db.commit()
        print("[✅] Данные из Google Sheets загружены в SQLite")

# ==== Выгрузка данных из SQLite в Google Sheets ====
async def sync_to_google_sheets():
    sheets = get_sheet()
    async with aiosqlite.connect(db_path) as db:

        # user_data
        async with db.execute("SELECT user_id, name, is_medosomotr, phone, register_date, from_manager, privacy_policy_date, get_dop_tests FROM user_data") as cur:
            rows = await cur.fetchall()
        sheets["user_data"].clear()
        sheets["user_data"].update("A1", [["user_id", "name", "is_medosomotr", "phone", "register_date", "from_manager", "privacy_policy_date", "get_dop_tests"]] + rows)

        # user_anketa
        async with db.execute("""SELECT user_id, organization_or_inn, osmotr_date, age, weight, height, smoking, alcohol, physical_activity, hypertension, darkening_of_the_eyes, sugar, joint_pain, chronic_diseases FROM user_anketa""") as cur:
            rows = await cur.fetchall()
        sheets["user_anketa"].clear()
        sheets["user_anketa"].update("A1", [["user_id", "organization_or_inn", "osmotr_date", "age", "weight", "height", "smoking", "alcohol", "physical_activity", "hypertension", "darkening_of_the_eyes", "sugar", "joint_pain", "chronic_diseases"]] + rows)

        # neuro_dialog_states
        async with db.execute("SELECT user_id, neuro_dialog_states FROM neuro_dialog_states") as cur:
            rows = await cur.fetchall()
        sheets["neuro_dialog_states"].clear()
        sheets["neuro_dialog_states"].update("A1", [["user_id", "dialog_state"]] + rows)

        # neuro_bot_dialogs
        async with db.execute("SELECT user_id, neuro_bot_dialogs FROM neuro_bot_dialogs") as cur:
            rows = await cur.fetchall()
        sheets["neuro_bot_dialogs"].clear()
        sheets["neuro_bot_dialogs"].update("A1", [["telegram_id, user_name, dialog_text, updated_at, med_id"]] + rows)


        # api_keys
        try:
            async with db.execute("SELECT * FROM api_keys") as cursor:
                keys = await cursor.fetchall()
            header = ["key", "is_active"]
            data = [[row[0], "TRUE" if row[1] else "FALSE"] for row in keys]
            sheet = sheets["api_keys"]
            sheet.clear()
            sheet.update('A1', [header] + data)
            print("[✅] api_keys обновлены")
        except Exception as e:
            print(f"[❌] Ошибка api_keys: {e}")

        print("[✅] Данные из SQLite выгружены в Google Sheets")

# ==== Периодическая синхронизация ====
async def periodic_sync(interval: int = 3600):
    while True:
        await asyncio.sleep(interval)
        try:
            await sync_to_google_sheets()
            print(f"Успешная синхронизация.")
        except Exception as e:
            print(f"Ошибка при синхронизации в Google Sheets: {e}")


#______ DIALOGS
async def append_answer(telegram_id: int, text: str):
        async with aiosqlite.connect(db_path) as db:
            cursor = await db.execute(
                "SELECT dialog_text FROM neuro_bot_dialogs WHERE telegram_id = ?",
                (telegram_id,)
            )
            row = await cursor.fetchone()

            # Собираем обновлённый текст
            new_entry = f"{text.strip()}\n"
            if row:
                dialog_text = row[0] + new_entry
            else:
                dialog_text = new_entry

            # Обновление или вставка
            await db.execute("""
                INSERT INTO neuro_bot_dialogs (telegram_id, dialog_text, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(telegram_id) DO UPDATE SET
                    dialog_text = excluded.dialog_text,
                    updated_at = excluded.updated_at
            """, (telegram_id, dialog_text, datetime.datetime.now(datetime.UTC)))
            await db.commit()

async def create_dialog_user(telegram_id: int, user_name: str):
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            INSERT INTO neuro_bot_dialogs (telegram_id, user_name, dialog_text)
            VALUES (?, ?, '')
            ON CONFLICT(telegram_id) DO NOTHING
            """,
            (telegram_id, user_name)
        )
        await db.commit()

async def create_dialog_user_with_med_id(telegram_id: int, med_id: str):
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            INSERT INTO neuro_bot_dialogs (telegram_id, med_id, dialog_text)
            VALUES (?, ?, '')
            ON CONFLICT(telegram_id) DO NOTHING
            """,
            (telegram_id, med_id)
        )
        await db.commit()

async def get_dialog( telegram_id: int) -> str:
        async with aiosqlite.connect(db_path) as db:
            cursor = await db.execute(
                "SELECT dialog_text FROM neuro_bot_dialogs WHERE telegram_id = ?",
                (telegram_id,)
            )
            row = await cursor.fetchone()
            return row[0] if row else ""

async def delete_dialog( telegram_id: int):
        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                "DELETE FROM neuro_bot_dialogs WHERE telegram_id = ?",
                (telegram_id,)
            )
            await db.commit()
#______


#______ USERS
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
                "from_manager":row[5],
                "privacy_policy_date":row[6],
                "get_dop_tests":row[7]
            }
        return None
#______


#______ ANKETA
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
# ______

#______ #NEURO_DIALOG_STATE
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
#______

#______ #API_KEYS
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


