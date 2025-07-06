import logging
import logging.config

from contextlib import asynccontextmanager

import asyncio
import asyncpg

import gspread
from oauth2client.service_account import ServiceAccountCredentials

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from utils.logging_settings import logging_config
from config import load_config

logging.config.dictConfig(logging_config)
logger = logging.getLogger(__name__)

db_pool = None


def task_dict_from_db(row):
    return {
        "title": row["title"],
        "description": row["description"],
        "start_day": row["start_day"],
        "start_time": row["start_time"],
        "end_day": row["end_day"],
        "end_time": row["end_time"],
    }


def task_dict_from_sheet(row):
    return {
        "title": row.get("title"),
        "description": row.get("description"),
        "start_day": int(row.get("start_day", 0)),
        "start_time": row.get("start_time"),
        "end_day": int(row.get("end_day", 0)),
        "end_time": row.get("end_time"),
    }


async def get_sheet_and_db(pool):
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('service_account.json', scope)
    client = gspread.authorize(creds)
    sheet = client.open("vol_bot_tasks").worksheet("List")
    sheet_records = sheet.get_all_records()
    async with pool.acquire() as conn:
        db_rows = await conn.fetch("SELECT * FROM task")
    db_tasks = [task_dict_from_db(row) for row in db_rows]
    sheet_tasks = [task_dict_from_sheet(row) for row in sheet_records]
    return sheet, sheet_tasks, db_tasks


@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_pool
    config = load_config()
    db_pool = await asyncpg.create_pool(
        user=config.db.user,
        password=config.db.password,
        database=config.db.database,
        host=config.db.host,
        port=config.db.port
    )
    logger.info("Successfully created DB connection")
    yield
    await db_pool.close()
    logger.info("DB connection closed")

app = FastAPI(lifespan=lifespan)


@app.get("/merge-sheet-to-db")
async def merge_sheet_to_db():
    try:
        sheet, sheet_tasks, db_tasks = await get_sheet_and_db(db_pool)
        db_titles = {t["title"]: t for t in db_tasks}
        sheet_titles = {t["title"]: t for t in sheet_tasks}

        async with db_pool.acquire() as conn:
            async with conn.transaction():
                # 1. Обновить БД по данным из Google Sheets (если отличается)
                for t in sheet_tasks:
                    if t["title"] in db_titles:
                        db_t = db_titles[t["title"]]
                        fields = ["description", "start_day", "start_time", "end_day", "end_time"]
                        if any(t[f] != db_t[f] for f in fields):
                            await conn.execute("""
                                UPDATE task SET description=$1, start_day=$2, start_time=$3, end_day=$4, end_time=$5, updated_at=NOW()
                                WHERE title=$6
                            """, t["description"], t["start_day"], t["start_time"], t["end_day"], t["end_time"], t["title"])
                    else:
                        # 2. Добавить в БД если есть только в Google Sheet
                        await conn.execute("""
                            INSERT INTO task (title, description, start_day, start_time, end_day, end_time, created_at)
                            VALUES ($1, $2, $3, $4, $5, $6, NOW())
                        """, t["title"], t["description"], t["start_day"], t["start_time"], t["end_day"], t["end_time"])

        # 3. Добавить в Google Sheet если есть только в БД (batch)
        new_rows = []
        for t in db_tasks:
            if t["title"] not in sheet_titles:
                new_rows.append([
                    t["title"], t["description"], t["start_day"], t["start_time"],
                    t["end_day"], t["end_time"]
                ])
        if new_rows:
            sheet.append_rows(new_rows, value_input_option="USER_ENTERED")

        return JSONResponse({"status": "ok", "message": "Merged sheet to DB"})
    except Exception as e:
        logger.exception("Error in merge_sheet_to_db")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@app.get("/merge-db-to-sheet")
async def merge_db_to_sheet():
    try:
        sheet, sheet_tasks, db_tasks = await get_sheet_and_db(db_pool)
        db_titles = {t["title"]: t for t in db_tasks}
        sheet_titles = {t["title"]: t for t in sheet_tasks}

        # 1. Обновить Google Sheet по данным из БД (batch)
        batch_updates = []
        for idx, t in enumerate(sheet_tasks):
            if t["title"] in db_titles:
                db_t = db_titles[t["title"]]
                fields = ["description", "start_day", "start_time", "end_day", "end_time"]
                if any(t[f] != db_t[f] for f in fields):
                    # Индексы в gspread начинаются с 2 (1 — заголовки)
                    batch_updates.append({
                        "range": f"B{idx+2}:F{idx+2}",
                        "values": [[
                            db_t["description"], db_t["start_day"], db_t["start_time"],
                            db_t["end_day"], db_t["end_time"]
                        ]]
                    })
            else:
                # 2. Добавить в БД если есть только в Google Sheet
                async with db_pool.acquire() as conn:
                    async with conn.transaction():
                        await conn.execute("""
                            INSERT INTO task (title, description, start_day, start_time, end_day, end_time, created_at)
                            VALUES ($1, $2, $3, $4, $5, $6, NOW())
                        """, t["title"], t["description"], t["start_day"], t["start_time"], t["end_day"], t["end_time"])

        if batch_updates:
            body = {"valueInputOption": "USER_ENTERED", "data": batch_updates}
            sheet.spreadsheet.values_batch_update(body)

        # 3. Добавить в Google Sheet если есть только в БД (batch)
        new_rows = []
        for t in db_tasks:
            if t["title"] not in sheet_titles:
                new_rows.append([
                    t["title"], t["description"], t["start_day"], t["start_time"],
                    t["end_day"], t["end_time"]
                ])
        if new_rows:
            sheet.append_rows(new_rows, value_input_option="USER_ENTERED")

        return JSONResponse({"status": "ok", "message": "Merged DB to sheet"})
    except Exception as e:
        logger.exception("Error in merge_db_to_sheet")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
    

@app.get("/get_lists")
async def get_lists():
    try:
        _, sheet_tasks, db_tasks = await get_sheet_and_db(db_pool)
        return JSONResponse({"status": "ok", "sheet_tasks": sheet_tasks, "db_tasks": db_tasks})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)