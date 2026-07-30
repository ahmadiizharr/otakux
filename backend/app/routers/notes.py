import uuid

from fastapi import APIRouter, HTTPException, UploadFile
from pydantic import BaseModel

from .. import d1, r2

router = APIRouter(prefix="/notes", tags=["notes"])


class NoteCreate(BaseModel):
    title: str
    content: str = ""


class Note(NoteCreate):
    id: int
    attachment_key: str | None = None
    created_at: str


@router.post("", response_model=Note)
async def create_note(note: NoteCreate):
    rows = await d1.query(
        "INSERT INTO notes (title, content) VALUES (?, ?) RETURNING *",
        [note.title, note.content],
    )
    return rows[0]


@router.get("", response_model=list[Note])
async def list_notes():
    return await d1.query("SELECT * FROM notes ORDER BY id DESC")


@router.get("/{note_id}", response_model=Note)
async def get_note(note_id: int):
    rows = await d1.query("SELECT * FROM notes WHERE id = ?", [note_id])
    if not rows:
        raise HTTPException(404, "Note not found")
    return rows[0]


@router.delete("/{note_id}", status_code=204)
async def delete_note(note_id: int):
    rows = await d1.query("SELECT * FROM notes WHERE id = ?", [note_id])
    if not rows:
        raise HTTPException(404, "Note not found")

    if rows[0]["attachment_key"]:
        r2.delete_file(rows[0]["attachment_key"])

    await d1.query("DELETE FROM notes WHERE id = ?", [note_id])


@router.post("/{note_id}/attachment", response_model=Note)
async def upload_attachment(note_id: int, file: UploadFile):
    rows = await d1.query("SELECT * FROM notes WHERE id = ?", [note_id])
    if not rows:
        raise HTTPException(404, "Note not found")

    key = f"notes/{note_id}/{uuid.uuid4()}-{file.filename}"
    data = await file.read()
    r2.upload_file(key, data, content_type=file.content_type)

    updated = await d1.query(
        "UPDATE notes SET attachment_key = ? WHERE id = ? RETURNING *",
        [key, note_id],
    )
    return updated[0]


@router.get("/{note_id}/attachment")
async def get_attachment_url(note_id: int):
    rows = await d1.query("SELECT * FROM notes WHERE id = ?", [note_id])
    if not rows or not rows[0]["attachment_key"]:
        raise HTTPException(404, "No attachment for this note")

    return {"url": r2.presigned_download_url(rows[0]["attachment_key"])}
