"""
/books - Unit 02: path/query parameters, validation, BackgroundTasks, search.

    GET    /books                list: ?author= ?tag= ?min_year= ?max_year=
                                       ?available= ?sort= ?skip= ?limit=
    GET    /books/search?q=      full-text search (Elasticsearch, MongoDB fallback)
    GET    /books/{id}           404 unknown, 422 malformed id (Path pattern)
    POST   /books                201 + Location, 409 ISBN used, 422 invalid
    PUT    /books/{id}           full replacement
    PATCH  /books/{id}           partial update
    DELETE /books/{id}           204

New compared with Unit 01:
    - Query(...) / Path(...) constraints -> 422 BEFORE the handler runs
    - BackgroundTasks: the book is indexed in Elasticsearch after the response
    - /books/search is declared BEFORE /books/{book_id}, otherwise FastAPI
      would take "search" for a book id (routes are matched in order)
"""
import re
from typing import Annotated, Literal

from bson import ObjectId
from fastapi import (APIRouter, BackgroundTasks, Depends, HTTPException, Path, Query,
                     Request, Response, status)
from pymongo import ASCENDING, DESCENDING, ReturnDocument
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

from .. import search
from ..db import get_database
from ..schemas import BookIn, BookOut, BookPatch, SearchResult

router = APIRouter(prefix="/books", tags=["books"])

# an ObjectId is exactly 24 hexadecimal characters: anything else -> 422
BookId = Annotated[str, Path(pattern=r"^[0-9a-f]{24}$", description="MongoDB ObjectId")]
FIELDS = ("title", "author", "year", "isbn", "price", "tags", "available")


def to_out(doc: dict) -> BookOut:
    return BookOut(id=str(doc["_id"]), **{k: doc[k] for k in FIELDS if k in doc})


def not_found(request: Request) -> HTTPException:
    request.state.action = "book_not_found"
    return HTTPException(status_code=404, detail="Book not found")


def isbn_conflict(request: Request, isbn: str) -> HTTPException:
    request.state.action = "book_isbn_conflict"
    return HTTPException(status_code=409, detail=f"ISBN {isbn} already exists")


@router.get("", response_model=list[BookOut])
def list_books(request: Request,
               author: str | None = None,
               tag: str | None = None,
               min_year: int | None = Query(default=None, ge=1450),
               max_year: int | None = Query(default=None, ge=1450),
               available: bool | None = None,
               sort: Literal["title", "-title", "year", "-year", "price", "-price"] = "title",
               skip: int = Query(default=0, ge=0),
               limit: int = Query(default=20, ge=1, le=100),
               db: Database = Depends(get_database)):
    request.state.action = "books_listed"
    query: dict = {}
    if author:
        query["author"] = author
    if tag:
        query["tags"] = tag.lower()          # matches one element of the array
    if available is not None:
        query["available"] = available
    if min_year or max_year:
        query["year"] = {k: v for k, v in (("$gte", min_year), ("$lte", max_year)) if v}
    direction = DESCENDING if sort.startswith("-") else ASCENDING
    cursor = db.books.find(query).sort(sort.lstrip("-"), direction).skip(skip).limit(limit)
    return [to_out(d) for d in cursor]


@router.get("/search", response_model=SearchResult)
def search_books(request: Request, q: str = Query(min_length=2, max_length=100),
                 size: int = Query(default=10, ge=1, le=50),
                 db: Database = Depends(get_database)):
    request.state.action = "books_searched"
    hits = search.search_books(q, size)
    if hits is not None:
        return {"engine": "elasticsearch", "total": len(hits), "hits": hits}
    # degraded mode: case-insensitive substring match, no ranking, no typo tolerance
    pattern = {"$regex": re.escape(q), "$options": "i"}
    docs = db.books.find({"$or": [{"title": pattern}, {"author": pattern}]}).limit(size)
    found = [to_out(d).model_dump() for d in docs]
    return {"engine": "mongodb", "total": len(found), "hits": found}


@router.get("/{book_id}", response_model=BookOut)
def get_book(book_id: BookId, request: Request, db: Database = Depends(get_database)):
    doc = db.books.find_one({"_id": ObjectId(book_id)})
    if doc is None:
        raise not_found(request)
    request.state.action = "book_read"
    return to_out(doc)


@router.post("", response_model=BookOut, status_code=status.HTTP_201_CREATED)
def create_book(book: BookIn, request: Request, response: Response,
                background: BackgroundTasks, db: Database = Depends(get_database)):
    try:
        result = db.books.insert_one(book.model_dump())
    except DuplicateKeyError:
        raise isbn_conflict(request, book.isbn)
    request.state.action = "book_created"
    book_id = str(result.inserted_id)
    response.headers["Location"] = f"/books/{book_id}"
    # runs AFTER the response is sent: the client does not wait for Elasticsearch
    background.add_task(search.index_book, book_id, book.model_dump())
    return to_out(db.books.find_one({"_id": result.inserted_id}))


@router.put("/{book_id}", response_model=BookOut)
def replace_book(book_id: BookId, book: BookIn, request: Request,
                 background: BackgroundTasks, db: Database = Depends(get_database)):
    try:
        doc = db.books.find_one_and_replace({"_id": ObjectId(book_id)}, book.model_dump(),
                                            return_document=ReturnDocument.AFTER)
    except DuplicateKeyError:
        raise isbn_conflict(request, book.isbn)
    if doc is None:
        raise not_found(request)
    request.state.action = "book_replaced"
    background.add_task(search.index_book, book_id, book.model_dump())
    return to_out(doc)


@router.patch("/{book_id}", response_model=BookOut)
def update_book(book_id: BookId, changes: BookPatch, request: Request,
                background: BackgroundTasks, db: Database = Depends(get_database)):
    fields = changes.model_dump(exclude_unset=True)
    doc = (db.books.find_one_and_update({"_id": ObjectId(book_id)}, {"$set": fields},
                                        return_document=ReturnDocument.AFTER)
           if fields else db.books.find_one({"_id": ObjectId(book_id)}))
    if doc is None:
        raise not_found(request)
    request.state.action = "book_updated"
    out = to_out(doc)
    background.add_task(search.index_book, book_id, out.model_dump(exclude={"id"}))
    return out


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_book(book_id: BookId, request: Request, background: BackgroundTasks,
                db: Database = Depends(get_database)):
    if db.books.delete_one({"_id": ObjectId(book_id)}).deleted_count == 0:
        raise not_found(request)
    request.state.action = "book_deleted"
    background.add_task(search.delete_book, book_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
